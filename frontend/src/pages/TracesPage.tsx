import { useState, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import clsx from 'clsx';
import { useTraces } from '../hooks/useTraces';
import { StatusBadge } from '../components/StatusBadge';
import { Pagination } from '../components/Pagination';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { EmptyState } from '../components/EmptyState';
import { formatCost, formatDuration, formatTokens, formatRelativeDate } from '../utils/formatters';

export function TracesPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get('function_name') ?? '');
  const [statusFilter, setStatusFilter] = useState<string | undefined>(
    searchParams.get('status') ?? undefined,
  );

  const filters = useMemo(() => ({
    function_name: search || undefined,
    status: statusFilter,
  }), [search, statusFilter]);

  const { traces, loading, error, hasMore, loadMore, refetch } = useTraces(filters);

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

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <input
          type="text"
          placeholder="Search by function name..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            updateFilter('function_name', e.target.value || undefined);
          }}
          className="bg-surface-secondary border border-border rounded-md px-3 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors w-64"
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
                'px-3 py-1 text-xs rounded-md transition-colors',
                statusFilter === opt.value
                  ? 'bg-accent text-white'
                  : 'text-text-secondary hover:text-text-primary hover:bg-surface-tertiary',
              )}
            >
              {opt.label}
            </button>
          ))}
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

                <span className="text-text-muted text-xs w-20 text-right">
                  {formatRelativeDate(trace.started_at)}
                </span>
              </div>
            ))}
          </div>
          <Pagination hasMore={hasMore} onLoadMore={loadMore} />
        </>
      )}
    </div>
  );
}
