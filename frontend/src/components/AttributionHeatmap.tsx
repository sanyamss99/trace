import { useMemo, useState, useCallback, useRef } from 'react';
import { logprobToColor, logprobToTextColor, cssVar } from '../utils/colors';
import type { LogprobEntry } from '../types/traces';

interface AttributionHeatmapProps {
  logprobs: LogprobEntry[];
}

interface TokenStyle {
  token: string;
  bgColor: string;
  textColor: string;
  logprob: number;
  probability: number;
}

export function AttributionHeatmap({ logprobs }: AttributionHeatmapProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const tokens = useMemo<TokenStyle[]>(
    () =>
      logprobs.map((lp) => ({
        token: lp.token,
        bgColor: logprobToColor(lp.logprob),
        textColor: logprobToTextColor(lp.logprob),
        logprob: lp.logprob,
        probability: Math.exp(lp.logprob) * 100,
      })),
    [logprobs],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const target = e.target as HTMLElement;
      const index = target.dataset.tokenIndex;
      if (index != null) {
        setHoveredIndex(Number(index));
        const rect = containerRef.current?.getBoundingClientRect();
        if (rect) {
          setTooltipPos({
            x: e.clientX - rect.left,
            y: e.clientY - rect.top - 40,
          });
        }
      } else {
        setHoveredIndex(null);
      }
    },
    [],
  );

  const handleMouseLeave = useCallback(() => {
    setHoveredIndex(null);
    setTooltipPos(null);
  }, []);

  return (
    <div>
      {/* Legend */}
      <div className="flex items-center gap-4 mb-3">
        <span className="text-text-muted text-xs">Confidence:</span>
        <div className="flex items-center gap-1">
          <div className="w-16 h-2 rounded-full" style={{
            background: `linear-gradient(to right, transparent, rgba(${cssVar('--raw-warning-rgb') || '245, 158, 11'}, 0.5), ${cssVar('--raw-error') || '#ef4444'})`,
          }} />
          <span className="text-text-muted text-xs ml-1">confident</span>
          <span className="text-text-muted text-xs ml-auto">uncertain</span>
        </div>
      </div>

      {/* Tokens */}
      <div
        ref={containerRef}
        className="relative font-mono text-sm leading-relaxed"
        style={{ whiteSpace: 'pre-wrap' }}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        {tokens.map((t, i) => (
          <span
            key={i}
            data-token-index={i}
            style={{
              backgroundColor: t.bgColor,
              color: t.textColor,
              borderRadius: '2px',
            }}
          >
            {t.token}
          </span>
        ))}

        {/* Tooltip */}
        {hoveredIndex !== null && tooltipPos && (
          <div
            className="absolute z-20 bg-surface-secondary border border-border rounded-md px-3 py-2 pointer-events-none shadow-lg"
            style={{ left: tooltipPos.x, top: tooltipPos.y, transform: 'translateX(-50%)' }}
          >
            <div className="font-mono text-xs text-text-primary mb-1">
              &ldquo;{tokens[hoveredIndex].token}&rdquo;
            </div>
            <div className="text-xs text-text-secondary">
              logprob: {tokens[hoveredIndex].logprob.toFixed(4)}
            </div>
            <div className="text-xs text-text-secondary">
              probability: {tokens[hoveredIndex].probability.toFixed(1)}%
            </div>
            <div className="mt-1 h-1 bg-surface-tertiary rounded-full overflow-hidden">
              <div
                className="h-full bg-accent rounded-full"
                style={{ width: `${Math.min(tokens[hoveredIndex].probability, 100)}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
