import { ApiError, apiFetch } from '../client';

describe('ApiError', () => {
  it('sets status, statusText, body, and message', () => {
    const error = new ApiError(404, 'Not Found', { detail: 'gone' });
    expect(error.status).toBe(404);
    expect(error.statusText).toBe('Not Found');
    expect(error.body).toEqual({ detail: 'gone' });
    expect(error.message).toBe('404 Not Found');
    expect(error.name).toBe('ApiError');
  });
});

describe('apiFetch', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('makes a GET request and returns parsed JSON', async () => {
    const data = { id: '1', name: 'test' };
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(data),
    } as Response);

    const result = await apiFetch('/traces');

    expect(fetch).toHaveBeenCalledWith(
      '/api/traces',
      expect.objectContaining({
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          Accept: 'application/json',
        }),
      }),
    );
    expect(result).toEqual(data);
  });

  it('includes X-Trace-Key header when API key is set', async () => {
    vi.mocked(Storage.prototype.getItem).mockReturnValue('tr-test-key');
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    } as Response);

    await apiFetch('/traces');

    expect(fetch).toHaveBeenCalledWith(
      '/api/traces',
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-Trace-Key': 'tr-test-key',
        }),
      }),
    );
  });

  it('throws ApiError when response is not ok', async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: () => Promise.resolve({ detail: 'bad key' }),
    } as unknown as Response);

    await expect(apiFetch('/traces')).rejects.toThrow(ApiError);

    try {
      await apiFetch('/traces');
    } catch (e) {
      const err = e as ApiError;
      expect(err.status).toBe(401);
      expect(err.body).toEqual({ detail: 'bad key' });
    }
  });

  it('passes signal through to fetch', async () => {
    const controller = new AbortController();
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    } as Response);

    await apiFetch('/traces', { signal: controller.signal });

    expect(fetch).toHaveBeenCalledWith(
      '/api/traces',
      expect.objectContaining({
        signal: controller.signal,
      }),
    );
  });
});
