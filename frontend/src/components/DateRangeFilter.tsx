import { useState, useMemo } from 'react';
import clsx from 'clsx';
import { subDays, subHours, formatISO } from 'date-fns';

export interface DateRange {
  started_after?: string;
  started_before?: string;
}

type Preset = '24h' | '7d' | '30d' | 'all' | 'custom';

interface DateRangeFilterProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
}

export function DateRangeFilter({ value, onChange }: DateRangeFilterProps) {
  const [activePreset, setActivePreset] = useState<Preset>(() => {
    if (!value.started_after) return 'all';
    return '7d';
  });
  const [showCustom, setShowCustom] = useState(false);

  const presets: { key: Preset; label: string }[] = useMemo(() => [
    { key: '24h', label: '24h' },
    { key: '7d', label: '7d' },
    { key: '30d', label: '30d' },
    { key: 'all', label: 'All' },
    { key: 'custom', label: 'Custom' },
  ], []);

  function handlePreset(preset: Preset) {
    setActivePreset(preset);
    if (preset === 'custom') {
      setShowCustom(true);
      return;
    }
    setShowCustom(false);
    const now = new Date();
    let started_after: string | undefined;
    if (preset === '24h') started_after = formatISO(subHours(now, 24));
    else if (preset === '7d') started_after = formatISO(subDays(now, 7));
    else if (preset === '30d') started_after = formatISO(subDays(now, 30));
    onChange({ started_after, started_before: undefined });
  }

  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-1">
        {presets.map((p) => (
          <button
            key={p.key}
            onClick={() => handlePreset(p.key)}
            className={clsx(
              'px-3 py-1 text-xs rounded-md transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-none',
              activePreset === p.key
                ? 'bg-accent text-white'
                : 'text-text-secondary hover:text-text-primary hover:bg-surface-tertiary',
            )}
          >
            {p.label}
          </button>
        ))}
      </div>
      {showCustom && (
        <div className="flex items-center gap-2 ml-2">
          <input
            type="date"
            className="bg-surface-tertiary border border-border rounded px-2 py-1 text-xs text-text-primary"
            onChange={(e) =>
              onChange({
                ...value,
                started_after: e.target.value ? new Date(e.target.value).toISOString() : undefined,
              })
            }
          />
          <span className="text-text-muted text-xs">to</span>
          <input
            type="date"
            className="bg-surface-tertiary border border-border rounded px-2 py-1 text-xs text-text-primary"
            onChange={(e) =>
              onChange({
                ...value,
                started_before: e.target.value ? new Date(e.target.value).toISOString() : undefined,
              })
            }
          />
        </div>
      )}
    </div>
  );
}
