/* FiFy standalone embed: public configuration only. No credentials belong here. */
(() => {
  const script = document.currentScript;
  if (!script || document.getElementById('fify-assistant-widget')) return;
  const source = new URL('./chatbot/frame', script.src);
  source.searchParams.set('bot_id', script.dataset.botId || 'fify-demo');
  source.searchParams.set('title', (script.dataset.title || 'FiFy AI Assistant').slice(0, 60));
  if (/^#[0-9a-f]{6}$/i.test(script.dataset.theme || '')) source.searchParams.set('theme', script.dataset.theme);
  const frame = document.createElement('iframe');
  frame.id = 'fify-assistant-widget';
  frame.title = script.dataset.title || 'FiFy AI Assistant';
  frame.src = source.href;
  frame.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-forms');
  frame.setAttribute('referrerpolicy', 'no-referrer');
  Object.assign(frame.style, { position: 'fixed', bottom: '16px', right: '16px', width: '210px', height: '80px', border: '0', background: 'transparent', zIndex: '2147483000', colorScheme: 'light', maxWidth: 'calc(100vw - 24px)', maxHeight: 'calc(100dvh - 24px)' });
  const resize = event => {
    if (event.source !== frame.contentWindow || event.origin !== source.origin || event.data?.type !== 'fify:resize') return;
    const open = event.data.open === true;
    frame.style.width = open ? '420px' : '210px';
    frame.style.height = open ? '700px' : '80px';
  };
  window.addEventListener('message', resize);
  document.body.appendChild(frame);
  // Let a host app clean up the listener when unmounting this widget.
  frame.addEventListener('fify:remove', () => { window.removeEventListener('message', resize); frame.remove(); }, { once: true });
})();
