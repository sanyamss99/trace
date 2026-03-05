import {
  formatCost,
  formatDuration,
  formatTokens,
  formatPercent,
  formatDate,
  formatRelativeDate,
} from '../formatters';

describe('formatCost', () => {
  it('returns $0.00 for null/undefined', () => {
    expect(formatCost(null)).toBe('$0.00');
    expect(formatCost(undefined)).toBe('$0.00');
  });

  it('formats small values with 4 decimal places', () => {
    expect(formatCost(0.005)).toBe('$0.0050');
  });

  it('formats normal values with 2 decimal places', () => {
    expect(formatCost(1.234)).toBe('$1.23');
  });
});

describe('formatDuration', () => {
  it('returns dash for null/undefined', () => {
    expect(formatDuration(null)).toBe('—');
    expect(formatDuration(undefined)).toBe('—');
  });

  it('returns <1ms for sub-millisecond values', () => {
    expect(formatDuration(0.5)).toBe('<1ms');
  });

  it('formats milliseconds', () => {
    expect(formatDuration(42)).toBe('42ms');
  });

  it('formats seconds', () => {
    expect(formatDuration(1500)).toBe('1.5s');
  });
});

describe('formatTokens', () => {
  it('returns dash for null/undefined', () => {
    expect(formatTokens(null)).toBe('—');
    expect(formatTokens(undefined)).toBe('—');
  });

  it('returns raw number under 1000', () => {
    expect(formatTokens(500)).toBe('500');
  });

  it('formats thousands with k suffix', () => {
    expect(formatTokens(1500)).toBe('1.5k');
  });

  it('formats millions with M suffix', () => {
    expect(formatTokens(2_500_000)).toBe('2.5M');
  });
});

describe('formatPercent', () => {
  it('returns 0% for null/undefined', () => {
    expect(formatPercent(null)).toBe('0%');
    expect(formatPercent(undefined)).toBe('0%');
  });

  it('formats decimal as percentage', () => {
    expect(formatPercent(0.1234)).toBe('12.3%');
  });
});

describe('formatDate', () => {
  it('formats ISO string to readable date', () => {
    const result = formatDate('2025-01-15T14:30:00Z');
    expect(result).toContain('Jan');
    expect(result).toContain('15');
    expect(result).toContain('2025');
  });
});

describe('formatRelativeDate', () => {
  it('returns a relative time string', () => {
    const recent = new Date(Date.now() - 60_000).toISOString();
    const result = formatRelativeDate(recent);
    expect(result).toContain('ago');
  });
});
