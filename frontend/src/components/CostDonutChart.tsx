import { PieChart, Pie, Cell, Legend, ResponsiveContainer, Tooltip } from 'recharts';
import { SEGMENT_DOT_COLORS } from '../utils/colors';
import { formatCost } from '../utils/formatters';
import type { ModelCostItem } from '../types/analytics';

interface CostDonutChartProps {
  data: ModelCostItem[];
}

export function CostDonutChart({ data }: CostDonutChartProps) {
  const total = data.reduce((sum, d) => sum + (d.total_cost_usd ?? 0), 0);
  const slices = data
    .filter((d) => (d.total_cost_usd ?? 0) > 0)
    .map((d) => ({
      name: d.model,
      value: d.total_cost_usd ?? 0,
      pct: total > 0 ? ((d.total_cost_usd ?? 0) / total) * 100 : 0,
    }));

  if (slices.length === 0) return null;

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={slices}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius="55%"
            outerRadius="80%"
            paddingAngle={2}
            stroke="none"
          >
            {slices.map((_, i) => (
              <Cell
                key={i}
                fill={SEGMENT_DOT_COLORS[i % SEGMENT_DOT_COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number) => formatCost(value)}
            contentStyle={{
              backgroundColor: 'var(--color-surface-tertiary, #1e1e2e)',
              border: '1px solid var(--color-border, #333)',
              borderRadius: '6px',
              fontSize: '12px',
            }}
            itemStyle={{ color: 'var(--color-text-secondary, #ccc)' }}
          />
          <Legend
            verticalAlign="bottom"
            formatter={(value: string) => {
              const item = slices.find((s) => s.name === value);
              return (
                <span className="text-text-secondary text-xs">
                  {value} ({item ? `${item.pct.toFixed(1)}%` : ''})
                </span>
              );
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
