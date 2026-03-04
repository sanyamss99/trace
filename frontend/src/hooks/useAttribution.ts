import { useState, useCallback } from 'react';
import { fetchAttribution } from '../api/traces';
import type { AttributionResponse } from '../types/traces';

export function useAttribution() {
  const [data, setData] = useState<AttributionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async (spanId: string, force = false) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchAttribution(spanId, force);
      setData(result);
    } catch (e) {
      setError(e as Error);
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setData(null);
    setError(null);
  }, []);

  return { data, loading, error, load, clear };
}
