import { useState, useEffect, useCallback } from 'react';
import { fetchTrace } from '../api/traces';
import type { TraceDetail } from '../types/traces';

export function useTraceDetail(traceId: string) {
  const [data, setData] = useState<TraceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchTrace(traceId);
      setData(result);
    } catch (e) {
      setError(e as Error);
    } finally {
      setLoading(false);
    }
  }, [traceId]);

  useEffect(() => { load(); }, [load]);

  return { data, loading, error, refetch: load };
}
