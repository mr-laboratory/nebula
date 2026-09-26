// Holds the theme mode, follows the OS setting in "system" mode and applies the result to <html>.
import { useEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from 'react'

import { ThemeContext } from '@/theme/context'
import { applyMode, loadMode, saveMode, systemPrefersDark, type Mode } from '@/theme/mode'

function subscribe(onChange: () => void): () => void {
  const query = window.matchMedia('(prefers-color-scheme: dark)')
  query.addEventListener('change', onChange)
  return () => query.removeEventListener('change', onChange)
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState(loadMode)
  const systemDark = useSyncExternalStore(subscribe, systemPrefersDark)
  const resolved = mode === 'system' ? (systemDark ? 'dark' : 'light') : mode

  useEffect(() => applyMode(resolved), [resolved])

  const value = useMemo(
    () => ({
      mode,
      resolved,
      setMode: (next: Mode) => {
        saveMode(next)
        setModeState(next)
      },
    }),
    [mode, resolved],
  )

  return <ThemeContext value={value}>{children}</ThemeContext>
}
