import { useState, useCallback, useRef, useEffect } from 'react';
import { fetchAttribution } from '../api/traces';
import type { AttributionResponse } from '../types/traces';

export function useAttribution() {
  const [data, setData] = useState<AttributionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  const load = useCallback(async (spanId: string, force = false) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setLoading(true);
    setError(null);
    try {
      const result = await fetchAttribution(spanId, force, controller.signal);
      setData(result);
    } catch (e) {
      if ((e as Error).name === 'AbortError') return;
      setError(e as Error);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    controllerRef.current?.abort();
    setData(null);
    setError(null);
  }, []);

  useEffect(() => () => controllerRef.current?.abort(), []);

  return { data, loading, error, load, clear };
}
