import { use } from 'react';
import { ThemeContext } from '../context/ThemeContext';
import type { ThemeContextValue } from '../context/ThemeContext';

export function useTheme(): ThemeContextValue {
  const ctx = use(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
