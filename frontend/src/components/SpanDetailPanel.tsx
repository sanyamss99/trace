import { useState, useEffect } from 'react';
import clsx from 'clsx';
import { useAttribution } from '../hooks/useAttribution';
import { SegmentHighlight } from './SegmentHighlight';
import { AttributionHeatmap } from './AttributionHeatmap';
import { SegmentScoreBar } from './SegmentScoreBar';
import { LoadingSpinner } from './LoadingSpinner';
import { ErrorMessage } from './ErrorMessage';
import type { Span } from '../types/traces';

type Tab = 'prompt' | 'completion' | 'attribution' | 'io';

interface SpanDetailPanelProps {
  span: Span;
  onClose: () => void;
}

export function SpanDetailPanel({ span, onClose }: SpanDetailPanelProps) {
  const isLlm = span.span_type === 'llm';
  const [tab, setTab] = useState<Tab>(isLlm ? 'prompt' : 'io');
  const attribution = useAttribution();

  useEffect(() => {
    if (isLlm) {
      attribution.load(span.id);
    } else {
      attribution.clear();
    }
  }, [span.id, isLlm]);

  const tabs: { key: Tab; label: string; show: boolean }[] = [
    { key: 'prompt', label: 'Prompt', show: isLlm },
    { key: 'completion', label: 'Completion', show: isLlm },
    { key: 'attribution', label: 'Attribution', show: isLlm },
    { key: 'io', label: 'Raw I/O', show: true },
  ];

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Escape') onClose();
  }

  return (
    <div
      className="border-l border-border bg-surface-secondary h-full overflow-y-auto"
      onKeyDown={handleKeyDown}
      tabIndex={-1}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border sticky top-0 bg-surface-secondary z-10">
        <span className="font-mono text-sm text-text-primary truncate">
          {span.function_name}
        </span>
        <button
          onClick={onClose}
          className="text-text-muted hover:text-text-primary text-sm transition-colors ml-2 shrink-0"
        >
          &#10005;
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 px-4 py-2 border-b border-border">
        {tabs
          .filter((t) => t.show)
          .map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={clsx(
                'px-2.5 py-1 text-xs rounded transition-colors',
                tab === t.key
                  ? 'text-accent bg-accent-subtle'
                  : 'text-text-muted hover:text-text-secondary',
              )}
            >
              {t.label}
            </button>
          ))}
      </div>

      {/* Content */}
      <div className="p-4">
        {tab === 'prompt' && (
          <div>
            {attribution.loading ? (
              <LoadingSpinner />
            ) : (() => {
              const segments = attribution.data?.segments?.length
                ? attribution.data.segments
                : span.segments;
              return segments.length > 0 && span.prompt_text ? (
                <SegmentHighlight
                  promptText={span.prompt_text}
                  segments={segments}
                />
              ) : span.prompt_text ? (
                <pre className="font-mono text-xs text-text-secondary whitespace-pre-wrap leading-relaxed">
                  {span.prompt_text}
                </pre>
              ) : (
                <p className="text-text-muted text-sm">No prompt text captured.</p>
              );
            })()}
          </div>
        )}

        {tab === 'completion' && (
          <div>
            {span.completion_logprobs && span.completion_logprobs.length > 0 ? (
              <AttributionHeatmap logprobs={span.completion_logprobs} />
            ) : span.completion_text ? (
              <pre className="font-mono text-xs text-text-secondary whitespace-pre-wrap leading-relaxed">
                {span.completion_text}
              </pre>
            ) : (
              <p className="text-text-muted text-sm">No completion text captured.</p>
            )}
          </div>
        )}

        {tab === 'attribution' && (
          <div>
            {attribution.loading ? (
              <LoadingSpinner />
            ) : attribution.error ? (
              <ErrorMessage error={attribution.error} onRetry={() => attribution.load(span.id)} />
            ) : attribution.data && attribution.data.segments.length > 0 ? (
              <SegmentScoreBar segments={attribution.data.segments} />
            ) : (
              <p className="text-text-muted text-sm">No attribution data available.</p>
            )}
          </div>
        )}

        {tab === 'io' && (
          <div className="space-y-4">
            <div>
              <h3 className="text-text-secondary text-xs font-medium mb-2">Input</h3>
              <pre className="font-mono text-xs text-text-secondary bg-surface-tertiary rounded-md p-3 overflow-x-auto whitespace-pre-wrap">
                {span.input_locals
                  ? JSON.stringify(span.input_locals, null, 2)
                  : '—'}
              </pre>
            </div>
            <div>
              <h3 className="text-text-secondary text-xs font-medium mb-2">Output</h3>
              <pre className="font-mono text-xs text-text-secondary bg-surface-tertiary rounded-md p-3 overflow-x-auto whitespace-pre-wrap">
                {span.output != null
                  ? JSON.stringify(span.output, null, 2)
                  : '—'}
              </pre>
            </div>
            {span.error && (
              <div>
                <h3 className="text-error text-xs font-medium mb-2">Error</h3>
                <pre className="font-mono text-xs text-error bg-error-subtle rounded-md p-3 whitespace-pre-wrap">
                  {span.error}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
