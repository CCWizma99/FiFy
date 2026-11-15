import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { expect, it, vi } from 'vitest';
import { createFavoritesStore, FAVORITES_KEY } from '../state/favoritesStore';
import FavoriteButton from '../components/FavoriteButton';
import Saved from '../pages/Saved';
const product = { id: 'favorite', product_name: 'Saved dress', price: 10 };
it('persists favorites and restores them in another store', () => {
  const storage = { getItem: () => null, setItem: vi.fn() };
  const store = createFavoritesStore(() => storage);
  store.toggle(product);
  expect(storage.setItem).toHaveBeenCalledWith(FAVORITES_KEY, JSON.stringify([product]));
  expect(createFavoritesStore(() => ({ getItem: () => JSON.stringify(store.getSnapshot()) })).getSnapshot()).toEqual([product]);
  store.toggle(product);
  expect(store.getSnapshot()).toEqual([]);
});
it.each(['{broken', '{}', '[null,42,{"id":"invalid"}]'])('handles corrupt storage: %s', value => {
  expect(createFavoritesStore(() => ({ getItem: () => value })).getSnapshot()).toEqual([]);
});
it('keeps session favorites when storage access fails', () => {
  const store = createFavoritesStore(() => { throw new Error('denied'); });
  expect(store.getSnapshot()).toEqual([]);
  const listener = vi.fn();
  store.subscribe(listener);
  store.toggle(product);
  expect(store.getSnapshot()).toEqual([product]);
  expect(listener).toHaveBeenCalled();
});
it('keeps session favorites when writes fail', () => {
  const store = createFavoritesStore(() => ({ getItem: () => '[]', setItem: () => { throw new Error('full'); } }));
  store.toggle(product);
  expect(store.getSnapshot()).toEqual([product]);
});
it('shares saved state across buttons and the Saved page', () => {
  render(<MemoryRouter><FavoriteButton product={product} /><Saved /></MemoryRouter>);
  fireEvent.click(screen.getByRole('button', { name: 'Save Saved dress' }));
  expect(screen.getByRole('link', { name: 'Saved dress' })).toHaveAttribute('href', '/product/favorite');
  expect(screen.getAllByRole('button', { name: 'Unsave Saved dress' })).toHaveLength(2);
  fireEvent.click(screen.getAllByRole('button', { name: 'Unsave Saved dress' })[1]);
  expect(screen.getByText('No saved items yet.')).toBeVisible();
});
