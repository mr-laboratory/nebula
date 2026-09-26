// Editor draft rules: what the form starts from, what changed, and what the API would reject.
import type { PostDetail, PostUpdate } from '@/api/types'

import { MAX_TAGS } from './tags'

export type Draft = { title: string; excerpt: string; tags: string[]; content: string }
export type DraftErrors = Partial<Record<keyof Draft, string>>

export const LIMITS = { title: 200, excerpt: 300, content: 100_000 } as const
export const EMPTY_DRAFT: Draft = { title: '', excerpt: '', tags: [], content: '' }

/**
 * The form's starting point for a saved post. The API fills `excerpt` from the content when the
 * author didn't write one; showing that as the author's own would save it as a custom excerpt.
 */
export function draftFrom(post: PostDetail): Draft {
  const generated = post.content.startsWith(post.excerpt)
  return {
    title: post.title,
    excerpt: generated ? '' : post.excerpt,
    tags: post.tags,
    content: post.content,
  }
}

const sameTags = (a: string[], b: string[]) =>
  a.length === b.length && [...a].sort().join() === [...b].sort().join()

/** Only the fields that differ from the saved version: PATCH sends nothing else. */
export function changedFields(saved: Draft, draft: Draft): PostUpdate {
  const changes: PostUpdate = {}
  // The API trims title and excerpt, so compare the way it will store them.
  if (draft.title.trim() !== saved.title) changes.title = draft.title.trim()
  if (draft.excerpt.trim() !== saved.excerpt) changes.excerpt = draft.excerpt.trim() || null
  if (draft.content !== saved.content) changes.content = draft.content
  if (!sameTags(draft.tags, saved.tags)) changes.tags = draft.tags
  return changes
}

export function isDirty(saved: Draft, draft: Draft): boolean {
  return Object.keys(changedFields(saved, draft)).length > 0
}

/** The API's rules, checked before sending so mistakes show instantly. The API still decides. */
export function validate(draft: Draft): DraftErrors {
  const errors: DraftErrors = {}
  if (!draft.title.trim()) errors.title = 'Give your post a title.'
  else if (draft.title.trim().length > LIMITS.title)
    errors.title = `At most ${LIMITS.title} characters.`
  if (draft.excerpt.trim().length > LIMITS.excerpt)
    errors.excerpt = `At most ${LIMITS.excerpt} characters.`
  if (!draft.content.trim()) errors.content = 'Write something first.'
  else if (draft.content.length > LIMITS.content) errors.content = 'This post is too long.'
  if (draft.tags.length > MAX_TAGS) errors.tags = `At most ${MAX_TAGS} tags.`
  return errors
}
