import { apiFetch } from './client';
import type {
  PaginatedTraceList,
  TraceDetail,
  Span,
  AttributionResponse,
} from '../types/traces';

export interface TraceFilters {
  limit?: number;
  cursor?: string;
  function_name?: string;
  environment?: string;
  status?: string;
  started_after?: string;
  started_before?: string;
}

export async function fetchTraces(
  filters: TraceFilters = {},
): Promise<PaginatedTraceList> {
  const params = new URLSearchParams();
  if (filters.limit) params.set('limit', String(filters.limit));
  if (filters.cursor) params.set('cursor', filters.cursor);
  if (filters.function_name) params.set('function_name', filters.function_name);
  if (filters.environment) params.set('environment', filters.environment);
  if (filters.status) params.set('status', filters.status);
  if (filters.started_after) params.set('started_after', filters.started_after);
  if (filters.started_before) params.set('started_before', filters.started_before);
  const qs = params.toString();
  return apiFetch<PaginatedTraceList>(`/traces${qs ? `?${qs}` : ''}`);
}

export async function fetchTrace(traceId: string): Promise<TraceDetail> {
  return apiFetch<TraceDetail>(`/traces/${traceId}`);
}

export async function fetchSpan(spanId: string): Promise<Span> {
  return apiFetch<Span>(`/traces/spans/${spanId}`);
}

export async function fetchAttribution(
  spanId: string,
  force = false,
): Promise<AttributionResponse> {
  const qs = force ? '?force=true' : '';
  return apiFetch<AttributionResponse>(
    `/traces/spans/${spanId}/attribution${qs}`,
  );
}
