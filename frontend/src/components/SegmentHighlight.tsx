import { useMemo, useState, useRef, useCallback, useEffect } from 'react';
import { segmentBgColor, segmentBorderColor, SEGMENT_DOT_COLORS, cssVar } from '../utils/colors';
import type { SpanSegment } from '../types/traces';

interface SegmentHighlightProps {
  promptText: string;
  segments: SpanSegment[];
}

interface TextRun {
  text: string;
  segmentIndex: number | null;
}

function buildRuns(text: string, segments: SpanSegment[]): TextRun[] {
  const sorted = segments
    .map((s, i) => ({ ...s, originalIndex: i }))
    .filter((s) => s.position_start != null && s.position_end != null)
    .sort((a, b) => a.position_start! - b.position_start!);

  if (sorted.length === 0) {
    return [{ text, segmentIndex: null }];
  }

  const runs: TextRun[] = [];
  let cursor = 0;

  for (const seg of sorted) {
    const start = seg.position_start!;
    const end = seg.position_end!;

    if (cursor < start) {
      runs.push({ text: text.slice(cursor, start), segmentIndex: null });
    }
    runs.push({
      text: text.slice(start, end),
      segmentIndex: seg.originalIndex,
    });
    cursor = end;
  }

  if (cursor < text.length) {
    runs.push({ text: text.slice(cursor), segmentIndex: null });
  }

  return runs;
}

export function SegmentHighlight({ promptText, segments }: SegmentHighlightProps) {
  const runs = useMemo(() => buildRuns(promptText, segments), [promptText, segments]);
  const [hoveredSegment, setHoveredSegment] = useState<number | null>(null);
  const [activeSegment, setActiveSegment] = useState<number | null>(null);
  const segmentRefs = useRef<Record<number, HTMLSpanElement | null>>({});
  const activeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sort legend by influence descending so most important is first
  const sortedLegend = useMemo(
    () =>
      segments
        .map((seg, i) => ({ seg, i }))
        .sort((a, b) => (b.seg.influence_score ?? 0) - (a.seg.influence_score ?? 0)),
    [segments],
  );

  const scrollToSegment = useCallback((segIdx: number) => {
    if (activeTimerRef.current) clearTimeout(activeTimerRef.current);
    setActiveSegment(segIdx);
    const el = segmentRefs.current[segIdx];
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    activeTimerRef.current = setTimeout(() => setActiveSegment(null), 1500);
  }, []);

  useEffect(() => {
    return () => {
      if (activeTimerRef.current) clearTimeout(activeTimerRef.current);
    };
  }, []);

  return (
    <div>
      {/* Legend — sorted by influence, shows score */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 mb-3 pb-3 border-b border-border">
        {sortedLegend.map(({ seg, i }) => {
          const influence = seg.influence_score ?? 0;
          const dotColor = SEGMENT_DOT_COLORS[i % SEGMENT_DOT_COLORS.length];
          return (
            <button
              key={seg.id}
              className="flex items-center gap-1.5 group cursor-pointer"
              onMouseEnter={() => setHoveredSegment(i)}
              onMouseLeave={() => setHoveredSegment(null)}
              onClick={() => scrollToSegment(i)}
            >
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: dotColor }}
              />
              <span className="text-text-secondary text-xs group-hover:text-text-primary transition-colors">
                {seg.segment_name}
              </span>
              <span
                className="font-mono text-xs px-1 py-px rounded"
                style={{
                  backgroundColor: segmentBgColor(influence),
                  color: influence > 0.3
                    ? (cssVar('--raw-influence-high-label') || '#a5b4fc')
                    : (cssVar('--raw-influence-mid') || '#8b90a0'),
                }}
              >
                {(influence * 100).toFixed(0)}%
              </span>
            </button>
          );
        })}
      </div>

      {/* Influence scale hint */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-text-muted text-xs">Highlight color = output influence</span>
        <div className="flex items-center gap-0.5">
          <div className="w-4 h-2 rounded-sm" style={{ backgroundColor: cssVar('--raw-segment-bg-cool') || '#172554' }} />
          <div className="w-4 h-2 rounded-sm" style={{ backgroundColor: cssVar('--raw-segment-bg-mid') || '#14532d' }} />
          <div className="w-4 h-2 rounded-sm" style={{ backgroundColor: cssVar('--raw-segment-bg-warm') || '#541414' }} />
        </div>
        <span className="text-text-muted text-xs">low → high</span>
      </div>

      {/* Text with influence-based highlights */}
      <div className="font-mono text-sm leading-relaxed whitespace-pre-wrap">
        {runs.map((run, i) => {
          if (run.segmentIndex == null) {
            return (
              <span key={i} className="text-text-secondary">
                {run.text}
              </span>
            );
          }

          const segIdx = run.segmentIndex;
          const seg = segments[segIdx];
          const influence = seg.influence_score;
          const isHovered = hoveredSegment === segIdx;
          const isActive = activeSegment === segIdx;
          const isDimmed = hoveredSegment !== null && !isHovered;

          return (
            <span
              key={i}
              ref={(el) => {
                if (el && !segmentRefs.current[segIdx]) {
                  segmentRefs.current[segIdx] = el;
                }
              }}
              onMouseEnter={() => setHoveredSegment(segIdx)}
              onMouseLeave={() => setHoveredSegment(null)}
              onClick={() => scrollToSegment(segIdx)}
              className="transition-all duration-150 cursor-pointer"
              style={{
                backgroundColor: segmentBgColor(influence, isHovered || isActive),
                borderBottom: `2px solid ${segmentBorderColor(influence)}`,
                opacity: isDimmed ? 0.35 : 1,
                outline: isActive ? `2px solid ${cssVar('--raw-accent') || '#4f46e5'}` : 'none',
                outlineOffset: '1px',
                borderRadius: isActive ? '2px' : undefined,
              }}
            >
              {run.text}
            </span>
          );
        })}
      </div>
    </div>
  );
}
