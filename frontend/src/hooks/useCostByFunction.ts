import { useState, useEffect, useCallback } from 'react';
import { fetchCostByFunction, type AnalyticsFilters } from '../api/analytics';
import type { FunctionCostItem } from '../types/analytics';

export function useCostByFunction(filters: AnalyticsFilters = {}) {
  const [data, setData] = useState<FunctionCostItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchCostByFunction(filters);
      setData(result);
    } catch (e) {
      setError(e as Error);
    } finally {
      setLoading(false);
    }
  }, [filters.started_after, filters.started_before, filters.environment]);

  useEffect(() => { load(); }, [load]);

  return { data, loading, error, refetch: load };
}
