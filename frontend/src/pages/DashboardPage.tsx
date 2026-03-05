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
import { useCostByModel } from '../hooks/useCostByModel';
import { formatCost, formatDuration, formatPercent, formatTokens } from '../utils/formatters';
import type { FunctionCostItem, ModelCostItem } from '../types/analytics';

export function DashboardPage() {
  const [dateRange, setDateRange] = useState<DateRange>({});
  const filters = useMemo(() => ({
    started_after: dateRange.started_after,
    started_before: dateRange.started_before,
  }), [dateRange.started_after, dateRange.started_before]);

  const stats = useOverviewStats(filters);
  const timeseries = useTimeseries(filters);
  const costByFn = useCostByFunction(filters);
  const costByModel = useCostByModel(filters);

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

      {/* Cost by model */}
      <div className="bg-surface-secondary border border-border rounded-lg p-5 mt-8">
        <h2 className="text-text-primary text-sm font-medium mb-4">Cost by Model</h2>
        {costByModel.error ? (
          <ErrorMessage error={costByModel.error} onRetry={costByModel.refetch} />
        ) : costByModel.loading ? (
          <LoadingSpinner />
        ) : costByModel.data.length === 0 ? (
          <EmptyState message="No model data yet." action="Send your first trace using the SDK." />
        ) : (
          <ModelCostTable data={costByModel.data} />
        )}
      </div>
    </div>
  );
}

type SortDir = 'asc' | 'desc';

function SortHeader({
  label,
  active,
  dir,
  align,
  onToggle,
}: {
  label: string;
  active: boolean;
  dir: SortDir;
  align?: 'left' | 'right';
  onToggle: () => void;
}) {
  const arrow = active ? (dir === 'asc' ? ' \u2191' : ' \u2193') : '';
  return (
    <button
      onClick={onToggle}
      className={`cursor-pointer select-none transition-colors ${
        align === 'right' ? 'text-right ml-auto' : ''
      } ${active ? 'text-text-primary' : 'text-text-muted hover:text-text-secondary'}`}
    >
      {label}{arrow}
    </button>
  );
}

function useSort<K extends string>(defaultKey: K, defaultDir: SortDir = 'desc') {
  const [sortKey, setSortKey] = useState<K>(defaultKey);
  const [sortDir, setSortDir] = useState<SortDir>(defaultDir);

  const toggle = (key: K) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  return { sortKey, sortDir, toggle };
}

function sorted<T>(data: T[], key: keyof T, dir: SortDir): T[] {
  return [...data].sort((a, b) => {
    const av = a[key] ?? -Infinity;
    const bv = b[key] ?? -Infinity;
    if (av < bv) return dir === 'asc' ? -1 : 1;
    if (av > bv) return dir === 'asc' ? 1 : -1;
    return 0;
  });
}

type FnSortKey = 'function_name' | 'call_count' | 'total_cost_usd' | 'avg_cost_usd' | 'avg_duration_ms' | 'error_count' | 'avg_quality_score';

