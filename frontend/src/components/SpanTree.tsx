import { useMemo } from 'react';
import { SpanRow } from './SpanRow';
import type { Span } from '../types/traces';

interface SpanTreeProps {
  spans: Span[];
  selectedSpanId: string | null;
  onSelectSpan: (span: Span) => void;
  traceStartMs: number;
  traceDurationMs: number;
}

function buildChildrenMap(spans: Span[]): Map<string | null, Span[]> {
  const map = new Map<string | null, Span[]>();
  for (const span of spans) {
    const key = span.parent_span_id;
    const list = map.get(key) ?? [];
    list.push(span);
    map.set(key, list);
  }
  // Sort each group by started_at
  for (const [key, list] of map) {
    map.set(
      key,
      list.sort((a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime()),
    );
  }
  return map;
}

export function SpanTree({
  spans,
  selectedSpanId,
  onSelectSpan,
  traceStartMs,
  traceDurationMs,
}: SpanTreeProps) {
  const childrenMap = useMemo(() => buildChildrenMap(spans), [spans]);

  function renderSpans(parentId: string | null, depth: number): React.ReactNode[] {
    const children = childrenMap.get(parentId) ?? [];
    return children.flatMap((span) => [
      <SpanRow
        key={span.id}
        span={span}
        depth={depth}
        traceStartMs={traceStartMs}
        traceDurationMs={traceDurationMs}
        isSelected={span.id === selectedSpanId}
        onClick={() => onSelectSpan(span)}
      />,
      ...renderSpans(span.id, depth + 1),
    ]);
  }

  return <div className="space-y-0.5">{renderSpans(null, 0)}</div>;
}
