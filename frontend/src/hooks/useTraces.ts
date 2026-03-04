import { useState, useEffect, useCallback } from 'react';
import { fetchTraces, type TraceFilters } from '../api/traces';
import type { TraceListItem } from '../types/traces';

export function useTraces(filters: Omit<TraceFilters, 'cursor'> = {}) {
  const [traces, setTraces] = useState<TraceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchTraces(filters);
      setTraces(result.traces);
      setNextCursor(result.next_cursor);
    } catch (e) {
      setError(e as Error);
    } finally {
      setLoading(false);
    }
  }, [filters.function_name, filters.environment, filters.status, filters.started_after, filters.started_before, filters.limit]);

  useEffect(() => { load(); }, [load]);

  const loadMore = useCallback(async () => {
    if (!nextCursor) return;
    try {
      const result = await fetchTraces({ ...filters, cursor: nextCursor });
      setTraces((prev) => [...prev, ...result.traces]);
      setNextCursor(result.next_cursor);
    } catch (e) {
      setError(e as Error);
    }
  }, [nextCursor, filters]);

  return {
    traces,
    loading,
    error,
    hasMore: nextCursor !== null,
    loadMore,
    refetch: load,
  };
}
