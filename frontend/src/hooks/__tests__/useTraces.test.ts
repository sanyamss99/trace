import { renderHook, waitFor } from '@testing-library/react';
import { useTraces } from '../useTraces';
import { fetchTraces } from '../../api/traces';

vi.mock('../../api/traces');

const mockFetchTraces = vi.mocked(fetchTraces);

describe('useTraces', () => {
  beforeEach(() => {
    mockFetchTraces.mockReset();
  });

  it('loads traces and transitions from loading to loaded', async () => {
    mockFetchTraces.mockResolvedValue({
      traces: [
        {
          id: 'tr-1',
          function_name: 'test_fn',
          status: 'ok',
          started_at: '2025-01-01T00:00:00Z',
          ended_at: '2025-01-01T00:00:01Z',
          duration_ms: 100,
          total_tokens: 50,
          total_cost_usd: 0.01,
          environment: 'dev',
          tags: null,
          span_count: 1,
        },
      ],
      next_cursor: null,
      limit: 50,
    });

    const { result } = renderHook(() => useTraces());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.traces).toHaveLength(1);
    expect(result.current.traces[0].id).toBe('tr-1');
    expect(result.current.error).toBeNull();
    expect(result.current.hasMore).toBe(false);
  });

  it('sets error state when fetch rejects', async () => {
    mockFetchTraces.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useTraces());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error?.message).toBe('Network error');
    expect(result.current.traces).toHaveLength(0);
  });

  it('aborts request on unmount', async () => {
    let capturedSignal: AbortSignal | undefined;

    mockFetchTraces.mockImplementation(async (_filters, signal) => {
      capturedSignal = signal;
      return new Promise(() => {}); // never resolves
    });

    const { unmount } = renderHook(() => useTraces());

    await waitFor(() => expect(capturedSignal).toBeDefined());

    unmount();

    expect(capturedSignal!.aborted).toBe(true);
  });
});
