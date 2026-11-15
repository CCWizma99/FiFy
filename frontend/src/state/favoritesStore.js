export const FAVORITES_KEY = 'fify.favorites';
export function createFavoritesStore(storage = () => localStorage) {
  let snapshot;
  const listeners = new Set();
  function read() {
    try {
      const data = JSON.parse(storage().getItem(FAVORITES_KEY) || '[]');
      return Array.isArray(data) ? data.filter(p => p && typeof p.id === 'string' && typeof p.product_name === 'string') : [];
    } catch { return []; }
  }
  const getSnapshot = () => snapshot ??= read();
  return {
    getSnapshot,
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    toggle(product) {
      const items = getSnapshot();
      snapshot = items.some(p => p.id === product.id) ? items.filter(p => p.id !== product.id) : [...items, product];
      try { storage().setItem(FAVORITES_KEY, JSON.stringify(snapshot)); } catch { /* Preserve session state. */ }
      listeners.forEach(listener => listener());
    },
  };
}
