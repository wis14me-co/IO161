import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock fetch globally
global.fetch = vi.fn();

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
global.localStorage = localStorageMock;

// Mock document
global.document = {
  querySelector: vi.fn(),
  cookie: '',
  head: {
    innerHTML: ''
  }
};

// Import the api module
import * as apiModule from '../../app/static/js/api.js';

describe('API Client', () => {
  let api;

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset CSRF token meta tag
    global.document.head.innerHTML = '<meta name="csrf-token" content="test-csrf-token">';
    global.document.querySelector.mockImplementation((selector) => {
      if (selector === 'meta[name="csrf-token"]') {
        return { content: 'test-csrf-token' };
      }
      return null;
    });
    global.document.cookie = '';
    localStorageMock.getItem.mockReturnValue(null);
    
    // Get fresh api instance
    api = apiModule.window?.api || new apiModule.ApiClient();
  });

  describe('ApiClient', () => {
    it('should make GET request with correct headers', async () => {
      const mockResponse = { data: 'test' };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: { get: () => 'application/json' }
      });

      const result = await api.get('/api/test');
      
      expect(global.fetch).toHaveBeenCalledWith('/api/test', expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-CSRF-Token': 'test-csrf-token'
        })
      }));
      expect(result).toEqual(mockResponse);
    });

    it('should include Authorization header when token exists', async () => {
      localStorageMock.getItem.mockReturnValue('test-token');
      // Create new instance to pick up token
      api = new apiModule.ApiClient();
      
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({}),
        headers: { get: () => 'application/json' }
      });

      await api.get('/api/test');
      
      expect(global.fetch).toHaveBeenCalledWith('/api/test', expect.objectContaining({
        headers: expect.objectContaining({
          'Authorization': 'Bearer test-token'
        })
      }));
    });

    it('should throw ApiError on non-ok response', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ code: 'unauthenticated', message: 'Invalid token' }),
        headers: { get: () => 'application/json' }
      });

      await expect(api.get('/api/test')).rejects.toThrow('Invalid token');
    });

    it('should make POST request with body', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
        headers: { get: () => 'application/json' }
      });

      const result = await api.post('/api/test', { key: 'value' });
      expect(result).toEqual({ success: true });
      
      expect(global.fetch).toHaveBeenCalledWith('/api/test', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ key: 'value' })
      }));
    });
  });

  describe('ApiError', () => {
    it('should have correct properties', () => {
      const error = new apiModule.ApiError(401, 'unauthenticated', 'Invalid token', {});
      expect(error.status).toBe(401);
      expect(error.code).toBe('unauthenticated');
      expect(error.message).toBe('Invalid token');
      expect(error.name).toBe('ApiError');
    });
  });
});