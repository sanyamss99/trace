interface SpanTimelineProps {
  startMs: number;
  durationMs: number;
  traceStartMs: number;
  traceDurationMs: number;
  color?: string;
}

export function SpanTimeline({
  startMs,
  durationMs,
  traceStartMs,
  traceDurationMs,
  color = '#6366f1',
}: SpanTimelineProps) {
  const totalMs = traceDurationMs || 1;
  const left = ((startMs - traceStartMs) / totalMs) * 100;
  const width = Math.max((durationMs / totalMs) * 100, 0.5);

  return (
    <div className="relative h-3 bg-surface-tertiary rounded-full overflow-hidden">
      <div
        className="absolute top-0 h-full rounded-full"
        style={{
          left: `${left}%`,
          width: `${width}%`,
          backgroundColor: color,
          opacity: 0.7,
        }}
      />
    </div>
  );
}
