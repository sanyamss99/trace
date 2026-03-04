import clsx from 'clsx';
import { SpanTimeline } from './SpanTimeline';
import { formatDuration, formatCost } from '../utils/formatters';
import { cssVar } from '../utils/colors';
import type { Span } from '../types/traces';

function spanTypeColors(): Record<string, string> {
  return {
    llm: cssVar('--raw-accent') || '#6366f1',
    retrieval: '#0ea5e9',
    generic: cssVar('--raw-influence-low') || '#505468',
  };
}

interface SpanRowProps {
  span: Span;
  depth: number;
  traceStartMs: number;
  traceDurationMs: number;
  isSelected: boolean;
  onClick: () => void;
}

export function SpanRow({
  span,
  depth,
  traceStartMs,
  traceDurationMs,
  isSelected,
  onClick,
}: SpanRowProps) {
  const colors = spanTypeColors();
  const borderColor = colors[span.span_type] ?? colors.generic;
  const spanStartMs = new Date(span.started_at).getTime();

  return (
    <div
      onClick={onClick}
      className={clsx(
        'flex items-center gap-3 px-3 py-2 rounded-md cursor-pointer transition-colors border-l-2',
        isSelected
          ? 'bg-accent-subtle border-l-accent'
          : 'hover:bg-surface-tertiary border-l-transparent',
      )}
      style={{ paddingLeft: `${12 + depth * 20}px`, borderLeftColor: isSelected ? undefined : borderColor }}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-text-primary truncate">
            {span.function_name}
          </span>
          {span.span_type === 'llm' && (
            <span className="text-accent text-xs" title="Attribution available">&#9671;</span>
          )}
          {span.model && (
            <span className="text-text-muted text-xs truncate">{span.model}</span>
          )}
        </div>
      </div>

      <div className="w-40 shrink-0">
        <SpanTimeline
          startMs={spanStartMs}
          durationMs={span.duration_ms ?? 0}
          traceStartMs={traceStartMs}
          traceDurationMs={traceDurationMs}
          color={borderColor}
        />
      </div>

      <span className="text-text-secondary font-mono text-xs w-14 text-right shrink-0">
        {formatDuration(span.duration_ms)}
      </span>

      {span.cost_usd != null && (
        <span className="text-text-muted font-mono text-xs w-16 text-right shrink-0">
          {formatCost(span.cost_usd)}
        </span>
      )}
    </div>
  );
}
