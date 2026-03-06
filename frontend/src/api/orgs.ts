import { apiFetch } from './client';

export interface OrgResponse {
  id: string;
  name: string;
  plan: string;
  created_at: string;
}

export interface MemberResponse {
  user_id: string;
  email: string;
  role: string;
  joined_at: string;
}

export interface JoinRequestResponse {
  id: string;
  user_id: string;
  user_email: string;
  status: string;
  created_at: string;
}

export function createOrg(name: string) {
  return apiFetch<OrgResponse>('/orgs', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

export function searchOrgs(query: string) {
  return apiFetch<{ orgs: OrgResponse[] }>(`/orgs/search?q=${encodeURIComponent(query)}`);
}

export function getCurrentOrg() {
  return apiFetch<OrgResponse>('/orgs/current');
}

export function refreshToken() {
  return apiFetch<{ token: string }>('/orgs/current/refresh-token', { method: 'POST' });
}

export function getMembers() {
  return apiFetch<{ members: MemberResponse[] }>('/orgs/current/members');
}

export function updateMemberRole(userId: string, role: 'owner' | 'member') {
  return apiFetch<MemberResponse>(`/orgs/current/members/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify({ role }),
  });
}

export function removeMember(userId: string) {
  return apiFetch<void>(`/orgs/current/members/${userId}`, { method: 'DELETE' });
}

export function requestToJoin(orgId: string) {
  return apiFetch<JoinRequestResponse>(`/orgs/${orgId}/join`, { method: 'POST' });
}

export function getJoinRequests() {
  return apiFetch<{ requests: JoinRequestResponse[] }>('/orgs/current/join-requests');
}

export function resolveJoinRequest(requestId: string, action: 'accept' | 'decline') {
  return apiFetch<JoinRequestResponse>(`/orgs/current/join-requests/${requestId}`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  });
}
