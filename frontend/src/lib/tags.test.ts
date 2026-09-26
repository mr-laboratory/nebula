// Tag normalisation tests: what the editor accepts before the API sees it.
import { describe, expect, it } from 'vitest'

import { normalizeTag } from './tags'

describe('normalizeTag', () => {
  it.each([
    ['Python', 'python'],
    ['  Machine   Learning ', 'machine-learning'],
    ['#fastapi', 'fastapi'],
    ['web-3', 'web-3'],
  ])('%s → %s', (raw, expected) => {
    expect(normalizeTag(raw)).toBe(expected)
  })

  it.each(['', 'c++', 'naïve', 'a'.repeat(41), '<b>'])('rejects %s', (raw) => {
    expect(normalizeTag(raw)).toBeNull()
  })
})
