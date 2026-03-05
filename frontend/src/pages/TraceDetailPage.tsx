import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTraceDetail } from '../hooks/useTraceDetail';
import { SpanTree } from '../components/SpanTree';
import { SpanDetailPanel } from '../components/SpanDetailPanel';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { formatDuration, formatCost, formatTokens } from '../utils/formatters';
import type { Span } from '../types/traces';

export function TraceDetailPage() {
  const { traceId } = useParams<{ traceId: string }>();
  const navigate = useNavigate();
  const { data: trace, loading, error, refetch } = useTraceDetail(traceId!);
  const [selectedSpan, setSelectedSpan] = useState<Span | null>(null);

  const traceStartMs = useMemo(() => {
    if (!trace) return 0;
    return new Date(trace.started_at).getTime();
  }, [trace]);

  const traceDurationMs = useMemo(() => {
    return trace?.duration_ms ?? 0;
  }, [trace]);

  if (loading) {
    return (
      <div className="py-12">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={refetch} />;
  }

  if (!trace) return null;

  return (
    <div className="max-w-full">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => navigate('/traces')}
          className="text-text-muted hover:text-text-primary transition-colors"
        >
          &larr;
        </button>
        <span className="font-mono text-lg text-text-primary font-medium">
          {trace.function_name}
        </span>
        <StatusBadge status={trace.status} />
        <span className="text-text-muted text-sm font-mono">
          {formatDuration(trace.duration_ms)}
          {' \u00B7 '}
          {formatTokens(trace.total_tokens)} tokens
          {' \u00B7 '}
          {formatCost(trace.total_cost_usd)}
        </span>
      </div>

      {/* Main area */}
      <div className="flex gap-0">
        {/* Span tree */}
        <div className={selectedSpan ? 'flex-1 min-w-0' : 'w-full'}>
          <div className="bg-surface-secondary border border-border rounded-lg p-3">
            <SpanTree
              spans={trace.spans}
              selectedSpanId={selectedSpan?.id ?? null}
              onSelectSpan={setSelectedSpan}
              traceStartMs={traceStartMs}
              traceDurationMs={traceDurationMs}
            />
          </div>
        </div>

        {/* Detail panel */}
        {selectedSpan && (
          <div className="fixed inset-0 z-30 bg-surface-primary md:relative md:inset-auto md:z-auto md:bg-transparent md:w-[45%] md:shrink-0">
            <SpanDetailPanel
              span={selectedSpan}
              onClose={() => setSelectedSpan(null)}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default TraceDetailPage;
