import { useState, useEffect, useCallback } from 'react';
import { fetchTraces, type TraceFilters } from '../api/traces';
import type { TraceListItem } from '../types/traces';

export function useTraces(filters: Omit<TraceFilters, 'cursor'> = {}) {
  const [traces, setTraces] = useState<TraceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchTraces(filters, signal);
      setTraces(result.traces);
      setNextCursor(result.next_cursor);
    } catch (e) {
      if ((e as Error).name === 'AbortError') return;
      setError(e as Error);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [filters.function_name, filters.environment, filters.status, filters.started_after, filters.started_before, filters.limit]);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const loadMore = useCallback(async () => {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const result = await fetchTraces({ ...filters, cursor: nextCursor });
      setTraces((prev) => [...prev, ...result.traces]);
      setNextCursor(result.next_cursor);
    } catch (e) {
      setError(e as Error);
    } finally {
      setLoadingMore(false);
    }
  }, [nextCursor, filters, loadingMore]);

  return {
    traces,
    loading,
    loadingMore,
    error,
    hasMore: nextCursor !== null,
    loadMore,
    refetch: () => load(),
  };
}
