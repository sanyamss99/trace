import { useState, useEffect, useCallback } from 'react';
import { fetchTrace } from '../api/traces';
import type { TraceDetail } from '../types/traces';

export function useTraceDetail(traceId: string) {
  const [data, setData] = useState<TraceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchTrace(traceId, signal);
      setData(result);
    } catch (e) {
      if ((e as Error).name === 'AbortError') return;
      setError(e as Error);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [traceId]);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  return { data, loading, error, refetch: () => load() };
}
