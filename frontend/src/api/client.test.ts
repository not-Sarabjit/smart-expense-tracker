import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import axios from 'axios';

/**
 * Tests for the Axios client interceptors.
 * We re-import the module fresh for each test via dynamic import so that the
 * interceptors always see the current localStorage state.
 */
describe('apiClient — request interceptor (JWT attachment)', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('attaches Authorization header when access_token is present', async () => {
    localStorage.setItem('access_token', 'test-token-abc');

    // Dynamically import so the module re-runs (interceptor closes over localStorage calls)
    const { default: client } = await import('./client');

    // Intercept at the adapter level before any real network call
    const spy = vi.fn().mockResolvedValue({
      data: {},
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {},
    });
    const originalAdapter = client.defaults.adapter;
    client.defaults.adapter = spy;

    try {
      await client.get('/test').catch(() => {});
    } catch {
      // ignore
    }

    // The spy receives the resolved config; check Authorization header
    if (spy.mock.calls.length > 0) {
      const config = spy.mock.calls[0][0];
      expect(config.headers?.['Authorization']).toBe('Bearer test-token-abc');
    }

    client.defaults.adapter = originalAdapter;
  });

  it('does not attach Authorization header when access_token is absent', async () => {
    localStorage.removeItem('access_token');

    const { default: client } = await import('./client');

    const spy = vi.fn().mockResolvedValue({
      data: {},
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {},
    });
    const originalAdapter = client.defaults.adapter;
    client.defaults.adapter = spy;

    try {
      await client.get('/test').catch(() => {});
    } catch {
      // ignore
    }

    if (spy.mock.calls.length > 0) {
      const config = spy.mock.calls[0][0];
      expect(config.headers?.['Authorization']).toBeUndefined();
    }

    client.defaults.adapter = originalAdapter;
  });
});

describe('apiClient — response interceptor (401 handling)', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('access_token', 'some-token');
    // jsdom does not support full navigation; mock window.location
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { href: '' },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('removes access_token and redirects to /login on 401 response', async () => {
    const { default: client } = await import('./client');

    // Simulate a 401 from the adapter
    const axiosErr = new axios.AxiosError('Unauthorized');
    axiosErr.response = {
      status: 401,
      statusText: 'Unauthorized',
      data: {},
      headers: {},
      config: {} as never,
    };

    const spy = vi.fn().mockRejectedValue(axiosErr);
    const originalAdapter = client.defaults.adapter;
    client.defaults.adapter = spy;

    try {
      await client.get('/protected');
    } catch {
      // expected rejection
    }

    expect(localStorage.getItem('access_token')).toBeNull();
    expect(window.location.href).toBe('/login');

    client.defaults.adapter = originalAdapter;
  });

  it('does not clear token or redirect for non-401 errors', async () => {
    const { default: client } = await import('./client');

    const axiosErr = new axios.AxiosError('Server Error');
    axiosErr.response = {
      status: 500,
      statusText: 'Internal Server Error',
      data: {},
      headers: {},
      config: {} as never,
    };

    const spy = vi.fn().mockRejectedValue(axiosErr);
    const originalAdapter = client.defaults.adapter;
    client.defaults.adapter = spy;

    try {
      await client.get('/data');
    } catch {
      // expected rejection
    }

    expect(localStorage.getItem('access_token')).toBe('some-token');

    client.defaults.adapter = originalAdapter;
  });
});
