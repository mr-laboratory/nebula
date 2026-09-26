// Theme mode (system, light or dark): how it's stored, resolved and applied to <html>.
export const MODES = ['system', 'light', 'dark'] as const
export type Mode = (typeof MODES)[number]
export type Resolved = 'light' | 'dark'

const KEY = 'nebula:theme' // also read by public/theme-init.js before first paint

export function loadMode(): Mode {
  try {
    const stored = localStorage.getItem(KEY)
    return MODES.includes(stored as Mode) ? (stored as Mode) : 'system'
  } catch {
    return 'system' // storage blocked (private mode, strict settings)
  }
}

export function saveMode(mode: Mode): void {
  try {
    localStorage.setItem(KEY, mode)
  } catch {
    // not persisted; the choice still applies for this visit
  }
}

export function systemPrefersDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/** Reflect the mode on <html>; CSS picks every color from the data-mode attribute. */
export function applyMode(mode: Resolved): void {
  const root = document.documentElement
  root.dataset.mode = mode
  root.style.colorScheme = mode
  const bg = getComputedStyle(root).getPropertyValue('--nb-void').trim()
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', bg || '#0b0d1c')
}
