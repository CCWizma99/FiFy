import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Home from '../pages/Home';
import Results from '../pages/Results';
import ProductDetail from '../pages/ProductDetail';
import ProductsTab from '../components/admin/ProductsTab';
import Onboarding from '../pages/Onboarding';
import Saved from '../pages/Saved';
import { apiUrl, websocketUrl } from '../api/config';
import { sortProducts, shareProduct } from '../utils';
const product = (id, price = 10) => ({ id, product_name: `Dress ${id}`, price, source_site: 'example.test' });
const ok = data => ({ ok: true, json: async () => data });
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
function router(element, entry = '/') {
  return render(<MemoryRouter initialEntries={[entry]}><Routes>
    <Route path="/" element={element} /><Route path="/results" element={<Results />} />
    <Route path="/product/:id" element={<ProductDetail />} /><Route path="/saved" element={<Saved />} />
  </Routes></MemoryRouter>);
}
beforeEach(() => { vi.stubGlobal('fetch', vi.fn().mockResolvedValue(ok([]))); });

describe('URLs and utility behavior', () => {
  it('normalizes absolute and relative prefixes and websocket schemes', () => {
    expect(apiUrl('/search/text', 'https://api.test/v1///')).toBe('https://api.test/v1/search/text');
    expect(apiUrl('admin/stats', '/api/')).toBe('/api/admin/stats');
    expect(apiUrl('products', 'api/')).toBe('/api/products');
    expect(apiUrl('health', '/')).toBe('/health');
    expect(websocketUrl('/admin/ws/logs/3', '/api/', 'https://shop.test')).toBe('wss://shop.test/api/admin/ws/logs/3');
    expect(websocketUrl('admin/ws', 'http://api.test/')).toBe('ws://api.test/admin/ws');
  });
  it('sorts each way without changing fetched data', () => {
    const items = [product('b', 20), product('a', 2)];
    expect(sortProducts(items, 'Price ascending')[0].id).toBe('a');
    expect(sortProducts(items, 'Price descending')[0].id).toBe('b');
    expect(sortProducts(items, 'Name')[0].id).toBe('a');
    expect(sortProducts(items, 'Featured')).toEqual(items);
    expect(items[0].id).toBe('b');
  });
  it('uses native sharing and falls back to clipboard', async () => {
    const native = vi.fn().mockResolvedValue();
    Object.defineProperty(navigator, 'share', { configurable: true, value: native });
    expect(await shareProduct(product('a'), 'https://shop.test/product/a')).toBe('Shared');
    expect(native).toHaveBeenCalledWith({ title: 'Dress a', url: 'https://shop.test/product/a' });
    native.mockRejectedValue(new Error('unsupported'));
    const writeText = vi.fn().mockResolvedValue();
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
    expect(await shareProduct(product('a'), 'url')).toBe('Link copied');
    writeText.mockRejectedValue(new Error('denied'));
    await expect(shareProduct(product('a'), 'url')).rejects.toThrow('Could not share');
    delete navigator.share; delete navigator.clipboard;
  });
});

it('Home shows fetch failure, retries, and sorts the loaded selection', async () => {
  fetch.mockRejectedValueOnce(new Error('offline')).mockResolvedValue(ok([product('b', 20), product('a', 2)]));
  router(<Home />);
  expect(await screen.findByRole('alert')).toHaveTextContent('offline');
  fireEvent.click(screen.getByText('Retry'));
  await screen.findByText('Dress a');
  fireEvent.click(screen.getByText('Price ascending'));
  expect(screen.getAllByText(/^Dress /)[0]).toHaveTextContent('Dress a');
  expect(screen.getByText(/Sorting covers the loaded selection/)).toBeVisible();
});

