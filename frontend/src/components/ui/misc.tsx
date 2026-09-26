// Small presentational pieces: glass card, tag chip, skeleton, avatar.
import type { ComponentProps } from 'react'

import { avatarBackground } from '@/lib/covers'
import { cn, initials } from '@/lib/utils'

export function Card({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('rounded-2xl glass', className)} {...props} />
}

export function Chip({
  className,
  active = false,
  ...props
}: ComponentProps<'span'> & { active?: boolean }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition',
        active
          ? 'border-plasma/60 bg-plasma/15 text-plasma'
          : 'border-edge bg-ink/[0.03] text-muted hover:border-nova/50 hover:text-ink',
        className,
      )}
      {...props}
    />
  )
}

export function Skeleton({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('animate-pulse rounded-lg bg-ink/[0.07]', className)} {...props} />
}

export function Avatar({
  name,
  seed,
  className,
}: {
  name: string
  seed: string
  className?: string
}) {
  return (
    <span
      aria-hidden
      className={cn(
        'inline-grid size-8 shrink-0 place-items-center rounded-full text-xs font-semibold text-void ring-1 ring-edge',
        className,
      )}
      style={{ background: avatarBackground(seed) }}
    >
      {initials(name)}
    </span>
  )
}
