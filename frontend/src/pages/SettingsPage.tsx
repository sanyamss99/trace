import { useState } from 'react';
import { useApiKey } from '../hooks/useApiKey';
import { useApiKeys } from '../hooks/useApiKeys';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { formatRelativeDate } from '../utils/formatters';

export function SettingsPage() {
  const { apiKey, clearApiKey } = useApiKey();
  const { keys, loading, error, create, revoke, refetch } = useApiKeys();
  const [newKeyName, setNewKeyName] = useState('');
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [confirmingDisconnect, setConfirmingDisconnect] = useState(false);
  const [confirmingRevokeId, setConfirmingRevokeId] = useState<string | null>(null);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    setCreating(true);
    try {
      const result = await create(newKeyName.trim());
      setCreatedKey(result.raw_key);
      setNewKeyName('');
    } catch {
      // error handled by hook
    } finally {
      setCreating(false);
    }
  }

  async function handleCopy() {
    if (!createdKey) return;
    await navigator.clipboard.writeText(createdKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-text-primary text-lg font-semibold mb-6">Settings</h1>

      {/* Active connection */}
      <div className="bg-surface-secondary border border-border rounded-lg p-5 mb-6">
        <h2 className="text-text-primary text-sm font-medium mb-3">Active Connection</h2>
        <div className="flex items-center justify-between">
          <span className="font-mono text-xs text-text-secondary">
            {apiKey ? `${apiKey.slice(0, 8)}${'*'.repeat(12)}` : 'Not connected'}
          </span>
          {apiKey && (
            confirmingDisconnect ? (
              <span className="flex items-center gap-2 text-xs">
                <span className="text-text-secondary">Disconnect?</span>
                <button
                  onClick={() => { clearApiKey(); setConfirmingDisconnect(false); }}
                  className="text-error hover:text-error/80 transition-colors font-medium"
                >
                  Yes
                </button>
                <button
                  onClick={() => setConfirmingDisconnect(false)}
                  className="text-text-muted hover:text-text-secondary transition-colors"
                >
                  Cancel
                </button>
              </span>
            ) : (
              <button
                onClick={() => setConfirmingDisconnect(true)}
                className="text-xs text-text-muted hover:text-error transition-colors"
              >
                Disconnect
              </button>
            )
          )}
        </div>
      </div>

      {/* Create new key */}
      <div className="bg-surface-secondary border border-border rounded-lg p-5 mb-6">
        <h2 className="text-text-primary text-sm font-medium mb-3">Create API Key</h2>
        <form onSubmit={handleCreate} className="flex gap-2">
          <input
            type="text"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="Key name"
            className="flex-1 bg-surface-tertiary border border-border rounded-md px-3 py-1.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors"
          />
          <button
            type="submit"
            disabled={creating || !newKeyName.trim()}
            className="bg-accent hover:bg-accent/90 text-white rounded-md px-4 py-1.5 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {creating ? 'Creating...' : 'Create'}
          </button>
        </form>

        {createdKey && (
          <div className="mt-4 bg-surface-tertiary border border-warning/30 rounded-md p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-warning text-xs font-medium">
                Save this — you won&apos;t see it again
              </span>
              <button
                onClick={handleCopy}
                className="text-xs text-accent hover:text-accent/80 transition-colors"
              >
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <code className="font-mono text-xs text-text-primary break-all">
              {createdKey}
            </code>
          </div>
        )}
      </div>

      {/* Key list */}
      <div className="bg-surface-secondary border border-border rounded-lg p-5">
        <h2 className="text-text-primary text-sm font-medium mb-3">API Keys</h2>
        {error ? (
          <ErrorMessage error={error} onRetry={refetch} />
        ) : loading ? (
          <LoadingSpinner />
        ) : keys.length === 0 ? (
          <p className="text-text-muted text-sm">No API keys yet.</p>
        ) : (
          <div className="space-y-2">
            {keys.map((key) => (
              <div
                key={key.id}
                className="flex items-center justify-between py-2 border-b border-border last:border-0"
              >
                <div>
                  <span className="text-text-primary text-sm">{key.name ?? 'Unnamed'}</span>
                  <div className="flex gap-3 mt-0.5">
                    <span className="text-text-muted text-xs">
                      Created {formatRelativeDate(key.created_at)}
                    </span>
                    <span className="text-text-muted text-xs">
                      {key.last_used_at
                        ? `Last used ${formatRelativeDate(key.last_used_at)}`
                        : 'Never used'}
                    </span>
                  </div>
                </div>
                {!key.revoked_at && (
                  confirmingRevokeId === key.id ? (
                    <span className="flex items-center gap-2 text-xs">
                      <span className="text-text-secondary">Revoke?</span>
                      <button
                        onClick={() => { revoke(key.id); setConfirmingRevokeId(null); }}
                        className="text-error hover:text-error/80 transition-colors font-medium"
                      >
                        Yes
                      </button>
                      <button
                        onClick={() => setConfirmingRevokeId(null)}
                        className="text-text-muted hover:text-text-secondary transition-colors"
                      >
                        Cancel
                      </button>
                    </span>
                  ) : (
                    <button
                      onClick={() => setConfirmingRevokeId(key.id)}
                      className="text-xs text-text-muted hover:text-error transition-colors"
                    >
                      Revoke
                    </button>
                  )
                )}
                {key.revoked_at && (
                  <span className="text-xs text-text-muted">Revoked</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default SettingsPage;
