import { useState } from 'react';
import { useApiKey } from '../hooks/useApiKey';
import { createOrg, searchOrgs, requestToJoin, refreshToken, type OrgResponse } from '../api/orgs';

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
