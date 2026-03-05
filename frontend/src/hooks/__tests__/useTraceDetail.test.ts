import { renderHook, waitFor } from '@testing-library/react';
import { useTraceDetail } from '../useTraceDetail';
import { fetchTrace } from '../../api/traces';

vi.mock('../../api/traces');

const mockFetchTrace = vi.mocked(fetchTrace);

describe('useTraceDetail', () => {
  beforeEach(() => {
    mockFetchTrace.mockReset();
  });

  it('fetches trace detail and sets data', async () => {
    mockFetchTrace.mockResolvedValue({
      id: 'tr-1',
      function_name: 'test_fn',
      status: 'ok',
      started_at: '2025-01-01T00:00:00Z',
      ended_at: '2025-01-01T00:00:01Z',
      duration_ms: 200,
      total_tokens: 100,
      total_cost_usd: 0.05,
      environment: 'dev',
      tags: null,
      spans: [],
    });

    const { result } = renderHook(() => useTraceDetail('tr-1'));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data?.id).toBe('tr-1');
    expect(result.current.error).toBeNull();
  });

  it('sets error state on fetch failure', async () => {
    mockFetchTrace.mockRejectedValue(new Error('Not found'));

    const { result } = renderHook(() => useTraceDetail('tr-bad'));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error?.message).toBe('Not found');
    expect(result.current.data).toBeNull();
  });
});
