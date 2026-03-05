/* eslint-disable react-refresh/only-export-components */
import { createContext, useState, useCallback, type ReactNode } from 'react';

export type AuthType = 'jwt' | 'api_key' | null;

export interface AuthContextValue {
  apiKey: string | null;
  authType: AuthType;
  setApiKey: (key: string) => void;
  setJwtToken: (token: string) => void;
  clearApiKey: () => void;
  clearAuth: () => void;
}

export const AuthContext = createContext<AuthContextValue>({
  apiKey: null,
  authType: null,
  setApiKey: () => {},
  setJwtToken: () => {},
  clearApiKey: () => {},
  clearAuth: () => {},
});

const API_KEY_STORAGE = 'trace_api_key';
const JWT_STORAGE = 'trace_jwt';
const AUTH_TYPE_STORAGE = 'trace_auth_type';

function loadInitialAuth(): { credential: string | null; authType: AuthType } {
  const authType = localStorage.getItem(AUTH_TYPE_STORAGE) as AuthType;
  if (authType === 'jwt') {
    const jwt = localStorage.getItem(JWT_STORAGE);
    if (jwt) return { credential: jwt, authType: 'jwt' };
  }
  if (authType === 'api_key') {
    const apiKey = localStorage.getItem(API_KEY_STORAGE);
    if (apiKey) return { credential: apiKey, authType: 'api_key' };
  }
  // Legacy: check for api key without auth type
  const legacyKey = localStorage.getItem(API_KEY_STORAGE);
  if (legacyKey) return { credential: legacyKey, authType: 'api_key' };
  return { credential: null, authType: null };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [{ credential, authType }, setState] = useState(loadInitialAuth);

  const setApiKey = useCallback((key: string) => {
    localStorage.setItem(API_KEY_STORAGE, key);
    localStorage.setItem(AUTH_TYPE_STORAGE, 'api_key');
    setState({ credential: key, authType: 'api_key' });
  }, []);

  const setJwtToken = useCallback((token: string) => {
    localStorage.setItem(JWT_STORAGE, token);
    localStorage.setItem(AUTH_TYPE_STORAGE, 'jwt');
    setState({ credential: token, authType: 'jwt' });
  }, []);

  const clearAuth = useCallback(() => {
    localStorage.removeItem(API_KEY_STORAGE);
    localStorage.removeItem(JWT_STORAGE);
    localStorage.removeItem(AUTH_TYPE_STORAGE);
    setState({ credential: null, authType: null });
  }, []);

  return (
    <AuthContext value={{
      apiKey: credential,
      authType,
      setApiKey,
      setJwtToken,
      clearApiKey: clearAuth,
      clearAuth,
    }}>
      {children}
    </AuthContext>
  );
}
