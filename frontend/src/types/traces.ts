export interface SpanSegment {
  id: string;
  segment_name: string;
  segment_type: string;
  segment_text: string;
  position_start: number | null;
  position_end: number | null;
  retrieval_rank: number | null;
  influence_score: number | null;
  utilization_score: number | null;
  attribution_method: string | null;
}

export interface LogprobEntry {
  token: string;
  logprob: number;
}

export interface Span {
  id: string;
  trace_id: string;
  parent_span_id: string | null;
  function_name: string;
  span_type: string;
  model: string | null;
  started_at: string;
  ended_at: string;
  duration_ms: number | null;
  prompt_text: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  completion_text: string | null;
  completion_logprobs: LogprobEntry[] | null;
  cost_usd: number | null;
  input_locals: Record<string, unknown> | null;
  output: unknown | null;
  error: string | null;
  span_metadata: Record<string, unknown> | null;
  segments: SpanSegment[];
}

export interface TraceListItem {
  id: string;
  function_name: string;
  environment: string;
  started_at: string;
  ended_at: string;
  duration_ms: number | null;
  total_tokens: number | null;
  total_cost_usd: number | null;
  status: string;
  tags: Record<string, unknown> | null;
  span_count: number;
}

export interface PaginatedTraceList {
  traces: TraceListItem[];
  next_cursor: string | null;
  limit: number;
}

export interface TraceDetail {
  id: string;
  function_name: string;
  environment: string;
  started_at: string;
  ended_at: string;
  duration_ms: number | null;
  total_tokens: number | null;
  total_cost_usd: number | null;
  status: string;
  tags: Record<string, unknown> | null;
  spans: Span[];
}

export interface AttributionResponse {
  span_id: string;
  method: string;
  segments: SpanSegment[];
}
