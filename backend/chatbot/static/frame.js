(() => {
  const params = new URLSearchParams(location.search);
  const title = (params.get('title') || 'FiFy AI Assistant').slice(0, 60);
  const botId = params.get('bot_id') || 'fify-demo';
  const theme = params.get('theme');
  if (/^#[0-9a-f]{6}$/i.test(theme || '')) document.documentElement.style.setProperty('--navy', theme);
  const $ = id => document.getElementById(id);
  $('bot-title').textContent = title;
  $('panel').setAttribute('aria-label', title);
  $('launcher').setAttribute('aria-label', `Open ${title}`);
  let history = [];
  let pending = null;
  let lastMessage = '';
  let open = false;
  function setOpen(value) {
    open = value;
    $('panel').hidden = !open;
    $('launcher').hidden = open;
    $('launcher').setAttribute('aria-expanded', String(open));
    // Contains only sizing state, never messages or credentials. Host validates source + origin.
    if (parent !== window) parent.postMessage({ type: 'fify:resize', open }, '*');
    (open ? $('message') : $('launcher')).focus();
  }
  function scroll() { $('messages').scrollTop = $('messages').scrollHeight; }
  function bubble(role, text) {
    const wrapper = document.createElement('div');
    wrapper.className = `message ${role}`;
    const label = document.createElement('div');
    label.className = 'speaker'; label.textContent = role === 'user' ? 'You' : 'FiFy assistant';
    const body = document.createElement('div');
    body.className = 'bubble'; body.textContent = text;
    wrapper.append(label, body); $('messages').append(wrapper); scroll();
  }
  function feedback(text, retry = false) {
    $('feedback').hidden = !text; $('feedback-text').textContent = text;
    $('retry').hidden = !retry;
  }
  function reset() {
    if (pending) pending.abort();
    pending = null; history = []; lastMessage = '';
    $('send').disabled = false; $('message').value = ''; feedback('');
    $('messages').replaceChildren();
    const greeting = document.createElement('div'); greeting.id = 'greeting';
    const heading = document.createElement('div'); heading.className = 'greeting-title'; heading.textContent = 'A little guidance.\nA better find.';
    const copy = document.createElement('p'); copy.className = 'greeting-copy'; copy.textContent = 'Hi, I’m your FiFy guide. Ask me about photo search, saving your finds, or getting started.';
    greeting.append(heading, copy); $('messages').append(greeting);
    $('suggestions').hidden = false;
    if (open) $('message').focus();
  }
  async function send(text, retry = false) {
    text = text.trim();
    if (!text || pending) return;
    if (text.length > 1000) { feedback('Please keep your message under 1,000 characters.'); return; }
    $('greeting')?.remove();
    if (!retry) bubble('user', text);
    $('suggestions').hidden = true; $('message').value = ''; feedback('');
    lastMessage = text;
    const controller = new AbortController(); pending = controller;
    $('send').disabled = true;
    const typing = document.createElement('div'); typing.className = 'typing'; typing.textContent = 'FiFy is thinking…'; typing.setAttribute('role', 'status'); $('messages').append(typing); scroll();
    const timeout = setTimeout(() => controller.abort(), 30000);
    try {
      const endpoint = new URL('../api/chatbot/message', location.href);
      const response = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bot_id: botId, message: text, history: history.slice(-8) }), signal: controller.signal });
      if (pending !== controller) return;
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const detail = typeof data.detail === 'string' ? data.detail : 'The assistant could not respond. Please try again.';
        throw new Error(detail);
      }
      const data = await response.json();
      if (pending !== controller) return;
      if (typeof data.reply?.text !== 'string' || !data.reply.text.trim()) throw new Error('The assistant returned an empty response. Please try again.');
      bubble('assistant', data.reply.text);
      history.push({ role: 'user', content: text }, { role: 'assistant', content: data.reply.text.slice(0, 1000) });
      history = history.slice(-8);
    } catch (error) {
      if (pending === controller) feedback(error.name === 'AbortError' ? 'The assistant took too long to respond. Please try again.' : error.message, true);
    } finally {
      clearTimeout(timeout); typing.remove();
      if (pending === controller) { pending = null; $('send').disabled = false; if (open) $('message').focus(); }
    }
  }
  $('launcher').addEventListener('click', () => setOpen(!open));
  $('close').addEventListener('click', () => setOpen(false));
  $('reset').addEventListener('click', reset);
  $('composer').addEventListener('submit', event => { event.preventDefault(); send($('message').value); });
  $('message').addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); send($('message').value); }
  });
  $('retry').addEventListener('click', () => send(lastMessage, true));
  $('suggestions').querySelectorAll('button').forEach(button => button.addEventListener('click', () => send(button.textContent)));
  document.addEventListener('keydown', event => { if (event.key === 'Escape') setOpen(false); });
  window.addEventListener('pagehide', () => { if (pending) pending.abort(); });
  reset();
})();
