import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { useTheme } from '../hooks/useTheme';

function ThemeToggle() {
  const { theme, toggle } = useTheme();

  return (
    <button
      onClick={toggle}
      className="flex items-center gap-1.5 px-2 py-1 rounded text-text-secondary hover:text-text-primary hover:bg-surface-tertiary transition-colors text-xs"
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      {theme === 'light' ? (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="5" />
          <path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
        </svg>
      ) : (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      )}
      <span>{theme === 'light' ? 'Light' : 'Dark'}</span>
    </button>
  );
}

export function Layout() {
  return (
    <div className="min-h-screen bg-surface-primary">
      <Sidebar />
      <div className="ml-14 flex flex-col">
        <header className="flex items-center justify-end px-6 py-2 border-b border-border">
          <ThemeToggle />
        </header>
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
