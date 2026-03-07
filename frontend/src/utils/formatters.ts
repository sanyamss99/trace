import { formatDistanceToNow, format } from 'date-fns';

export function formatCost(usd: number | null | undefined): string {
  if (usd == null) return '$0.00';
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return '—';
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function formatTokens(count: number | null | undefined): string {
  if (count == null) return '—';
  if (count < 1000) return String(count);
  if (count < 1_000_000) return `${(count / 1000).toFixed(1)}k`;
  return `${(count / 1_000_000).toFixed(1)}M`;
}

export function formatDate(iso: string): string {
  return format(new Date(iso), 'MMM d, yyyy HH:mm');
}

export function formatDatePrecise(iso: string): string {
  const d = new Date(iso);
  const base = format(d, 'MMM d, yyyy HH:mm:ss');
  const ms = String(d.getMilliseconds()).padStart(3, '0');
  return `${base}.${ms}`;
}

export function formatRelativeDate(iso: string): string {
  return formatDistanceToNow(new Date(iso), { addSuffix: true });
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return '0%';
  return `${(value * 100).toFixed(1)}%`;
}
