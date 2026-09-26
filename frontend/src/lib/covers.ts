// Deterministic cover and avatar choices: the same slug or username always gets the same art.
import { pick } from '@/lib/utils'

export const ACCENTS = ['nova', 'plasma', 'flare'] as const
export type Accent = (typeof ACCENTS)[number]

export const PATTERNS = ['orbits', 'waves', 'constellation', 'grid', 'blobs'] as const
export type Pattern = (typeof PATTERNS)[number]

export function hashString(text: string): number {
  let hash = 2166136261 // FNV-1a: cheap, and small input changes spread across all bits
  for (const char of text) {
    hash ^= char.codePointAt(0) ?? 0
    hash = Math.imul(hash, 16777619)
  }
  return hash >>> 0
}

/** A seeded random generator (mulberry32), so generated shapes are stable between renders. */
export function seededRandom(seed: number): () => number {
  let state = seed
  return () => {
    state = (state + 0x6d2b79f5) | 0
    let t = Math.imul(state ^ (state >>> 15), 1 | state)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** Two different theme accents for `seed`: the main one and a companion. */
export function accentPair(seed: string): [Accent, Accent] {
  const hash = hashString(seed)
  const first = hash % ACCENTS.length
  const second = (first + 1 + ((hash >>> 4) % (ACCENTS.length - 1))) % ACCENTS.length
  return [pick(ACCENTS, first), pick(ACCENTS, second)]
}

export function patternFor(seed: string): Pattern {
  return pick(PATTERNS, hashString(seed) >>> 8)
}

/** Mix a theme accent with the page background, so art stays muted in both modes. */
export function tone(accent: Accent, percent: number): string {
  return `color-mix(in oklab, var(--nb-${accent}) ${percent}%, var(--nb-void))`
}

export function avatarBackground(seed: string): string {
  const [a, b] = accentPair(seed)
  return `linear-gradient(135deg, ${tone(a, 85)}, ${tone(b, 65)})`
}
