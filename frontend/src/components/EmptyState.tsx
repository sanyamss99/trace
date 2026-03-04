interface EmptyStateProps {
  message: string;
  action?: string;
}

export function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <div className="text-center py-12">
      <p className="text-text-secondary text-sm">{message}</p>
      {action && (
        <p className="text-text-muted text-sm mt-2">{action}</p>
      )}
    </div>
  );
}
