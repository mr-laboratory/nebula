// Permission hint tests: who sees like, edit and delete controls.
import { describe, expect, it } from 'vitest'

import type { Comment, Me, PostSummary } from '@/api/types'

import { canDeleteComment, canEditComment, canLike, COMMENT_DELETE_ANY } from './permissions'

const user = (username: string, permissions: string[] = []): Me =>
  ({ username, display_name: username, permissions, roles: [] }) as unknown as Me

const post = (author: string, status: PostSummary['status'] = 'published'): PostSummary =>
  ({ author: { username: author, display_name: author }, status }) as PostSummary

const comment = (author: string | null, is_deleted = false): Comment =>
  ({
    author: author ? { username: author, display_name: author } : null,
    body: is_deleted ? null : 'hi',
    is_deleted,
  }) as Comment

describe('canLike', () => {
  it('allows published posts by others', () => {
    expect(canLike(user('ada'), post('grace'))).toBe(true)
  })

  it('refuses own posts and drafts', () => {
    expect(canLike(user('ada'), post('ada'))).toBe(false)
    expect(canLike(user('ada'), post('grace', 'draft'))).toBe(false)
  })
})

describe('comment controls', () => {
  it('lets only the comment author edit', () => {
    expect(canEditComment(user('ada'), comment('ada'))).toBe(true)
    expect(canEditComment(user('grace'), comment('ada'))).toBe(false)
    expect(canEditComment(null, comment('ada'))).toBe(false)
  })

  it('lets the comment author, post author or a moderator delete', () => {
    const thread = post('grace')
    expect(canDeleteComment(user('ada'), comment('ada'), thread)).toBe(true)
    expect(canDeleteComment(user('grace'), comment('ada'), thread)).toBe(true)
    expect(canDeleteComment(user('mod', [COMMENT_DELETE_ANY]), comment('ada'), thread)).toBe(true)
    expect(canDeleteComment(user('eve'), comment('ada'), thread)).toBe(false)
  })

  it('offers nothing on deleted placeholders', () => {
    const gone = comment(null, true)
    expect(canEditComment(user('ada'), gone)).toBe(false)
    expect(canDeleteComment(user('mod', [COMMENT_DELETE_ANY]), gone, post('grace'))).toBe(false)
  })
})
