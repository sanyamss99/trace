import { useState } from 'react';
import {
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Line,
  ComposedChart,
} from 'recharts';
import clsx from 'clsx';
import { format } from 'date-fns';
import { cssVar } from '../utils/colors';
import type { TimeSeriesPoint } from '../types/analytics';

type Metric = 'volume' | 'cost' | 'errors';

interface TimeseriesChartProps {
  data: TimeSeriesPoint[];
}

export function TimeseriesChart({ data }: TimeseriesChartProps) {
  const [metric, setMetric] = useState<Metric>('volume');

  const tabs: { key: Metric; label: string }[] = [
    { key: 'volume', label: 'Volume' },
    { key: 'cost', label: 'Cost' },
    { key: 'errors', label: 'Errors' },
  ];

  function getDataKey(): string {
    if (metric === 'volume') return 'trace_count';
    if (metric === 'cost') return 'total_cost_usd';
    return 'error_count';
  }

  function getColor(): string {
    if (metric === 'errors') return cssVar('--raw-error') || '#ef4444';
    return cssVar('--raw-accent') || '#6366f1';
  }

  const tickFill = cssVar('--raw-chart-tick') || '#505468';
  const errorColor = cssVar('--raw-error') || '#ef4444';

  return (
    <div>
      <div className="flex gap-1 mb-4">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setMetric(tab.key)}
            className={clsx(
              'px-2.5 py-1 text-xs rounded transition-colors',
              metric === tab.key
                ? 'text-accent bg-accent-subtle'
                : 'text-text-muted hover:text-text-secondary',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={data}>
          <XAxis
            dataKey="date"
            tick={{ fill: tickFill, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(d: string) => format(new Date(d), 'MMM d')}
          />
          <YAxis
            tick={{ fill: tickFill, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={40}
            tickCount={3}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: cssVar('--raw-chart-tooltip-bg') || '#12131a',
              border: `1px solid ${cssVar('--raw-chart-tooltip-border') || '#232530'}`,
              borderRadius: '6px',
              fontSize: '12px',
              color: cssVar('--raw-chart-tooltip-text') || '#e8eaf0',
            }}
            labelFormatter={(d: string) => format(new Date(d), 'MMM d, yyyy')}
          />
          <Area
            type="monotone"
            dataKey={getDataKey()}
            stroke={getColor()}
            strokeWidth={1.5}
            fill={getColor()}
            fillOpacity={0.15}
          />
          {metric === 'volume' && (
            <Line
              type="monotone"
              dataKey="error_count"
              stroke={errorColor}
              strokeWidth={1}
              dot={{ fill: errorColor, r: 2 }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
