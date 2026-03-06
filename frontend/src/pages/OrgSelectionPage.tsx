import { useState } from 'react';
import { useApiKey } from '../hooks/useApiKey';
import { createOrg, searchOrgs, requestToJoin, refreshToken, type OrgResponse } from '../api/orgs';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api';

export function OrgSelectionPage() {
  const { setJwtToken, clearAuth } = useApiKey();

  // Create org state
  const [orgName, setOrgName] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');

  // Search/join state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<OrgResponse[]>([]);
  const [searching, setSearching] = useState(false);
  const [pendingOrgId, setPendingOrgId] = useState<string | null>(null);
  const [joinError, setJoinError] = useState('');

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!orgName.trim()) return;
    setCreating(true);
    setCreateError('');
    try {
      await createOrg(orgName.trim());
      const { token } = await refreshToken();
      setJwtToken(token);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Failed to create organization');
    } finally {
      setCreating(false);
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    setJoinError('');
    try {
      const data = await searchOrgs(searchQuery.trim());
      setSearchResults(data.orgs);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }

  async function handleJoin(orgId: string) {
    setJoinError('');
    try {
      await requestToJoin(orgId);
      setPendingOrgId(orgId);
    } catch (err) {
      setJoinError(err instanceof Error ? err.message : 'Failed to send join request');
    }
  }

  return (
    <div className="min-h-screen bg-surface-primary flex items-center justify-center p-4">
      <div className="w-full max-w-lg space-y-8">
        <div className="text-center">
          <h1 className="text-text-primary text-2xl font-bold">Welcome to Trace</h1>
          <p className="text-text-secondary mt-2">Create or join an organization to get started.</p>
        </div>

        {/* Create Organization */}
        <div className="bg-surface-secondary border border-border rounded-lg p-6">
          <h2 className="text-text-primary text-sm font-medium mb-4">Create Organization</h2>
          <form onSubmit={handleCreate} className="flex gap-2">
            <input
              type="text"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              placeholder="Organization name"
              className="flex-1 bg-surface-tertiary border border-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors"
            />
            <button
              type="submit"
              disabled={creating || !orgName.trim()}
              className="bg-accent hover:bg-accent/90 text-white rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50"
            >
              {creating ? 'Creating...' : 'Create'}
            </button>
          </form>
          {createError && (
            <p className="text-error text-xs mt-2">{createError}</p>
          )}
        </div>

        {/* Join Organization */}
        <div className="bg-surface-secondary border border-border rounded-lg p-6">
          <h2 className="text-text-primary text-sm font-medium mb-4">Join Organization</h2>
          <form onSubmit={handleSearch} className="flex gap-2 mb-4">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name"
              className="flex-1 bg-surface-tertiary border border-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors"
            />
            <button
              type="submit"
              disabled={searching || !searchQuery.trim()}
              className="bg-surface-tertiary hover:bg-surface-tertiary/80 text-text-primary border border-border rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50"
            >
              {searching ? 'Searching...' : 'Search'}
            </button>
          </form>

          {pendingOrgId && (
            <div className="bg-accent/10 border border-accent/30 rounded-md p-3 mb-4">
              <p className="text-accent text-sm font-medium">Request sent! An org owner will review your request.</p>
              <p className="text-text-secondary text-xs mt-2">Once accepted, sign in again to continue.</p>
              <button
                type="button"
                onClick={() => { window.location.href = `${API_BASE}/auth/google`; }}
                className="mt-3 w-full flex items-center justify-center gap-2 bg-white hover:bg-gray-50 text-gray-800 border border-gray-300 rounded-md px-3 py-2 text-sm font-medium transition-colors"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                </svg>
                Sign in with Google
              </button>
            </div>
          )}

          {joinError && (
            <p className="text-error text-xs mb-4">{joinError}</p>
          )}

          {searchResults.length > 0 && (
            <div className="space-y-2">
              {searchResults.map((org) => (
                <div
                  key={org.id}
                  className="flex items-center justify-between py-3 px-3 border border-border rounded-md"
                >
                  <div>
                    <span className="text-text-primary text-sm font-medium">{org.name}</span>
                    <span className="text-text-muted text-xs ml-2">{org.plan}</span>
                  </div>
                  {pendingOrgId === org.id ? (
                    <span className="text-accent text-xs font-medium">Pending</span>
                  ) : (
                    <button
                      onClick={() => handleJoin(org.id)}
                      className="text-xs text-accent hover:text-accent/80 font-medium transition-colors"
                    >
                      Request to Join
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {searchResults.length === 0 && searchQuery && !searching && (
            <p className="text-text-muted text-sm">No organizations found.</p>
          )}
        </div>

        <div className="text-center">
          <button
            onClick={clearAuth}
            className="text-xs text-text-muted hover:text-text-secondary transition-colors"
          >
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}

export default OrgSelectionPage;
