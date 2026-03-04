import { useState, useEffect, useCallback } from 'react';
import { fetchApiKeys, createApiKey, revokeApiKey } from '../api/apiKeys';
import type { ApiKey, ApiKeyCreated } from '../types/apiKeys';

export function useApiKeys() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchApiKeys();
      setKeys(result);
    } catch (e) {
      setError(e as Error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const create = useCallback(async (name: string): Promise<ApiKeyCreated> => {
    const created = await createApiKey(name);
    await load();
    return created;
  }, [load]);

  const revoke = useCallback(async (keyId: string) => {
    await revokeApiKey(keyId);
    await load();
  }, [load]);

  return { keys, loading, error, create, revoke, refetch: load };
}
