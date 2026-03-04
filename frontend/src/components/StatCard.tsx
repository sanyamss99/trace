import clsx from 'clsx';

interface StatCardProps {
  label: string;
  value: string;
  variant?: 'default' | 'error';
  pulse?: boolean;
}

export function StatCard({ label, value, variant = 'default', pulse = false }: StatCardProps) {
  return (
    <div className="flex flex-col gap-1 py-4">
      <span
        className={clsx(
          'font-mono text-2xl font-semibold tracking-tight',
          variant === 'error' ? 'text-error' : 'text-text-primary',
          pulse && 'animate-pulse',
        )}
      >
        {value}
      </span>
      <span className="text-text-secondary text-sm">{label}</span>
    </div>
  );
}
