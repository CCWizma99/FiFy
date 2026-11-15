import { render } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import CrawlerConsole from '../components/admin/CrawlerConsole';
afterEach(() => vi.unstubAllEnvs());
it('uses one configured prefix in search, admin, and websocket callers', async () => {
  vi.stubEnv('VITE_API_URL', '/api/');
  vi.resetModules();
  const search = await import('../api/search');
  const admin = await import('../api/admin');
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
  await search.getAllProducts();
  await admin.getScraperStats();
  expect(fetch.mock.calls[0][0]).toBe('/api/products?limit=20');
  expect(fetch.mock.calls[1][0]).toBe('/api/admin/stats');
  const connect = vi.fn();
  class Socket { constructor(url) { connect(url); } close() {} }
  vi.stubGlobal('WebSocket', Socket);
  render(<CrawlerConsole site={{ id: 12, domain: 'example.test' }} onClose={() => {}} />);
  expect(connect).toHaveBeenCalledWith('ws://localhost:3000/api/admin/ws/logs/12');
});
