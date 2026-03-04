import type { ApiError } from '../api/client';

interface ErrorMessageProps {
  error: Error;
  onRetry?: () => void;
}

export function ErrorMessage({ error, onRetry }: ErrorMessageProps) {
  const isAuthError = (error as ApiError).status === 401;

  return (
    <div className="bg-error-subtle border border-error/20 rounded-md p-4">
      <p className="text-error font-mono text-sm">{error.message}</p>
      {isAuthError && (
        <p className="text-text-secondary text-sm mt-2">
          Check your API key in Settings.
        </p>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 text-sm text-accent hover:text-accent/80 transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}