it('Home hides old products and ignores late category responses', async () => {
  const old = deferred();
  fetch.mockReturnValueOnce(old.promise).mockResolvedValue(ok([product('new')]));
  router(<Home />);
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByRole('button', { name: 'Tops', exact: true }));
  await screen.findByText('Dress new');
  await act(async () => old.resolve(ok([product('old')])));
  expect(screen.queryByText('Dress old')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Dresses', exact: true }));
  expect(screen.queryByText('Dress new')).not.toBeInTheDocument();
});

it('inventory debounces, retries failures, and clears stale detail selection', async () => {
  fetch.mockResolvedValueOnce(ok([product('a')])).mockRejectedValueOnce(new Error('inventory offline')).mockResolvedValue(ok([product('b')]));
  router(<ProductsTab />);
  fireEvent.click(await screen.findByText('Dress a'));
  await waitFor(() => expect(screen.getByRole('heading', { name: 'Dress a', level: 2 })).toBeVisible());
  const input = screen.getByPlaceholderText(/Search products semantically/);
  fireEvent.change(input, { target: { value: 'blu' } });
  fireEvent.change(input, { target: { value: 'blue' } });
  await waitFor(() => expect(screen.queryByRole('heading', { name: 'Dress a', level: 2 })).toBeNull());
  expect(fetch).toHaveBeenCalledTimes(1);
  await screen.findByRole('alert');
  fireEvent.click(screen.getByText('Retry'));
  await screen.findByText('Dress b');
  expect(fetch).toHaveBeenCalledTimes(3);
  expect(fetch.mock.calls[1][0]).toContain('q=blue');
});

function NextProduct() {
  const navigate = useNavigate();
  return <><button onClick={() => navigate('/product/b')}>Next product</button><ProductDetail /></>;
}
it('product navigation clears errors and ignores old product responses', async () => {
  const late = deferred();
  fetch.mockReturnValueOnce(late.promise).mockResolvedValue(ok(product('b')));
  render(<MemoryRouter initialEntries={['/product/a']}><Routes><Route path="/product/:id" element={<NextProduct />} /></Routes></MemoryRouter>);
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByText('Next product'));
  await screen.findByRole('heading', { name: 'Dress b' });
  await act(async () => late.resolve({ ok: false }));
  expect(screen.queryByText('Product Not Found')).toBeNull();
});
it('product recovers from an error on the next route ID', async () => {
  fetch.mockRejectedValueOnce(new Error('missing')).mockResolvedValue(ok(product('b')));
  render(<MemoryRouter initialEntries={['/product/a']}><Routes><Route path="/product/:id" element={<NextProduct />} /></Routes></MemoryRouter>);
  await screen.findByText('Product Not Found');
  fireEvent.click(screen.getByText('Next product'));
  await screen.findByRole('heading', { name: 'Dress b' });
  expect(screen.queryByText('missing')).toBeNull();
});
it('direct results visits redirect home', async () => {
  render(<MemoryRouter initialEntries={['/results']}><Routes><Route path="/results" element={<Results />} /><Route path="/" element={<p>Home destination</p>} /></Routes></MemoryRouter>);
  await screen.findByText('Home destination');
  expect(fetch).not.toHaveBeenCalled();
});
it('image previews do not launch duplicate searches and readers are cleaned up', async () => {
  let reader;
  class Reader {
    readyState = 1;
    readAsDataURL() { reader = this; }
    abort = vi.fn();
  }
  vi.stubGlobal('FileReader', Reader);
  fetch.mockResolvedValue(ok({ results: [product('image')] }));
  const view = router(<Home />, { pathname: '/results', state: { type: 'image', file: new File(['x'], 'test.png') } });
  await screen.findByText('Dress image');
  act(() => { reader.result = 'data:image/png;base64,eA=='; reader.onload(); });
  expect(fetch).toHaveBeenCalledTimes(1);
  view.unmount();
  expect(reader.abort).toHaveBeenCalled();
  expect(reader.onload).toBeNull();
});
it('category changes discard late search results', async () => {
  const late = deferred();
  fetch.mockReset().mockResolvedValueOnce(ok({ results: [product('initial')] })).mockReturnValueOnce(late.promise).mockResolvedValue(ok({ results: [product('latest')] }));
  router(<Home />, { pathname: '/results', state: { type: 'text', query: 'dress' } });
  await screen.findByText('Dress initial');
  fireEvent.click(screen.getByText('Tops'));
  expect(screen.queryByText('Dress initial')).toBeNull();
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  // A newer category request supersedes the pending response.
  fireEvent.click(screen.getByText('Dresses'));
  await screen.findByText('Dress latest');
  await act(async () => late.resolve(ok({ results: [product('late')] })));
  expect(screen.queryByText('Dress late')).toBeNull();
});
it('inspiration chips and onboarding selections launch text searches', async () => {
  fetch.mockResolvedValue(ok({ results: [] }));
  const view = router(<Home />);
  fireEvent.click(screen.getByText('Linen blazer'));
  await waitFor(() => expect(fetch).toHaveBeenCalled());
  expect(fetch.mock.calls.at(-1)[1].body.get('query')).toBe('Linen blazer');
  view.unmount(); fetch.mockClear();
  router(<Onboarding />);
  fireEvent.click(screen.getByRole('button', { name: 'Streetwear' }));
  fireEvent.click(screen.getByText('Start Finding'));
  await waitFor(() => expect(fetch).toHaveBeenCalled());
  expect(fetch.mock.calls[0][1].body.get('query')).toBe('Streetwear');
});
it('Find Similar searches by name and share errors are visible', async () => {
  fetch.mockResolvedValueOnce(ok(product('a'))).mockResolvedValue(ok({ results: [] }));
  Object.defineProperty(navigator, 'share', { configurable: true, value: undefined });
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: undefined });
  router(<Home />, '/product/a');
  await screen.findByRole('heading', { name: 'Dress a' });
  fireEvent.click(screen.getByRole('button', { name: 'Share product' }));
  expect(await screen.findByRole('status')).toHaveTextContent('Sharing unavailable');
  fireEvent.click(screen.getByText('Find Similar Items'));
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(fetch.mock.calls[1][1].body.get('query')).toBe('Dress a');
});

