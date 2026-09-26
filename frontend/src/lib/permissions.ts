// What the signed-in user may do. UI hints only: the API enforces every rule on its own.
import type { Comment, Me, PostSummary } from '@/api/types'

export const COMMENT_DELETE_ANY = 'comment:delete:any'
export const POST_DELETE_ANY = 'post:delete:any'

export function hasPermission(me: Me | null, code: string): boolean {
  return me?.permissions.includes(code) ?? false
}

export function isAuthor(me: Me | null, post: Pick<PostSummary, 'author'>): boolean {
  return me !== null && me.username === post.author.username
}

export function canLike(me: Me | null, post: PostSummary): boolean {
  return post.status === 'published' && !isAuthor(me, post)
}

export function canEditComment(me: Me | null, comment: Comment): boolean {
  return me !== null && !comment.is_deleted && comment.author?.username === me.username
}

export function canDeleteComment(me: Me | null, comment: Comment, post: PostSummary): boolean {
  if (me === null || comment.is_deleted) return false
  return (
    comment.author?.username === me.username ||
    isAuthor(me, post) ||
    hasPermission(me, COMMENT_DELETE_ANY)
  )
}
