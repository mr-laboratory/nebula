// The theme context and its hook, kept apart from the provider for fast refresh.
import { createContext, use } from 'react'

import type { Mode, Resolved } from '@/theme/mode'

export type ThemeState = {
  mode: Mode
  resolved: Resolved
  setMode: (mode: Mode) => void
}

export const ThemeContext = createContext<ThemeState | null>(null)

export function useTheme(): ThemeState {
  const theme = use(ThemeContext)
  if (!theme) throw new Error('useTheme must be used inside <ThemeProvider>')
  return theme
}
