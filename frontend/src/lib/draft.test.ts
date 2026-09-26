// Draft rule tests: generated excerpts, minimal PATCH bodies and client-side validation.
import { describe, expect, it } from 'vitest'

import type { PostDetail } from '@/api/types'

import { changedFields, draftFrom, isDirty, validate, type Draft } from './draft'

const post = (overrides: Partial<PostDetail> = {}): PostDetail =>
  ({
    title: 'Hello',
    content: 'The quick brown fox jumps over the lazy dog.',
    excerpt: 'The quick brown fox',
    tags: ['a', 'b'],
    ...overrides,
  }) as PostDetail

const saved: Draft = { title: 'Hello', excerpt: '', tags: ['a', 'b'], content: 'Body' }

describe('draftFrom', () => {
  it('treats an excerpt generated from the content as no excerpt', () => {
    expect(draftFrom(post()).excerpt).toBe('')
  })

  it('keeps an excerpt the author wrote', () => {
    expect(draftFrom(post({ excerpt: 'A short story' })).excerpt).toBe('A short story')
  })
})

describe('changedFields', () => {
  it('is empty when nothing changed, even with reordered tags or padded title', () => {
    expect(changedFields(saved, { ...saved, title: '  Hello ', tags: ['b', 'a'] })).toEqual({})
    expect(isDirty(saved, saved)).toBe(false)
  })

  it('sends only what changed', () => {
    expect(changedFields(saved, { ...saved, content: 'New body' })).toEqual({ content: 'New body' })
  })

  it('clears the excerpt with null', () => {
    expect(changedFields({ ...saved, excerpt: 'Old' }, saved)).toEqual({ excerpt: null })
  })
})

describe('validate', () => {
  it('requires a title and content', () => {
    expect(validate({ ...saved, title: ' ', content: '\n' })).toEqual({
      title: 'Give your post a title.',
      content: 'Write something first.',
    })
  })

  it('accepts a valid draft', () => {
    expect(validate(saved)).toEqual({})
  })

  it('enforces length limits', () => {
    expect(validate({ ...saved, excerpt: 'x'.repeat(301) }).excerpt).toMatch(/300/)
  })
})
