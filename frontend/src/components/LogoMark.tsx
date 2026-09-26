// The Nebula mark: a glowing core with a tilted orbit that passes behind and in front of it.
import { useId } from 'react'

import { cn } from '@/lib/utils'

export function LogoMark({ className }: { className?: string }) {
  const id = `l${useId().replace(/[^a-zA-Z0-9]/g, '')}`
  const orbit = 'M4 21 A 12 5.2 -24 0 0 28 11'
  return (
    <svg viewBox="0 0 32 32" aria-hidden className={cn('size-8', className)}>
      <defs>
        <linearGradient id={`${id}-core`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" style={{ stopColor: 'var(--nb-plasma)' }} />
          <stop offset="1" style={{ stopColor: 'var(--nb-nova)' }} />
        </linearGradient>
      </defs>
      {/* back half of the orbit, drawn before the core so the core hides it */}
      <path
        d="M28 11 A 12 5.2 -24 0 0 4 21"
        fill="none"
        strokeWidth={1.6}
        strokeLinecap="round"
        style={{ stroke: 'var(--nb-muted)', opacity: 0.55 }}
      />
      <circle cx={16} cy={16} r={7.5} style={{ fill: `url(#${id}-core)` }} />
      <path
        d={orbit}
        fill="none"
        strokeWidth={1.8}
        strokeLinecap="round"
        style={{ stroke: 'var(--nb-ink)' }}
      />
      <circle cx={26.4} cy={12.1} r={2} style={{ fill: 'var(--nb-flare)' }} />
    </svg>
  )
}
