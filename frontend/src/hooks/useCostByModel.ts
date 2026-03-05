import { useState, useEffect, useCallback } from 'react';
import { fetchCostByModel, type AnalyticsFilters } from '../api/analytics';
import type { ModelCostItem } from '../types/analytics';

export function useCostByModel(filters: AnalyticsFilters = {}) {
  const [data, setData] = useState<ModelCostItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchCostByModel(filters);
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
