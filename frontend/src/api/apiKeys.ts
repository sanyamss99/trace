import { apiFetch } from './client';
import type { ApiKey, ApiKeyCreated } from '../types/apiKeys';

export async function fetchApiKeys(): Promise<ApiKey[]> {
  return apiFetch<ApiKey[]>('/api-keys');
}

export async function createApiKey(name: string): Promise<ApiKeyCreated> {
  return apiFetch<ApiKeyCreated>('/api-keys', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

export async function revokeApiKey(keyId: string): Promise<ApiKey> {
  return apiFetch<ApiKey>(`/api-keys/${keyId}`, {
    method: 'DELETE',
  });
}
