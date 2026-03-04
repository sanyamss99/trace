import { createContext, useState, useCallback, type ReactNode } from 'react';

export interface AuthContextValue {
  apiKey: string | null;
  setApiKey: (key: string) => void;
  clearApiKey: () => void;
}

export const AuthContext = createContext<AuthContextValue>({
  apiKey: null,
  setApiKey: () => {},
  clearApiKey: () => {},
});

const STORAGE_KEY = 'trace_api_key';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKeyState] = useState<string | null>(
    () => localStorage.getItem(STORAGE_KEY),
  );

  const setApiKey = useCallback((key: string) => {
    localStorage.setItem(STORAGE_KEY, key);
    setApiKeyState(key);
  }, []);

  const clearApiKey = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setApiKeyState(null);
  }, []);

  return (
    <AuthContext value={{ apiKey, setApiKey, clearApiKey }}>
      {children}
    </AuthContext>
  );
}
