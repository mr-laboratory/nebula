// Shared frame for the sign-in and register pages: centred glass card with a heading.
import type { ReactNode } from 'react'

import { Card } from '@/components/ui/misc'

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle: string
  children: ReactNode
  footer: ReactNode
}) {
  return (
    <div className="mx-auto w-full max-w-md py-6 sm:py-12">
      <title>{`${title} · Nebula`}</title>
      <Card className="space-y-6 p-6 shadow-glow sm:p-8">
        <div className="space-y-1 text-center">
          <h1 className="font-display text-3xl font-bold">{title}</h1>
          <p className="text-muted">{subtitle}</p>
        </div>
        {children}
      </Card>
      <p className="mt-6 text-center text-sm text-muted">{footer}</p>
    </div>
  )
}
