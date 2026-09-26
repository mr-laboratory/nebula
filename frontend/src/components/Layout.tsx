// App shell: themed backdrop, top navigation and footer around every page.
import { ChevronDown, LayoutList, LogOut, PenLine, ShieldCheck, UserRound } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useId, useRef, useState } from 'react'
import { Link, Outlet, ScrollRestoration, useLocation } from 'react-router'

import { useAuth } from '@/auth/context'
import { LogoMark } from '@/components/LogoMark'
import { ThemeToggle } from '@/components/ThemeToggle'
import { buttonVariants } from '@/components/ui/button-variants'
import { Avatar } from '@/components/ui/misc'
import { cn } from '@/lib/utils'

// Layers are styled in index.css (see "Page backdrop").
function NebulaBackground() {
  return (
    <div aria-hidden className="nb-backdrop">
      <div className="nb-glow-a" />
      <div className="nb-glow-b" />
      <div className="nb-stars starfield" />
      <div className="nb-grain" />
    </div>
  )
}

export function Logo() {
  return (
    <Link to="/" className="group flex items-center gap-2.5" aria-label="Nebula home">
      <LogoMark className="transition duration-500 group-hover:rotate-[-14deg]" />
      <span className="font-display text-xl font-semibold tracking-tight">Nebula</span>
    </Link>
  )
}

function AccountMenu() {
  const { me, signOut } = useAuth()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [at, setAt] = useState(location.key)
  const root = useRef<HTMLDivElement>(null)
  const menuId = useId()
  // Close on navigation (adjusting state during render instead of an effect).
  if (location.key !== at) {
    setAt(location.key)
    setOpen(false)
  }

  useEffect(() => {
    if (!open) return
    function onPointer(event: PointerEvent) {
      if (!root.current?.contains(event.target as Node)) setOpen(false)
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  if (!me) return null
  const moderator = me.roles.includes('moderator')
  const item =
    'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-ink/90 transition hover:bg-ink/[0.06] hover:text-ink'

  return (
    <div ref={root} className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={menuId}
        aria-label="Account menu"
        onClick={() => setOpen((value) => !value)}
        className="flex items-center gap-2 rounded-full p-0.5 transition hover:bg-ink/5 sm:rounded-xl sm:py-1 sm:pr-2 sm:pl-1"
      >
        <Avatar name={me.display_name} seed={me.username} />
        <span className="hidden text-left leading-tight sm:block">
          <span className="block max-w-36 truncate text-sm font-medium">{me.display_name}</span>
          <span className="flex items-center gap-1 text-xs text-muted">
            @{me.username}
            {moderator && (
              <span className="inline-flex items-center gap-0.5 text-plasma">
                <ShieldCheck className="size-3" aria-hidden /> mod
              </span>
            )}
          </span>
        </span>
        <ChevronDown
          className={cn('hidden size-4 text-muted transition sm:block', open && 'rotate-180')}
          aria-hidden
        />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            id={menuId}
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 mt-2 w-56 origin-top-right rounded-2xl border border-edge bg-void/95 p-1.5 shadow-glow backdrop-blur-xl"
          >
            <div className="border-b border-edge px-3 pt-1.5 pb-2.5 sm:hidden">
              <p className="truncate text-sm font-medium">{me.display_name}</p>
              <p className="text-xs text-muted">@{me.username}</p>
            </div>
            <ul className="py-1">
              <li>
                <Link to={`/u/${me.username}`} className={item}>
                  <UserRound className="size-4" aria-hidden /> Profile
                </Link>
              </li>
              <li>
                <Link to="/dashboard" className={item}>
                  <LayoutList className="size-4" aria-hidden /> My posts
                </Link>
              </li>
              <li>
                <Link to="/write" className={item}>
                  <PenLine className="size-4" aria-hidden /> New post
                </Link>
              </li>
            </ul>
            <div className="border-t border-edge pt-1">
              <button
                type="button"
                onClick={() => void signOut()}
                className={cn(item, 'hover:text-danger')}
              >
                <LogOut className="size-4" aria-hidden /> Sign out
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function UserMenu() {
  const { me } = useAuth()
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

  return (
    <div className="flex items-center gap-2 sm:gap-3">
      <Link
        to="/write"
        className={cn(
          buttonVariants({ variant: 'primary', size: 'sm' }),
          'max-sm:size-9 max-sm:px-0',
        )}
        aria-label="Write a post"
      >
        <PenLine /> <span className="hidden sm:inline">Write</span>
      </Link>
      <AccountMenu />
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
          <div className="flex items-center gap-1 sm:gap-2">
            <ThemeToggle />
            <UserMenu />
          </div>
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
