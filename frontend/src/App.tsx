import { lazy, Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import { useApiKey } from './hooks/useApiKey';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Layout } from './components/Layout';
import { LoginPage } from './pages/LoginPage';
import { LoadingSpinner } from './components/LoadingSpinner';

const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const TracesPage = lazy(() => import('./pages/TracesPage'));
const TraceDetailPage = lazy(() => import('./pages/TraceDetailPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));

function OAuthCallbackHandler() {
  const { setJwtToken } = useApiKey();

  useEffect(() => {
    const hash = window.location.hash;
    if (hash.startsWith('#token=')) {
      const token = hash.slice('#token='.length);
      if (token) {
        setJwtToken(token);
        // Clean the hash from URL
        window.history.replaceState(null, '', window.location.pathname);
      }
    }
  }, [setJwtToken]);

  return null;
}

function AuthGate() {
  const { apiKey } = useApiKey();

  if (!apiKey) {
    return <LoginPage />;
  }

  return (
    <Suspense fallback={<div className="py-12"><LoadingSpinner /></div>}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="traces" element={<TracesPage />} />
          <Route path="traces/:traceId" element={<TraceDetailPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <ErrorBoundary>
        <BrowserRouter>
          <AuthProvider>
            <OAuthCallbackHandler />
            <Routes>
              <Route path="/*" element={<AuthGate />} />
            </Routes>
          </AuthProvider>
        </BrowserRouter>
      </ErrorBoundary>
    </ThemeProvider>
  );
}
