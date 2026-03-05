const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

export class ApiError extends Error {
  status: number;
  statusText: string;
  body: unknown;

  constructor(status: number, statusText: string, body: unknown) {
    super(`${status} ${statusText}`);
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
    this.body = body;
  }
}

function getAuthHeaders(): Record<string, string> {
  const authType = localStorage.getItem('trace_auth_type');
  if (authType === 'jwt') {
    const token = localStorage.getItem('trace_jwt');
    if (token) return { Authorization: `Bearer ${token}` };
  }
  // Fall back to API key (also handles legacy case with no auth_type set)
  const apiKey = localStorage.getItem('trace_api_key');
  if (apiKey) return { 'X-Trace-Key': apiKey };
  return {};
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...getAuthHeaders(),
    ...((options.headers as Record<string, string>) ?? {}),
  };

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, res.statusText, body);
  }

  return res.json() as Promise<T>;
}
