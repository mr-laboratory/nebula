// Shared empty, error and loading states so every page fails and waits the same way.
import { AlertTriangle, Orbit } from 'lucide-react'
import type { ReactNode } from 'react'

import { describeError } from '@/api/errors'
import { LogoMark } from '@/components/LogoMark'
import { Button } from '@/components/ui/button'
import { Card, Skeleton } from '@/components/ui/misc'

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <Card className="flex flex-col items-center gap-4 p-10 text-center" role="alert">
      <AlertTriangle className="size-8 text-danger" aria-hidden />
      <p className="text-muted">{describeError(error)}</p>
      {onRetry && <Button onClick={onRetry}>Try again</Button>}
    </Card>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <Card className="flex flex-col items-center gap-3 p-12 text-center">
      <Orbit className="size-10 text-nova" aria-hidden />
      <h2 className="font-display text-lg font-semibold">{title}</h2>
      {children && <div className="text-muted">{children}</div>}
    </Card>
  )
}

export function PostCardSkeleton() {
  return (
    <Card className="overflow-hidden" aria-hidden>
      <Skeleton className="h-28 rounded-none" />
      <div className="space-y-3 p-5">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="mt-4 h-8 w-1/2" />
      </div>
    </Card>
  )
}

export function Splash() {
  return (
    <output className="grid min-h-dvh place-items-center bg-void" aria-label="Loading">
      <LogoMark className="size-14 animate-pulse" />
    </output>
  )
}
