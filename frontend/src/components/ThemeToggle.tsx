// Header button that cycles the theme: follow the system, light, then dark.
import { Monitor, Moon, Sun } from 'lucide-react'

import { buttonVariants } from '@/components/ui/button-variants'
import { pick } from '@/lib/utils'
import { useTheme } from '@/theme/context'
import { MODES } from '@/theme/mode'

const LABELS = { system: 'System theme', light: 'Light theme', dark: 'Dark theme' }
const ICONS = { system: Monitor, light: Sun, dark: Moon }

export function ThemeToggle() {
  const { mode, setMode } = useTheme()
  const next = pick(MODES, MODES.indexOf(mode) + 1)
  const Icon = ICONS[mode]
  return (
    <button
      type="button"
      onClick={() => setMode(next)}
      className={buttonVariants({ variant: 'ghost', size: 'icon' })}
      aria-label={`${LABELS[mode]}. Switch to ${LABELS[next].toLowerCase()}`}
      title={LABELS[mode]}
    >
      <Icon />
    </button>
  )
}
