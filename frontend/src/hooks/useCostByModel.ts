import { useState, useEffect, useCallback } from 'react';
import { fetchCostByModel, type AnalyticsFilters } from '../api/analytics';
import type { ModelCostItem } from '../types/analytics';

export function useCostByModel(filters: AnalyticsFilters = {}) {
  const [data, setData] = useState<ModelCostItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchCostByModel(filters, signal);
      setData(result);
    } catch (e) {
      if ((e as Error).name === 'AbortError') return;
      setError(e as Error);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [filters.started_after, filters.started_before, filters.environment, filters.function_name]);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  return { data, loading, error, refetch: () => load() };
}
