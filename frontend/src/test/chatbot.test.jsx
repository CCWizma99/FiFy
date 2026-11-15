import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { JSDOM } from 'jsdom';
import { afterEach, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Chatbot from '../components/Chatbot';
const asset = name => readFileSync(resolve(process.cwd(), '../backend/chatbot/static', name), 'utf8');
let dom;
afterEach(() => dom?.window.close());
function widget(fetchImpl) {
  dom = new JSDOM(asset('frame.html'), { url: 'https://demo.test/chatbot/frame', runScripts: 'outside-only' });
  dom.window.fetch = fetchImpl;
  dom.window.eval(asset('frame.js'));
  return { window: dom.window, document: dom.window.document, $: id => dom.window.document.getElementById(id) };
}
const response = text => ({ ok: true, json: async () => ({ reply: { text } }) });
const tick = () => new Promise(resolve => setTimeout(resolve, 20));
function submit(w, text) {
  w.$('message').value = text;
  w.$('composer').dispatchEvent(new w.window.Event('submit', { cancelable: true }));
}
it('opens, focuses, sends a chip, renders plain text, and clears history', async () => {
  const fetch = vi.fn().mockResolvedValue(response('No account is required. <script>unsafe</script>'));
  const w = widget(fetch);
  w.$('launcher').click();
  expect(w.$('panel').hidden).toBe(false);
  expect(w.document.activeElement).toBe(w.$('message'));
  w.$('suggestions').querySelectorAll('button')[2].click();
  expect(w.$('send').disabled).toBe(true);
  await tick();
  expect(w.$('messages').textContent).toContain('No account is required. <script>unsafe</script>');
  expect(w.$('messages').querySelector('script')).toBeNull();
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ bot_id: 'fify-demo', message: 'Do I need an account?', history: [] });
  submit(w, 'How do I save?'); await tick();
  expect(JSON.parse(fetch.mock.calls[1][1].body).history).toHaveLength(2);
  w.$('reset').click(); submit(w, 'Hello'); await tick();
  expect(JSON.parse(fetch.mock.calls[2][1].body).history).toEqual([]);
  w.$('close').click();
  expect(w.$('panel').hidden).toBe(true);
  expect(w.document.activeElement).toBe(w.$('launcher'));
});
it('shows failures and retries without duplicating the user turn', async () => {
  const fetch = vi.fn().mockResolvedValueOnce({ ok: false, json: async () => ({ detail: 'Quota exhausted. Try later.' }) }).mockResolvedValue(response('Hello'));
  const w = widget(fetch); w.$('launcher').click(); submit(w, 'Hello'); await tick();
  expect(w.$('feedback').hidden).toBe(false);
  expect(w.$('feedback').textContent).toContain('Quota exhausted');
  w.$('retry').click(); await tick();
  expect(w.$('messages').querySelectorAll('.user')).toHaveLength(1);
  expect(w.$('messages').querySelectorAll('.assistant')).toHaveLength(1);
});
it('ignores replies after reset and aborts pending work', async () => {
  let finish;
  const fetch = vi.fn(() => new Promise(resolve => { finish = resolve; }));
  const w = widget(fetch); w.$('launcher').click(); submit(w, 'Hello');
  const signal = fetch.mock.calls[0][1].signal;
  w.$('reset').click(); finish(response('Old reply')); await tick();
  expect(signal.aborted).toBe(true);
  expect(w.$('messages').textContent).not.toContain('Old reply');
  expect(w.$('send').disabled).toBe(false);
});
it('Enter sends, Shift+Enter does not, and Escape closes', async () => {
  const fetch = vi.fn().mockResolvedValue(response('Hello'));
  const w = widget(fetch); w.$('launcher').click(); w.$('message').value = 'Hi';
  w.$('message').dispatchEvent(new w.window.KeyboardEvent('keydown', { key: 'Enter', shiftKey: true }));
  expect(fetch).not.toHaveBeenCalled();
  w.$('message').dispatchEvent(new w.window.KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); await tick();
  expect(fetch).toHaveBeenCalledTimes(1);
  w.document.dispatchEvent(new w.window.KeyboardEvent('keydown', { key: 'Escape' }));
  expect(w.$('panel').hidden).toBe(true);
});
it('loader isolates styling and only accepts resize messages from its iframe', () => {
  dom = new JSDOM('<body><script src="https://assistant.test/widget.js" data-bot-id="fify-demo"></script></body>', { url: 'https://host.test', runScripts: 'outside-only' });
  const script = dom.window.document.querySelector('script');
  Object.defineProperty(dom.window.document, 'currentScript', { value: script });
  dom.window.eval(asset('widget.js'));
  const frame = dom.window.document.querySelector('iframe');
  expect(frame.src).toContain('https://assistant.test/chatbot/frame?bot_id=fify-demo');
  expect(frame.getAttribute('sandbox')).toBe('allow-scripts allow-same-origin allow-forms');
  dom.window.dispatchEvent(new dom.window.MessageEvent('message', { origin: 'https://evil.test', source: frame.contentWindow, data: { type: 'fify:resize', open: true } }));
  expect(frame.style.width).toBe('210px');
  dom.window.dispatchEvent(new dom.window.MessageEvent('message', { origin: 'https://assistant.test', source: frame.contentWindow, data: { type: 'fify:resize', open: true } }));
  expect(frame.style.width).toBe('420px');
  dom.window.eval(asset('widget.js'));
  expect(dom.window.document.querySelectorAll('iframe')).toHaveLength(1);
});
it('mounts the public script in FiFy and excludes admin pages', () => {
  const view = render(<MemoryRouter><Chatbot /></MemoryRouter>);
  expect(document.querySelector('script[data-bot-id="fify-demo"]')).toBeTruthy();
  view.unmount();
  expect(document.querySelector('script[data-bot-id="fify-demo"]')).toBeNull();
  render(<MemoryRouter initialEntries={['/admin']}><Chatbot /></MemoryRouter>);
  expect(document.querySelector('script[data-bot-id="fify-demo"]')).toBeNull();
});
