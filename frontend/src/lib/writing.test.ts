// Writing-check helpers: context snippets and applying suggestions without breaking offsets.
import { describe, expect, it } from 'vitest'

import type { WritingIssue } from '@/api/types'

import { applySuggestion, issueContext } from './writing'

const issue = (offset: number, length: number): WritingIssue => ({
  offset,
  length,
  message: 'Possible problem',
  category: 'spelling',
  suggestions: [],
})

describe('issueContext', () => {
  it('shows the match with the rest of its line', () => {
    const text = '# Title\nTeh cat sat.\nNext line'
    expect(issueContext(text, issue(8, 3))).toEqual({
      before: '',
      match: 'Teh',
      after: ' cat sat.',
    })
  })

  it('marks context cut short with an ellipsis', () => {
    const text = `${'a'.repeat(60)} Teh ${'b'.repeat(60)}`
    const { before, match, after } = issueContext(text, issue(61, 3))
    expect(before.startsWith('…')).toBe(true)
    expect(after.endsWith('…')).toBe(true)
    expect(match).toBe('Teh')
  })
})

describe('applySuggestion', () => {
  it('replaces the text and shifts later issues', () => {
    const text = 'Teh cat and teh dog'
    const first = issue(0, 3)
    const later = issue(12, 3)

    const result = applySuggestion(text, [first, later], first, 'The')
    expect(result.text).toBe('The cat and teh dog')
    expect(result.issues).toEqual([later])

    const longer = applySuggestion(text, [first, later], first, 'Theee')
    expect(longer.issues[0]?.offset).toBe(14)
    expect(longer.text.slice(14, 17)).toBe('teh')
  })

  it('keeps earlier issues and drops overlapping ones', () => {
    const text = 'one two three'
    const earlier = issue(0, 3)
    const target = issue(4, 3)
    const overlapping = issue(6, 3)

    const result = applySuggestion(text, [earlier, target, overlapping], target, '2')
    expect(result.text).toBe('one 2 three')
    expect(result.issues).toEqual([earlier])
  })

  it('works with emoji, whose length is two UTF-16 units', () => {
    const text = '🚀 Teh launch'
    const target = issue(3, 3) // the API counts UTF-16 units, like String.length
    expect(applySuggestion(text, [target], target, 'The').text).toBe('🚀 The launch')
  })
})
