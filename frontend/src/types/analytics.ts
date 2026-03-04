export interface OverviewStats {
  trace_count: number;
  total_tokens: number | null;
  total_cost_usd: number | null;
  avg_duration_ms: number | null;
  error_count: number;
  error_rate: number;
}

export interface TimeSeriesPoint {
  date: string;
  trace_count: number;
  total_cost_usd: number | null;
  error_count: number;
}

export interface FunctionCostItem {
  function_name: string;
  call_count: number;
  total_tokens: number | null;
  total_cost_usd: number | null;
  avg_cost_usd: number | null;
  avg_duration_ms: number | null;
  error_count: number;
}
