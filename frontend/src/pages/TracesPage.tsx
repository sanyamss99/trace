import { useState, useMemo, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import clsx from 'clsx';
import { useTraces } from '../hooks/useTraces';
import { useCostByFunction } from '../hooks/useCostByFunction';
import { useFunctionDetail } from '../hooks/useFunctionDetail';
import { useCostByModel } from '../hooks/useCostByModel';
import { StatusBadge } from '../components/StatusBadge';
import { Pagination } from '../components/Pagination';
import { DateRangeFilter, type DateRange } from '../components/DateRangeFilter';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { EmptyState } from '../components/EmptyState';
import { formatCost, formatDuration, formatTokens, formatDatePrecise } from '../utils/formatters';
import type { FunctionCostItem, FunctionDetail, ModelCostItem } from '../types/analytics';

const MODEL_COLORS = ['var(--raw-accent)', '#0ea5e9', '#a855f7', '#f59e0b'];

function FunctionSummaryCards({
  item,
  detail,
  modelCosts,
}: {
  item: FunctionCostItem;
  detail: FunctionDetail | null;
  modelCosts: ModelCostItem[];
}) {
  const successRate = item.call_count > 0
    ? ((item.call_count - item.error_count) / item.call_count * 100).toFixed(1)
    : '100.0';

  const statuses = detail?.recent_statuses ?? [];
  const failureCount = statuses.filter((s) => s === 'error').length;

  const p = detail?.percentiles ?? null;
  const hasPercentiles = p !== null && p.p50 !== null;
  const percentileBars = hasPercentiles
    ? [
        { label: 'p50', value: p!.p50!, color: 'var(--raw-success)' },
        { label: 'p90', value: p!.p90!, color: 'var(--raw-warning)' },
        { label: 'p99', value: p!.p99!, color: 'var(--raw-error)' },
      ]
    : [];
  const maxLatency = Math.max(...percentileBars.map((b) => b.value), 1);

  const topModels = modelCosts.slice(0, 4);
  const maxModelCost = Math.max(...topModels.map((m) => m.total_cost_usd ?? 0), 0.0001);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {/* Cost */}
      <div className="bg-surface-secondary border border-border rounded-lg p-5">
        <h3 className="text-sm font-medium text-text-primary">Cost</h3>
        <p className="text-xs text-text-muted mb-3">Average per call</p>
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-2xl font-semibold text-text-primary">
            {formatCost(item.avg_cost_usd)}
          </span>
          <span className="text-xs text-text-muted">/call</span>
        </div>
        {topModels.length > 0 ? (
          <div className="mt-3 space-y-2">
            {topModels.map((m, i) => (
              <div key={m.model} className="space-y-0.5">
                <div className="flex justify-between text-[11px]">
                  <span className="text-text-secondary truncate">{m.model}</span>
                  <span className="font-mono text-text-muted">{formatTokens(m.total_tokens)}</span>
                </div>
                <div className="h-1.5 bg-surface-tertiary rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${((m.total_cost_usd ?? 0) / maxModelCost) * 100}%`,
                      backgroundColor: MODEL_COLORS[i % MODEL_COLORS.length],
                      opacity: 0.6,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-3 text-xs text-text-secondary space-y-1">
            <div className="flex justify-between">
              <span>Total cost</span>
              <span className="font-mono">{formatCost(item.total_cost_usd)}</span>
            </div>
            <div className="flex justify-between">
              <span>Total tokens</span>
              <span className="font-mono">{formatTokens(item.total_tokens)}</span>
            </div>
          </div>
        )}
      </div>

      {/* Reliability */}
      <div className="bg-surface-secondary border border-border rounded-lg p-5">
        <h3 className="text-sm font-medium text-text-primary">Reliability</h3>
        <p className="text-xs text-text-muted mb-3">Success rate</p>
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-2xl font-semibold text-success">
            {successRate}%
          </span>
          <span className="text-xs text-text-muted">success</span>
        </div>
        {statuses.length > 0 ? (
          <>
            <div className="mt-3 grid grid-cols-10 gap-0.5">
              {statuses.map((s, i) => (
                <div
                  key={i}
                  className={clsx(
                    'h-4 rounded-sm',
                    s === 'error' ? 'bg-error/80' : 'bg-success/50',
                  )}
                />
              ))}
            </div>
            <div className="mt-2 text-xs text-text-secondary flex justify-between">
              <span>last {statuses.length} calls</span>
              {failureCount > 0 && (
                <span className="text-error">{failureCount} failures</span>
              )}
            </div>
          </>
        ) : (
          <>
            <div className="mt-3 flex gap-0.5 h-2 rounded overflow-hidden">
              {item.call_count > 0 && (item.call_count - item.error_count) > 0 && (
                <div
                  className="bg-success/50 rounded-l"
                  style={{ width: `${((item.call_count - item.error_count) / item.call_count) * 100}%` }}
                />
              )}
              {item.error_count > 0 && (
                <div
                  className="bg-error rounded-r"
                  style={{ width: `${(item.error_count / item.call_count) * 100}%` }}
                />
              )}
            </div>
            <div className="mt-2 text-xs text-text-secondary flex justify-between">
              <span>{item.call_count} calls</span>
              {item.error_count > 0 && (
                <span className="text-error">{item.error_count} failures</span>
              )}
            </div>
          </>
        )}
      </div>

      {/* Latency */}
      <div className="bg-surface-secondary border border-border rounded-lg p-5">
        <h3 className="text-sm font-medium text-text-primary">Latency</h3>
        <p className="text-xs text-text-muted mb-3">
          {hasPercentiles ? 'Percentile breakdown' : 'Average response time'}
        </p>
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-2xl font-semibold text-text-primary">
            {formatDuration(hasPercentiles ? p!.p50 : item.avg_duration_ms)}
          </span>
          <span className="text-xs text-text-muted">{hasPercentiles ? 'median' : 'avg'}</span>
        </div>
        {hasPercentiles && (
          <div className="mt-3 space-y-2">
            {percentileBars.map((bar) => (
              <div key={bar.label} className="space-y-0.5">
                <div className="flex justify-between text-[11px] font-mono text-text-muted">
                  <span>{bar.label}</span>
                  <span>{formatDuration(bar.value)}</span>
                </div>
                <div className="h-2 bg-surface-tertiary rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(bar.value / maxLatency) * 100}%`,
                      backgroundColor: bar.color,
                      opacity: 0.6,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function TracesPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get('function_name') ?? '');
  const [statusFilter, setStatusFilter] = useState<string | undefined>(
    searchParams.get('status') ?? undefined,
  );

  const dateRange = useMemo<DateRange>(() => ({
    started_after: searchParams.get('started_after') ?? undefined,
    started_before: searchParams.get('started_before') ?? undefined,
  }), [searchParams]);

  const setDateRange = useCallback((range: DateRange) => {
    const next = new URLSearchParams(searchParams);
    if (range.started_after) next.set('started_after', range.started_after);
    else next.delete('started_after');
    if (range.started_before) next.set('started_before', range.started_before);
    else next.delete('started_before');
    setSearchParams(next);
  }, [searchParams, setSearchParams]);

  const functionNameParam = searchParams.get('function_name');

  const analyticsFilters = useMemo(() => ({
    started_after: dateRange.started_after,
    started_before: dateRange.started_before,
  }), [dateRange.started_after, dateRange.started_before]);

  const costByFn = useCostByFunction(analyticsFilters);
  const functionItem = useMemo(() => {
    if (!functionNameParam || costByFn.loading) return null;
    return costByFn.data.find((f) => f.function_name === functionNameParam) ?? null;
  }, [functionNameParam, costByFn.data, costByFn.loading]);

  const functionDetail = useFunctionDetail(functionNameParam, analyticsFilters);
  const modelCostFilters = useMemo(() => ({
    ...analyticsFilters,
    function_name: functionNameParam ?? undefined,
  }), [analyticsFilters, functionNameParam]);
  const costByModel = useCostByModel(functionNameParam ? modelCostFilters : analyticsFilters);

  const filters = useMemo(() => ({
    function_name: search || undefined,
    status: statusFilter,
    started_after: dateRange.started_after,
    started_before: dateRange.started_before,
  }), [search, statusFilter, dateRange.started_after, dateRange.started_before]);

  const { traces, loading, loadingMore, error, hasMore, loadMore, refetch } = useTraces(filters);

  const maxDuration = Math.max(...traces.map((t) => t.duration_ms ?? 0), 1);

  function updateFilter(key: string, value: string | undefined) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
  }

  const statusOptions: { label: string; value: string | undefined }[] = [
    { label: 'All', value: undefined },
    { label: 'Ok', value: 'ok' },
    { label: 'Error', value: 'error' },
  ];

  return (
    <div className="max-w-6xl">
      <h1 className="text-text-primary text-lg font-semibold mb-6">Traces</h1>

      {functionItem && (
        <FunctionSummaryCards
          item={functionItem}
          detail={functionDetail.data}
          modelCosts={functionNameParam ? costByModel.data : []}
        />
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-4">
        <input
          type="text"
          placeholder="Search by function name..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            updateFilter('function_name', e.target.value || undefined);
          }}
          className="bg-surface-secondary border border-border rounded-md px-3 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors w-full sm:w-64"
        />
        <div className="flex gap-1">
          {statusOptions.map((opt) => (
            <button
              key={opt.label}
              onClick={() => {
                setStatusFilter(opt.value);
                updateFilter('status', opt.value);
              }}
              className={clsx(
                'px-3 py-1 text-xs rounded-md transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-none',
                statusFilter === opt.value
                  ? 'bg-accent text-white'
                  : 'text-text-secondary hover:text-text-primary hover:bg-surface-tertiary',
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="sm:ml-auto">
          <DateRangeFilter value={dateRange} onChange={setDateRange} />
        </div>
      </div>

      {/* Table */}
      {error ? (
        <ErrorMessage error={error} onRetry={refetch} />
      ) : loading ? (
        <div className="py-8"><LoadingSpinner /></div>
      ) : traces.length === 0 ? (
        <EmptyState message="No traces match your filters." action="Try adjusting your search or status filter." />
      ) : (
        <>
          <div className="space-y-1">
            {traces.map((trace) => (
              <div
                key={trace.id}
                onClick={() => navigate(`/traces/${trace.id}`)}
                className="flex items-center gap-4 px-4 py-3 rounded-lg border border-transparent hover:border-border-focus hover:bg-surface-secondary hover:-translate-y-px transition-all cursor-pointer"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-text-primary font-medium truncate">
                      {trace.function_name}
                    </span>
                    <span className="text-text-muted text-xs">{trace.environment}</span>
                  </div>
                </div>

                <div className="w-32 flex items-center gap-2">
                  <div className="flex-1 h-1 bg-surface-tertiary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent/50 rounded-full"
                      style={{ width: `${((trace.duration_ms ?? 0) / maxDuration) * 100}%` }}
                    />
                  </div>
                  <span className="text-text-muted text-xs font-mono whitespace-nowrap">
                    {formatDuration(trace.duration_ms)}
                  </span>
                </div>

                <StatusBadge status={trace.status} />

                <span className="font-mono text-xs text-text-secondary w-16 text-right">
                  {formatCost(trace.total_cost_usd)}
                </span>

                <span className="text-text-muted text-xs w-14 text-right">
                  {formatTokens(trace.total_tokens)}
                </span>

                <span className="text-text-muted text-xs text-right whitespace-nowrap">
                  {formatDatePrecise(trace.started_at)}
                </span>
              </div>
            ))}
          </div>
          <Pagination hasMore={hasMore} loading={loadingMore} onLoadMore={loadMore} />
        </>
      )}
    </div>
  );
}

export default TracesPage;
