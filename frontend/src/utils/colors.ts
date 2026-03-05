import { scaleSequential } from 'd3-scale';
import { interpolateRgb } from 'd3-interpolate';

/**
 * Read a CSS custom property from :root / [data-theme].
 * Falls back to empty string if the property is not defined.
 */
export function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
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

// 3-stop interpolation: a → b → c over t ∈ [0, 1]
function lerpColor3(a: string, b: string, c: string, t: number): string {
  if (t <= 0.5) return lerpColor(a, b, t * 2);
  return lerpColor(b, c, (t - 0.5) * 2);
}

// ── Yellow → Orange → Red heatmap ──
const HEAT_YELLOW = '#fde725';
const HEAT_ORANGE = '#f59e0b';
const HEAT_RED    = '#ef4444';

function heatmapColor(t: number): string {
  return lerpColor3(HEAT_YELLOW, HEAT_ORANGE, HEAT_RED, Math.max(0, Math.min(1, t)));
}

function heatmapAlpha(t: number, alpha: number): string {
  const clamped = Math.max(0, Math.min(1, t));
  const color = lerpColor3(HEAT_YELLOW, HEAT_ORANGE, HEAT_RED, clamped);
  // Extract rgb values from "rgb(r, g, b)" string
  const match = color.match(/rgb\((\d+), (\d+), (\d+)\)/);
  if (!match) return color;
  return `rgba(${match[1]}, ${match[2]}, ${match[3]}, ${alpha})`;
}

// Logprob color scale: confident (faint yellow) → uncertain (orange) → very uncertain (red)
// Logprobs are negative: 0 = most confident, -inf = least confident
// We map [-4, 0] range — anything below -4 is clamped to max uncertainty
function makeUncertaintyScale() {
  return scaleSequential<string>()
    .domain([0, -4])
    .interpolator(interpolateRgb(HEAT_YELLOW, HEAT_RED));
}

export function logprobToColor(logprob: number): string {
  if (logprob > -0.1) {
    // Confident — faint yellow tint
    return cssVar('--raw-heatmap-confident-bg') || 'rgba(253, 231, 37, 0.12)';
  }
  if (logprob > -2.0) {
    // Medium uncertainty — yellow→orange range
    const t = (logprob + 0.1) / (-2.0 + 0.1);
    const alpha = 0.30 + t * 0.40;
    return heatmapAlpha(t * 0.5, alpha);
  }
  // High uncertainty — orange→red range
  return makeUncertaintyScale()(Math.max(logprob, -4));
}

export function logprobToTextColor(logprob: number): string {
  if (logprob > -0.1) return cssVar('--raw-logprob-text-confident') || '#fef9c3';
  if (logprob > -2.0) return cssVar('--raw-logprob-text-medium') || '#fbbf24';
  return cssVar('--raw-logprob-text-uncertain') || '#fca5a5';
}

// Influence-based segment coloring — yellow→orange→red spectrum
export function segmentBgColor(influence: number | null, hovered = false): string {
  const score = influence ?? 0;
  if (score < 0.05) {
    return hovered
      ? (cssVar('--raw-segment-bg-hover-none') || '#1e2038')
      : (cssVar('--raw-segment-bg-none') || '#181a28');
  }
  const cool = cssVar('--raw-segment-bg-cool') || '#352a04';
  const mid = cssVar('--raw-segment-bg-mid') || '#3b1f06';
  const warm = cssVar('--raw-segment-bg-warm') || '#450a0a';
  const t = Math.sqrt(Math.min(score, 1));
  const base = lerpColor3(cool, mid, warm, t);
  if (!hovered) return base;
  return lerpColor3(cool, mid, warm, Math.min(t + 0.15, 1));
}

export function segmentBorderColor(influence: number | null): string {
  const score = influence ?? 0;
  if (score < 0.05) return cssVar('--raw-influence-low') || '#505468';
  const t = Math.sqrt(Math.min(score, 1));
  const cool = cssVar('--raw-segment-border-cool') || HEAT_YELLOW;
  const warm = cssVar('--raw-segment-border-warm') || HEAT_RED;
  return lerpColor(cool, warm, t);
}

// Score bar color — yellow→orange→red for low/medium/high
export function scoreBarColor(score: number): string {
  if (score < 0.1) return cssVar('--raw-influence-low') || '#505468';
  return heatmapColor(Math.sqrt(score));
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
  if (score == null || score < 0.2) return low;
  return heatmapColor(Math.sqrt(score));
}
