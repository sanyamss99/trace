import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import { useApiKey } from './hooks/useApiKey';
import { Layout } from './components/Layout';
import { ApiKeySetup } from './components/ApiKeySetup';
import { DashboardPage } from './pages/DashboardPage';
import { TracesPage } from './pages/TracesPage';
import { TraceDetailPage } from './pages/TraceDetailPage';
import { SettingsPage } from './pages/SettingsPage';

function AuthGate() {
  const { apiKey } = useApiKey();

  if (!apiKey) {
    return <ApiKeySetup />;
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="traces" element={<TracesPage />} />
        <Route path="traces/:traceId" element={<TraceDetailPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/*" element={<AuthGate />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}
