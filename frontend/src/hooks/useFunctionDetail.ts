import { useState, useEffect, useCallback } from 'react';
import { fetchFunctionDetail, type AnalyticsFilters } from '../api/analytics';
import type { FunctionDetail } from '../types/analytics';

export function useFunctionDetail(
  functionName: string | null,
  filters: AnalyticsFilters = {},
) {
  const [data, setData] = useState<FunctionDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    if (!functionName) {
      setData(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await fetchFunctionDetail(
        { ...filters, function_name: functionName },
        signal,
      );
      setData(result);
    } catch (e) {
      if ((e as Error).name === 'AbortError') return;
      setError(e as Error);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [functionName, filters.started_after, filters.started_before, filters.environment]);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  return { data, loading, error, refetch: () => load() };
}
