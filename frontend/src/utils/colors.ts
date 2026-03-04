import { scaleSequential } from 'd3-scale';
import { interpolateRgb } from 'd3-interpolate';

/**
 * Read a CSS custom property from :root / [data-theme].
 * Falls back to empty string if the property is not defined.
 */
export function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function accentRgb(): string {
  return cssVar('--raw-accent-rgb') || '99, 102, 241';
}

function warningRgb(): string {
  return cssVar('--raw-warning-rgb') || '245, 158, 11';
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

function lerpColor(a: string, b: string, t: number): string {
  const [r1, g1, b1] = hexToRgb(a);
  const [r2, g2, b2] = hexToRgb(b);
  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const bl = Math.round(b1 + (b2 - b1) * t);
  return `rgb(${r}, ${g}, ${bl})`;
}

// Logprob color scale: confident (transparent) -> uncertain (amber) -> very uncertain (red)
// Logprobs are negative: 0 = most confident, -inf = least confident
// We map [-4, 0] range — anything below -4 is clamped to max uncertainty
function makeUncertaintyScale() {
  return scaleSequential<string>()
    .domain([0, -4])
    .interpolator(
      interpolateRgb(
        `rgba(${accentRgb()}, 0)`,
        cssVar('--raw-error') || '#ef4444',
      ),
    );
}

export function logprobToColor(logprob: number): string {
  if (logprob > -0.1) {
    // Confident — visible green tint instead of invisible transparent
    return cssVar('--raw-heatmap-confident-bg') || 'rgba(5, 150, 105, 0.12)';
  }
  if (logprob > -2.0) {
    // Medium uncertainty — amber range, boosted alpha for visibility
    const t = (logprob + 0.1) / (-2.0 + 0.1);
    const alpha = 0.30 + t * 0.40;
    return `rgba(${warningRgb()}, ${alpha})`;
  }
  // High uncertainty — red range
  return makeUncertaintyScale()(Math.max(logprob, -4));
}

export function logprobToTextColor(logprob: number): string {
  if (logprob > -0.1) return cssVar('--raw-logprob-text-confident') || '#e8eaf0';
  if (logprob > -2.0) return cssVar('--raw-logprob-text-medium') || '#fbbf24';
  return cssVar('--raw-logprob-text-uncertain') || '#fca5a5';
}

// 3-stop interpolation: a → b → c over t ∈ [0, 1]
function lerpColor3(a: string, b: string, c: string, t: number): string {
  if (t <= 0.5) return lerpColor(a, b, t * 2);
  return lerpColor(b, c, (t - 0.5) * 2);
}

// Influence-based segment coloring — cool→warm spectrum for clear differentiation
export function segmentBgColor(influence: number | null, hovered = false): string {
  const score = influence ?? 0;
  if (score < 0.05) {
    return hovered
      ? (cssVar('--raw-segment-bg-hover-none') || '#1e2038')
      : (cssVar('--raw-segment-bg-none') || '#181a28');
  }
  const cool = cssVar('--raw-segment-bg-cool') || '#172554';
  const mid = cssVar('--raw-segment-bg-mid') || '#14532d';
  const warm = cssVar('--raw-segment-bg-warm') || '#541414';
  const t = Math.sqrt(Math.min(score, 1));
  const base = lerpColor3(cool, mid, warm, t);
  if (!hovered) return base;
  return lerpColor3(cool, mid, warm, Math.min(t + 0.15, 1));
}

export function segmentBorderColor(influence: number | null): string {
  const score = influence ?? 0;
  if (score < 0.05) return cssVar('--raw-influence-low') || '#505468';
  const cool = cssVar('--raw-segment-border-cool') || '#60a5fa';
  const warm = cssVar('--raw-segment-border-warm') || '#f87171';
  const t = Math.sqrt(Math.min(score, 1));
  return lerpColor(cool, warm, t);
}

// Score bar color — semantic: low=muted, medium=accent-muted, high=bright accent
export function scoreBarColor(score: number): string {
  const low = cssVar('--raw-influence-low') || '#505468';
  const accent = cssVar('--raw-accent') || '#6366f1';
  if (score < 0.1) return low;
  if (score < 0.3) return `${accent}80`;
  if (score < 0.6) return `${accent}b3`;
  return accent;
}

// Categorical colors — only for legend dots to distinguish segments by name
export const SEGMENT_DOT_COLORS = [
  '#6366f1', '#10b981', '#f59e0b', '#ec4899', '#0ea5e9', '#a855f7',
] as const;

// Kept for backward compat — components should prefer influence-based colors
export const SEGMENT_COLORS = [
  { bg: 'rgba(99, 102, 241, 0.12)', border: '#6366f1', label: 'indigo' },
  { bg: 'rgba(16, 185, 129, 0.12)', border: '#10b981', label: 'emerald' },
  { bg: 'rgba(245, 158, 11, 0.12)', border: '#f59e0b', label: 'amber' },
  { bg: 'rgba(236, 72, 153, 0.12)', border: '#ec4899', label: 'pink' },
  { bg: 'rgba(14, 165, 233, 0.12)', border: '#0ea5e9', label: 'sky' },
  { bg: 'rgba(168, 85, 247, 0.12)', border: '#a855f7', label: 'purple' },
] as const;

export function influenceToColor(score: number | null): string {
  const low = cssVar('--raw-influence-low') || '#505468';
  const mid = cssVar('--raw-influence-mid') || '#8b90a0';
  const accent = cssVar('--raw-accent') || '#6366f1';
  if (score == null || score < 0.2) return low;
  if (score < 0.5) return mid;
  return accent;
}
