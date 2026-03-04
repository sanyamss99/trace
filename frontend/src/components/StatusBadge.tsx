import clsx from 'clsx';

interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const isError = status === 'error';
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium',
        isError
          ? 'text-error bg-error-subtle'
          : 'text-success bg-success/10',
      )}
    >
      <span
        className={clsx(
          'w-1.5 h-1.5 rounded-full',
          isError ? 'bg-error' : 'bg-success',
        )}
      />
      {status}
    </span>
  );
}
