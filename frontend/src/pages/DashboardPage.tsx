import { useState, useMemo } from 'react';
import { DateRangeFilter, type DateRange } from '../components/DateRangeFilter';
import { StatCard } from '../components/StatCard';
import { TimeseriesChart } from '../components/TimeseriesChart';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { EmptyState } from '../components/EmptyState';
import { useOverviewStats } from '../hooks/useOverviewStats';
import { useTimeseries } from '../hooks/useTimeseries';
import { useCostByFunction } from '../hooks/useCostByFunction';
import { formatCost, formatDuration, formatPercent } from '../utils/formatters';
import type { FunctionCostItem } from '../types/analytics';

export function DashboardPage() {
  const [dateRange, setDateRange] = useState<DateRange>({});
  const filters = useMemo(() => ({
    started_after: dateRange.started_after,
    started_before: dateRange.started_before,
  }), [dateRange.started_after, dateRange.started_before]);

  const stats = useOverviewStats(filters);
  const timeseries = useTimeseries(filters);
  const costByFn = useCostByFunction(filters);

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-text-primary text-lg font-semibold">Dashboard</h1>
        <DateRangeFilter value={dateRange} onChange={setDateRange} />
      </div>

      {/* Stat cards */}
      {stats.error ? (
        <ErrorMessage error={stats.error} onRetry={stats.refetch} />
      ) : stats.loading ? (
        <div className="py-8"><LoadingSpinner /></div>
      ) : stats.data ? (
        <div className="grid grid-cols-4 gap-8 mb-8">
          <StatCard label="Traces" value={String(stats.data.trace_count)} />
          <StatCard label="Total Cost" value={formatCost(stats.data.total_cost_usd)} />
          <StatCard label="Avg Latency" value={formatDuration(stats.data.avg_duration_ms)} />
          <StatCard
            label="Error Rate"
            value={formatPercent(stats.data.error_rate)}
            variant={stats.data.error_rate > 0.05 ? 'error' : 'default'}
            pulse={stats.data.error_rate > 0.05}
          />
        </div>
      ) : null}

      {/* Timeseries */}
      <div className="bg-surface-secondary border border-border rounded-lg p-5 mb-8">
        {timeseries.error ? (
          <ErrorMessage error={timeseries.error} onRetry={timeseries.refetch} />
        ) : timeseries.loading ? (
          <div className="h-60 flex items-center"><LoadingSpinner /></div>
        ) : timeseries.data.length === 0 ? (
          <EmptyState message="No data for this time range." />
        ) : (
          <TimeseriesChart data={timeseries.data} />
        )}
      </div>

      {/* Cost by function */}
      <div className="bg-surface-secondary border border-border rounded-lg p-5">
        <h2 className="text-text-primary text-sm font-medium mb-4">Cost by Function</h2>
        {costByFn.error ? (
          <ErrorMessage error={costByFn.error} onRetry={costByFn.refetch} />
        ) : costByFn.loading ? (
          <LoadingSpinner />
        ) : costByFn.data.length === 0 ? (
          <EmptyState message="No function data yet." action="Send your first trace using the SDK." />
        ) : (
          <CostTable data={costByFn.data} />
        )}
      </div>
    </div>
  );
}

function CostTable({ data }: { data: FunctionCostItem[] }) {
  const maxCost = Math.max(...data.map((d) => d.total_cost_usd ?? 0), 0.001);

  return (
    <div className="space-y-1">
      <div className="grid grid-cols-[1fr_80px_80px_80px_60px] gap-4 text-xs text-text-muted pb-2 border-b border-border">
        <span>Function</span>
        <span className="text-right">Calls</span>
        <span className="text-right">Avg Cost</span>
        <span className="text-right">Avg Latency</span>
        <span className="text-right">Errors</span>
      </div>
      {data.map((item) => {
        const costRatio = (item.total_cost_usd ?? 0) / maxCost;
        const errorRatio = item.call_count > 0 ? item.error_count / item.call_count : 0;
        return (
          <div
            key={item.function_name}
            className="grid grid-cols-[1fr_80px_80px_80px_60px] gap-4 items-center py-2 text-sm"
          >
            <div className="flex items-center gap-3">
              <span className="font-mono text-text-primary text-xs truncate">
                {item.function_name}
              </span>
              <div className="h-1 flex-1 max-w-[40px] bg-surface-tertiary rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent/40 rounded-full"
                  style={{ width: `${costRatio * 100}%` }}
                />
              </div>
            </div>
            <span className="text-right font-mono text-text-secondary text-xs">
              {item.call_count}
            </span>
            <span className="text-right font-mono text-text-secondary text-xs">
              {formatCost(item.avg_cost_usd)}
            </span>
            <span className="text-right font-mono text-text-secondary text-xs">
              {formatDuration(item.avg_duration_ms)}
            </span>
            <div className="flex justify-end">
              <div className="w-10 h-1 bg-surface-tertiary rounded-full overflow-hidden">
                <div
                  className="h-full bg-error rounded-full"
                  style={{ width: `${errorRatio * 100}%` }}
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
