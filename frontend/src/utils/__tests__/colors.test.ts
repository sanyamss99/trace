import {
  scoreBarColor,
  segmentBgColor,
  segmentBorderColor,
  influenceToColor,
  SEGMENT_DOT_COLORS,
} from '../colors';

describe('scoreBarColor', () => {
  it('returns muted color for scores below 0.1', () => {
    const color = scoreBarColor(0.05);
    expect(color).toContain('505468');
  });

  it('returns a heatmap color for higher scores', () => {
    const color = scoreBarColor(0.5);
    expect(color).toMatch(/rgb/);
  });
});

describe('segmentBgColor', () => {
  it('returns dark background for near-zero influence', () => {
    const color = segmentBgColor(0.01);
    expect(color).toBeTruthy();
  });

  it('returns a different color when hovered', () => {
    const normal = segmentBgColor(0.5);
    const hovered = segmentBgColor(0.5, true);
    expect(normal).not.toBe(hovered);
  });
});

describe('segmentBorderColor', () => {
  it('returns muted color for near-zero influence', () => {
    const color = segmentBorderColor(0.01);
    expect(color).toContain('505468');
  });

  it('returns an interpolated color for significant influence', () => {
    const color = segmentBorderColor(0.8);
    expect(color).toMatch(/rgb/);
  });
});

describe('influenceToColor', () => {
  it('returns muted color for null or low scores', () => {
    expect(influenceToColor(null)).toContain('505468');
    expect(influenceToColor(0.1)).toContain('505468');
  });

  it('returns a heatmap color for significant scores', () => {
    const color = influenceToColor(0.8);
    expect(color).toMatch(/rgb/);
  });
});

describe('SEGMENT_DOT_COLORS', () => {
  it('is an array of 6 hex colors', () => {
    expect(SEGMENT_DOT_COLORS).toHaveLength(6);
    for (const color of SEGMENT_DOT_COLORS) {
      expect(color).toMatch(/^#[0-9a-f]{6}$/i);
    }
  });
});
