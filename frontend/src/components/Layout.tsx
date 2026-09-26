// App shell: animated nebula background, top navigation and footer around every page.
import { LogOut, ShieldCheck } from 'lucide-react'
import { Link, Outlet, ScrollRestoration, useLocation } from 'react-router'

import { useAuth } from '@/auth/context'
import { Button } from '@/components/ui/button'
import { buttonVariants } from '@/components/ui/button-variants'
import { Avatar } from '@/components/ui/misc'
import { cn } from '@/lib/utils'

function NebulaBackground() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 starfield opacity-60" />
      <div className="absolute -top-1/3 -left-1/4 size-[70vmax] animate-drift rounded-full bg-[radial-gradient(closest-side,rgb(139_92_246/0.28),transparent)] blur-3xl" />
      <div className="absolute -right-1/4 -bottom-1/3 size-[65vmax] animate-drift rounded-full bg-[radial-gradient(closest-side,rgb(34_211_238/0.18),transparent)] blur-3xl [animation-delay:-20s]" />
      <div className="absolute top-1/3 left-1/2 size-[40vmax] animate-drift rounded-full bg-[radial-gradient(closest-side,rgb(244_114_182/0.12),transparent)] blur-3xl [animation-delay:-10s]" />
    </div>
  )
}

export function Logo() {
  return (
    <Link to="/" className="group flex items-center gap-2.5" aria-label="Nebula home">
      <img
        src="/favicon.svg"
        alt=""
        className="size-8 transition duration-500 group-hover:rotate-12"
      />
      <span className="font-display text-xl font-semibold tracking-tight">Nebula</span>
    </Link>
  )
}

function UserMenu() {
  const { me, signOut } = useAuth()
  const location = useLocation()
  const next = encodeURIComponent(location.pathname + location.search)

  if (!me) {
    return (
      <div className="flex items-center gap-2">
        <Link
          to={`/login?next=${next}`}
          className={buttonVariants({ variant: 'ghost', size: 'sm' })}
        >
          Sign in
        </Link>
        <Link
          to={`/register?next=${next}`}
          className={buttonVariants({ variant: 'primary', size: 'sm' })}
        >
          Join Nebula
        </Link>
      </div>
    )
  }

  const moderator = me.roles.includes('moderator')
  return (
    <div className="flex items-center gap-1.5 sm:gap-3">
      <div className="flex items-center gap-2">
        <Avatar name={me.display_name} seed={me.username} />
        <div className="hidden leading-tight sm:block">
          <p className="text-sm font-medium">{me.display_name}</p>
          <p className="flex items-center gap-1 text-xs text-muted">
            @{me.username}
            {moderator && (
              <span className="inline-flex items-center gap-0.5 text-plasma">
                <ShieldCheck className="size-3" aria-hidden /> mod
              </span>
            )}
          </p>
        </div>
      </div>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => void signOut()}
        aria-label="Sign out"
        title="Sign out"
      >
        <LogOut />
      </Button>
    </div>
  )
}

export function Layout() {
  return (
    <div className="flex min-h-dvh flex-col">
      <NebulaBackground />
      <a
        href="#main"
        className="sr-only z-50 rounded-lg bg-void px-3 py-2 focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-40 border-b border-edge/60 bg-void/60 backdrop-blur-xl">
        <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Logo />
          <UserMenu />
        </nav>
      </header>
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 sm:py-12">
        <Outlet />
      </main>
      <footer className="border-t border-edge/60">
        <div
          className={cn(
            'mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-4 py-6 text-sm text-muted sm:flex-row sm:px-6',
          )}
        >
          <p>
            <span className="text-gradient font-medium">Nebula</span> · Where ideas take shape.
          </p>
          <p>Built with FastAPI, PostgreSQL and React.</p>
        </div>
      </footer>
      <ScrollRestoration />
    </div>
  )
}
