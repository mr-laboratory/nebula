// Helper tests: open-redirect guard, relative times, reading time and initials.
import { describe, expect, it } from 'vitest'

import { initials, readingMinutes, safeNext, timeAgo } from './utils'

describe('safeNext', () => {
  it.each(['/', '/p/hello', '/?tag=python'])('keeps same-site path %s', (path) => {
    expect(safeNext(path)).toBe(path)
  })

  it.each([
    null,
    '',
    'https://evil.example',
    '//evil.example',
    '/\\evil.example',
    'javascript:alert(1)',
  ])('rejects %s', (value) => {
    expect(safeNext(value)).toBe('/')
  })
})

describe('timeAgo', () => {
  const now = Date.parse('2026-09-26T12:00:00Z')

  it.each([
    ['2026-09-26T11:59:40Z', 'just now'],
    ['2026-09-26T11:55:00Z', '5 minutes ago'],
    ['2026-09-26T09:00:00Z', '3 hours ago'],
    ['2026-09-25T12:00:00Z', 'yesterday'],
    ['2025-09-26T12:00:00Z', 'last year'],
  ])('%s → %s', (iso, expected) => {
    expect(timeAgo(iso, now)).toBe(expected)
  })
})

describe('readingMinutes', () => {
  it('is at least one minute', () => {
    expect(readingMinutes('short')).toBe(1)
  })

  it('assumes about 220 words a minute', () => {
    expect(readingMinutes(Array(660).fill('word').join(' '))).toBe(3)
  })
})

describe('initials', () => {
  it.each([
    ['Ada Lovelace', 'AL'],
    ['grace', 'G'],
    ['  ', '?'],
  ])('%s → %s', (name, expected) => {
    expect(initials(name)).toBe(expected)
  })
})
