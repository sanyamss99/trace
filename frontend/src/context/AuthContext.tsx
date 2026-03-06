/* eslint-disable react-refresh/only-export-components */
import { createContext, useState, useCallback, type ReactNode } from 'react';

export type AuthType = 'jwt' | 'api_key' | null;

export interface AuthContextValue {
  apiKey: string | null;
  authType: AuthType;
  orgId: string | null;
  userId: string | null;
  setApiKey: (key: string) => void;
  setJwtToken: (token: string) => void;
  clearApiKey: () => void;
  clearAuth: () => void;
}

export const AuthContext = createContext<AuthContextValue>({
  apiKey: null,
  authType: null,
  orgId: null,
  userId: null,
  setApiKey: () => {},
  setJwtToken: () => {},
  clearApiKey: () => {},
  clearAuth: () => {},
});

const API_KEY_STORAGE = 'trace_api_key';
const JWT_STORAGE = 'trace_jwt';
const AUTH_TYPE_STORAGE = 'trace_auth_type';

interface JwtPayload {
  sub?: string;
  org_id?: string;
}

function decodeJwtPayload(token: string): JwtPayload {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return {};
    const payload = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(payload) as JwtPayload;
  } catch {
    return {};
  }
}

interface AuthState {
  credential: string | null;
  authType: AuthType;
  orgId: string | null;
  userId: string | null;
}

function loadInitialAuth(): AuthState {
  const authType = localStorage.getItem(AUTH_TYPE_STORAGE) as AuthType;
  if (authType === 'jwt') {
    const jwt = localStorage.getItem(JWT_STORAGE);
    if (jwt) {
      const payload = decodeJwtPayload(jwt);
      return {
        credential: jwt,
        authType: 'jwt',
        orgId: payload.org_id || null,
        userId: payload.sub || null,
      };
    }
  }
  if (authType === 'api_key') {
    const apiKey = localStorage.getItem(API_KEY_STORAGE);
    if (apiKey) return { credential: apiKey, authType: 'api_key', orgId: 'api_key', userId: null };
  }
  // Legacy: check for api key without auth type
  const legacyKey = localStorage.getItem(API_KEY_STORAGE);
  if (legacyKey) return { credential: legacyKey, authType: 'api_key', orgId: 'api_key', userId: null };
  return { credential: null, authType: null, orgId: null, userId: null };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [{ credential, authType, orgId, userId }, setState] = useState(loadInitialAuth);

  const setApiKey = useCallback((key: string) => {
    localStorage.setItem(API_KEY_STORAGE, key);
    localStorage.setItem(AUTH_TYPE_STORAGE, 'api_key');
    setState({ credential: key, authType: 'api_key', orgId: 'api_key', userId: null });
  }, []);

  const setJwtToken = useCallback((token: string) => {
    localStorage.setItem(JWT_STORAGE, token);
    localStorage.setItem(AUTH_TYPE_STORAGE, 'jwt');
    const payload = decodeJwtPayload(token);
    setState({
      credential: token,
      authType: 'jwt',
      orgId: payload.org_id || null,
      userId: payload.sub || null,
    });
  }, []);

  const clearAuth = useCallback(() => {
    localStorage.removeItem(API_KEY_STORAGE);
    localStorage.removeItem(JWT_STORAGE);
    localStorage.removeItem(AUTH_TYPE_STORAGE);
    setState({ credential: null, authType: null, orgId: null, userId: null });
  }, []);

  return (
    <AuthContext value={{
      apiKey: credential,
      authType,
      orgId,
      userId,
      setApiKey,
      setJwtToken,
      clearApiKey: clearAuth,
      clearAuth,
    }}>
      {children}
    </AuthContext>
  );
}
