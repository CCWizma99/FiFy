import { useSyncExternalStore } from 'react';
import { createFavoritesStore } from './favoritesStore';
const store = createFavoritesStore();
export function useFavorites() {
  const favorites = useSyncExternalStore(store.subscribe, store.getSnapshot);
  return { favorites, isSaved: id => favorites.some(p => p.id === id), toggle: store.toggle };
}
