import { useState } from 'react';
import { useApiKey } from '../hooks/useApiKey';

export function ApiKeySetup() {
  const { setApiKey } = useApiKey();
  const [value, setValue] = useState('');
  const [error, setError] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) {
      setError('API key is required');
      return;
    }
    setApiKey(trimmed);
  }

  return (
    <div className="min-h-screen bg-surface-primary flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="bg-surface-secondary border border-border rounded-lg p-8">
          <div className="text-center mb-6">
            <span className="text-accent text-3xl font-bold">&#9671;</span>
            <h1 className="text-text-primary text-xl font-semibold mt-3">
              Connect to your Trace instance
            </h1>
            <p className="text-text-secondary text-sm mt-2">
              Enter your API key to access the dashboard.
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            <input
              type="password"
              value={value}
              onChange={(e) => {
                setValue(e.target.value);
                setError('');
              }}
              placeholder="tr-xxxxxxxxxxxxxxxxxxxx"
              className="w-full bg-surface-tertiary border border-border rounded-md px-4 py-2.5 text-text-primary font-mono text-sm placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors"
              autoFocus
            />
            {error && (
              <p className="text-error text-sm mt-2">{error}</p>
            )}
            <button
              type="submit"
              className="w-full mt-4 bg-accent hover:bg-accent/90 text-white rounded-md px-4 py-2.5 text-sm font-medium transition-colors"
            >
              Connect
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
