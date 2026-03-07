import { apiFetch } from './client';
import type {
  OverviewStats,
  TimeSeriesPoint,
  FunctionCostItem,
  ModelCostItem,
  FunctionDetail,
} from '../types/analytics';

export interface AnalyticsFilters {
  started_after?: string;
  started_before?: string;
  environment?: string;
  function_name?: string;
}

function buildQuery(filters: AnalyticsFilters): string {
  const params = new URLSearchParams();

  if (filters.started_after) params.set('started_after', filters.started_after);
  if (filters.started_before) params.set('started_before', filters.started_before);
  if (filters.environment) params.set('environment', filters.environment);
  if (filters.function_name) params.set('function_name', filters.function_name);
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

export async function fetchOverview(
  filters: AnalyticsFilters = {},
  signal?: AbortSignal,
): Promise<OverviewStats> {
  return apiFetch<OverviewStats>(
    `/traces/analytics/overview${buildQuery(filters)}`,
    { signal },
  );
}

export async function fetchTimeseries(
  filters: AnalyticsFilters = {},
  signal?: AbortSignal,
): Promise<TimeSeriesPoint[]> {
  return apiFetch<TimeSeriesPoint[]>(
    `/traces/analytics/timeseries${buildQuery(filters)}`,
    { signal },
  );
}

export async function fetchCostByFunction(
  filters: AnalyticsFilters = {},
  signal?: AbortSignal,
): Promise<FunctionCostItem[]> {
  return apiFetch<FunctionCostItem[]>(
    `/traces/analytics/cost-by-function${buildQuery(filters)}`,
    { signal },
  );
}

export async function fetchCostByModel(
  filters: AnalyticsFilters = {},
  signal?: AbortSignal,
): Promise<ModelCostItem[]> {
  return apiFetch<ModelCostItem[]>(
    `/traces/analytics/cost-by-model${buildQuery(filters)}`,
    { signal },
  );
}

export async function fetchFunctionDetail(
  filters: AnalyticsFilters & { function_name: string },
  signal?: AbortSignal,
): Promise<FunctionDetail> {
  return apiFetch<FunctionDetail>(
    `/traces/analytics/function-detail${buildQuery(filters)}`,
    { signal },
  );
}
