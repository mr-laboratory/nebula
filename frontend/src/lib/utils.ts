// Small shared helpers: class merging, dates, safe redirects and per-post gradients.
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

const relative = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 31_536_000],
  ['month', 2_592_000],
  ['week', 604_800],
  ['day', 86_400],
  ['hour', 3_600],
  ['minute', 60],
]

export function timeAgo(iso: string, now: number = Date.now()): string {
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000)
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) return relative.format(Math.round(seconds / size), unit)
  }
  return 'just now'
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function readingMinutes(text: string): number {
  return Math.max(1, Math.round(text.trim().split(/\s+/).length / 220))
}

/**
 * Where to go after signing in. Only same-site paths are allowed: `?next=https://evil.example`
 * or `//evil.example` would otherwise turn the login page into an open redirect.
 */
export function safeNext(next: string | null | undefined): string {
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.includes('\\')) return '/'
  return next
}

/** A stable two-colour gradient derived from a string, used as a post's cover art. */
export function gradientFor(seed: string): string {
  let hash = 0
  for (const char of seed) hash = (hash * 31 + char.charCodeAt(0)) | 0
  const hue = Math.abs(hash) % 360
  const second = (hue + 50 + (Math.abs(hash >> 8) % 80)) % 360
  return `radial-gradient(120% 140% at 10% 0%, hsl(${hue} 90% 62% / 0.85), transparent 55%),
    radial-gradient(120% 140% at 100% 100%, hsl(${second} 90% 58% / 0.75), transparent 60%),
    linear-gradient(135deg, hsl(${hue} 60% 14%), hsl(${second} 60% 10%))`
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).slice(0, 2)
  return parts.map((part) => part[0]?.toUpperCase() ?? '').join('') || '?'
}
