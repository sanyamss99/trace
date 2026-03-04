import { useMemo } from 'react';
import clsx from 'clsx';
import { scoreBarColor, SEGMENT_DOT_COLORS } from '../utils/colors';
import type { SpanSegment } from '../types/traces';

interface SegmentScoreBarProps {
  segments: SpanSegment[];
}

export function SegmentScoreBar({ segments }: SegmentScoreBarProps) {
  // Sort by influence descending — most impactful chunk at top
  const ranked = useMemo(
    () =>
      segments
        .map((seg, originalIndex) => ({ seg, originalIndex }))
        .sort((a, b) => (b.seg.influence_score ?? 0) - (a.seg.influence_score ?? 0)),
    [segments],
  );

  return (
    <div className="space-y-1">
      {/* Header */}
      <div className="grid grid-cols-[24px_1fr_100px_100px] gap-2 items-center pb-2 border-b border-border">
        <span className="text-text-muted text-xs text-center">#</span>
        <span className="text-text-muted text-xs">Segment</span>
        <span className="text-text-muted text-xs text-right">Influence</span>
        <span className="text-text-muted text-xs text-right">Utilization</span>
      </div>

      {ranked.map(({ seg, originalIndex }, rank) => {
        const influence = seg.influence_score ?? 0;
        const utilization = seg.utilization_score ?? 0;
        const dotColor = SEGMENT_DOT_COLORS[originalIndex % SEGMENT_DOT_COLORS.length];
        const isRetrievalUnused =
          seg.segment_type === 'retrieval' &&
          seg.retrieval_rank != null &&
          seg.retrieval_rank <= 1 &&
          utilization < 0.1;

        return (
          <div
            key={seg.id}
            className={clsx(
              'grid grid-cols-[24px_1fr_100px_100px] gap-2 items-center py-2 rounded',
              rank === 0 && influence > 0.3 && 'bg-accent-subtle',
            )}
          >
            {/* Rank */}
            <span className={clsx(
              'text-center font-mono text-xs',
              rank === 0 && influence > 0.3 ? 'text-accent font-semibold' : 'text-text-muted',
            )}>
              {rank + 1}
            </span>

            {/* Name + type + warnings */}
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: dotColor }}
              />
              <span className="font-mono text-xs text-text-primary truncate">
                {seg.segment_name}
              </span>
              <span className={clsx(
                'text-xs px-1.5 py-0.5 rounded shrink-0',
                seg.segment_type === 'retrieval'
                  ? 'text-sky-400 bg-sky-400/10'
                  : seg.segment_type === 'system'
                    ? 'text-text-muted bg-surface-tertiary'
                    : 'text-accent bg-accent-subtle',
              )}>
                {seg.segment_type}
              </span>
              {isRetrievalUnused && (
                <span
                  className="text-warning text-xs shrink-0"
                  title="Retrieved at rank #1 but barely used — possible RAG failure"
                >
                  &#9888; unused
                </span>
              )}
            </div>

            {/* Influence bar */}
            <div className="flex items-center gap-1.5">
              <div className="flex-1 h-2 bg-surface-tertiary rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${Math.min(influence * 100, 100)}%`,
                    backgroundColor: scoreBarColor(influence),
                  }}
                />
              </div>
              <span className={clsx(
                'font-mono text-xs w-8 text-right',
                influence > 0.5 ? 'text-accent' : 'text-text-secondary',
              )}>
                {(influence * 100).toFixed(0)}%
              </span>
            </div>

            {/* Utilization bar */}
            <div className="flex items-center gap-1.5">
              <div className="flex-1 h-2 bg-surface-tertiary rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${Math.min(utilization * 100, 100)}%`,
                    backgroundColor: scoreBarColor(utilization),
                  }}
                />
              </div>
              <span className="font-mono text-xs text-text-secondary w-8 text-right">
                {(utilization * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        );
      })}

      {/* Explanation footer */}
      <div className="pt-3 mt-2 border-t border-border space-y-1">
        <p className="text-text-muted text-xs">
          <span className="text-text-secondary font-medium">Influence</span> — how much this chunk affected uncertain tokens in the output
        </p>
        <p className="text-text-muted text-xs">
          <span className="text-text-secondary font-medium">Utilization</span> — how much of this chunk&apos;s content appeared in the output
        </p>
      </div>
    </div>
  );
}