it('favorite state follows Home, Results, and product navigation', async () => {
  const item = product('cross-page');
  fetch.mockImplementation(url => Promise.resolve(ok(url.includes('/search/') ? { results: [item] } : url.includes('/products?') ? [item] : item)));
  router(<Home />);
  fireEvent.click(await screen.findByRole('button', { name: 'Save Dress cross-page' }));
  fireEvent.click(screen.getByText('Linen blazer'));
  expect(await screen.findByRole('button', { name: 'Unsave Dress cross-page' })).toHaveAttribute('aria-pressed', 'true');
  fireEvent.click(screen.getByText('Dress cross-page'));
  const unsave = await screen.findByRole('button', { name: 'Unsave Dress cross-page' });
  fireEvent.click(unsave);
  expect(screen.getByRole('button', { name: 'Save Dress cross-page' })).toHaveAttribute('aria-pressed', 'false');
});

it('Results displays failed search feedback and retries', async () => {
  fetch.mockRejectedValueOnce(new Error('search offline')).mockResolvedValue(ok({ results: [product('retry')] }));
  router(<Home />, { pathname: '/results', state: { type: 'text', query: 'dress' } });
  expect(await screen.findByRole('alert')).toHaveTextContent('search offline');
  fireEvent.click(screen.getByText('Retry'));
  await screen.findByText('Dress retry');
});

it('inventory ignores an older response after a newer query completes', async () => {
  const old = deferred();
  fetch.mockReturnValueOnce(old.promise).mockResolvedValue(ok([product('new-inventory')]));
  router(<ProductsTab />);
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  fireEvent.change(screen.getByPlaceholderText(/Search products semantically/), { target: { value: 'new' } });
  await screen.findByText('Dress new-inventory');
  await act(async () => old.resolve(ok([product('old-inventory')])));
  expect(screen.queryByText('Dress old-inventory')).toBeNull();
});
