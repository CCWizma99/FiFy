export function apiUrl(path, base = import.meta.env.VITE_API_URL || 'http://localhost:8000') {
  const prefix = base.replace(/\/+$/, '');
  const rooted = !prefix || /^(https?:)?\//.test(prefix) ? prefix : `/${prefix.replace(/^\.\//, '')}`;
  return `${rooted}/${path.replace(/^\/+/, '')}`;
}

export function websocketUrl(path, base = import.meta.env.VITE_API_URL || 'http://localhost:8000', origin = window.location.origin) {
  const url = new URL(apiUrl(path, base), origin);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return url.href;
}