function CostTable({ data }: { data: FunctionCostItem[] }) {
  const { sortKey, sortDir, toggle } = useSort<FnSortKey>('total_cost_usd');
  const rows = useMemo(() => sorted(data, sortKey, sortDir), [data, sortKey, sortDir]);
  const maxCost = Math.max(...data.map((d) => d.total_cost_usd ?? 0), 0.001);

  return (
    <div className="space-y-1">
      <div className="grid grid-cols-[1fr_80px_80px_80px_80px_80px_60px] gap-4 text-xs pb-2 border-b border-border">
        <SortHeader label="Function" active={sortKey === 'function_name'} dir={sortDir} onToggle={() => toggle('function_name')} />
        <SortHeader label="Calls" align="right" active={sortKey === 'call_count'} dir={sortDir} onToggle={() => toggle('call_count')} />
        <SortHeader label="Total Cost" align="right" active={sortKey === 'total_cost_usd'} dir={sortDir} onToggle={() => toggle('total_cost_usd')} />
        <SortHeader label="Avg Cost" align="right" active={sortKey === 'avg_cost_usd'} dir={sortDir} onToggle={() => toggle('avg_cost_usd')} />
        <SortHeader label="Avg Latency" align="right" active={sortKey === 'avg_duration_ms'} dir={sortDir} onToggle={() => toggle('avg_duration_ms')} />
        <SortHeader label="Avg Quality" align="right" active={sortKey === 'avg_quality_score'} dir={sortDir} onToggle={() => toggle('avg_quality_score')} />
        <SortHeader label="Errors" align="right" active={sortKey === 'error_count'} dir={sortDir} onToggle={() => toggle('error_count')} />
      </div>
      {rows.map((item) => {
        const costRatio = (item.total_cost_usd ?? 0) / maxCost;
        const errorRatio = item.call_count > 0 ? item.error_count / item.call_count : 0;
        return (
          <div
            key={item.function_name}
            className="grid grid-cols-[1fr_80px_80px_80px_80px_80px_60px] gap-4 items-center py-2 text-sm"
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
              {formatCost(item.total_cost_usd)}
            </span>
            <span className="text-right font-mono text-text-secondary text-xs">
              {formatCost(item.avg_cost_usd)}
            </span>
            <span className="text-right font-mono text-text-secondary text-xs">
              {formatDuration(item.avg_duration_ms)}
            </span>
            <span className="text-right font-mono text-text-secondary text-xs">
              {item.avg_quality_score != null ? `${(item.avg_quality_score * 100).toFixed(0)}%` : '—'}
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

type ModelSortKey = 'model' | 'call_count' | 'total_tokens' | 'total_cost_usd' | 'avg_cost_usd' | 'avg_quality_score';

function ModelCostTable({ data }: { data: ModelCostItem[] }) {
  const { sortKey, sortDir, toggle } = useSort<ModelSortKey>('total_cost_usd');
  const rows = useMemo(() => sorted(data, sortKey, sortDir), [data, sortKey, sortDir]);
  const maxCost = Math.max(...data.map((d) => d.total_cost_usd ?? 0), 0.001);

  return (
    <div className="space-y-1">
      <div className="grid grid-cols-[1fr_80px_100px_80px_80px_80px] gap-4 text-xs pb-2 border-b border-border">
        <SortHeader label="Model" active={sortKey === 'model'} dir={sortDir} onToggle={() => toggle('model')} />
        <SortHeader label="Calls" align="right" active={sortKey === 'call_count'} dir={sortDir} onToggle={() => toggle('call_count')} />
        <SortHeader label="Total Tokens" align="right" active={sortKey === 'total_tokens'} dir={sortDir} onToggle={() => toggle('total_tokens')} />
        <SortHeader label="Total Cost" align="right" active={sortKey === 'total_cost_usd'} dir={sortDir} onToggle={() => toggle('total_cost_usd')} />
        <SortHeader label="Avg Cost" align="right" active={sortKey === 'avg_cost_usd'} dir={sortDir} onToggle={() => toggle('avg_cost_usd')} />
        <SortHeader label="Avg Quality" align="right" active={sortKey === 'avg_quality_score'} dir={sortDir} onToggle={() => toggle('avg_quality_score')} />
      </div>
      {rows.map((item) => {
        const costRatio = (item.total_cost_usd ?? 0) / maxCost;
        return (
          <div
            key={item.model}
            className="grid grid-cols-[1fr_80px_100px_80px_80px_80px] gap-4 items-center py-2 text-sm"
          >
            <div className="flex items-center gap-3">
              <span className="font-mono text-text-primary text-xs truncate">
                {item.model}
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
              {formatTokens(item.total_tokens)}
            </span>
            <span className="text-right font-mono text-text-secondary text-xs">
              {formatCost(item.total_cost_usd)}
            </span>
            <span className="text-right font-mono text-text-secondary text-xs">
              {formatCost(item.avg_cost_usd)}
            </span>
            <span className="text-right font-mono text-text-secondary text-xs">
              {item.avg_quality_score != null ? `${(item.avg_quality_score * 100).toFixed(0)}%` : '—'}
            </span>
          </div>
        );
      })}
    </div>
  );
}
