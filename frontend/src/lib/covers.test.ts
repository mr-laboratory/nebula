// Cover helper tests: stable hashing and seeding, and accent pairs that never repeat a color.
import { describe, expect, it } from 'vitest'

import { ACCENTS, accentPair, hashString, patternFor, PATTERNS, seededRandom } from './covers'

describe('covers', () => {
  it('hashes deterministically', () => {
    expect(hashString('hello-world')).toBe(hashString('hello-world'))
    expect(hashString('hello-world')).not.toBe(hashString('hello-worle'))
  })

  it('repeats the same random sequence for the same seed', () => {
    const a = seededRandom(42)
    const b = seededRandom(42)
    const values = [a(), a(), a()]
    expect([b(), b(), b()]).toEqual(values)
    for (const value of values) expect(value).toBeGreaterThanOrEqual(0)
    for (const value of values) expect(value).toBeLessThan(1)
  })

  it.each(['a', 'post-1', 'another-slug', 'z', 'getting-started'])(
    'pairs two accents for %s',
    (seed) => {
      const [first, second] = accentPair(seed)
      expect(ACCENTS).toContain(first)
      expect(ACCENTS).toContain(second)
      expect(first).not.toBe(second)
      expect(PATTERNS).toContain(patternFor(seed))
    },
  )

  it('uses every pattern across many slugs', () => {
    const seen = new Set(Array.from({ length: 200 }, (_, i) => patternFor(`post-${i}`)))
    expect(seen.size).toBe(PATTERNS.length)
  })
})
