import { useState } from 'react';
import { useApiKey } from '../hooks/useApiKey';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api';

export function LoginPage() {
  const { setApiKey } = useApiKey();
  const [showApiKey, setShowApiKey] = useState(false);
  const [value, setValue] = useState('');
  const [error, setError] = useState('');

  function handleGoogleLogin() {
    window.location.href = `${API_BASE}/auth/google`;
  }

  function handleApiKeySubmit(e: React.FormEvent) {
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
              Sign in to Trace
            </h1>
            <p className="text-text-secondary text-sm mt-2">
              Debug your LLM applications in real time.
            </p>
          </div>

          <button
            type="button"
            onClick={handleGoogleLogin}
            className="w-full flex items-center justify-center gap-3 bg-white hover:bg-gray-50 text-gray-800 border border-gray-300 rounded-md px-4 py-2.5 text-sm font-medium transition-colors"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                fill="#4285F4"
              />
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                fill="#34A853"
              />
              <path
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                fill="#FBBC05"
              />
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#EA4335"
              />
            </svg>
            Sign in with Google
          </button>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs">
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="bg-surface-secondary px-2 text-text-muted hover:text-text-secondary transition-colors"
              >
                {showApiKey ? 'Hide' : 'Use API key instead'}
              </button>
            </div>
          </div>

          {showApiKey && (
            <form onSubmit={handleApiKeySubmit}>
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
          )}
        </div>
      </div>
    </div>
  );
}
