import { useState, useEffect, useCallback } from 'react';
import { fetchTimeseries, type AnalyticsFilters } from '../api/analytics';
import type { TimeSeriesPoint } from '../types/analytics';

export function useTimeseries(filters: AnalyticsFilters = {}) {
  const [data, setData] = useState<TimeSeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchTimeseries(filters, signal);
      setData(result);
    } catch (e) {
      if ((e as Error).name === 'AbortError') return;
      setError(e as Error);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [filters.started_after, filters.started_before, filters.environment]);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  return { data, loading, error, refetch: () => load() };
}
