// Comment thread: flat list (oldest first), "show more", and create / edit / delete in place.
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { MessageCircle, Pencil, Trash2 } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation } from 'react-router'

import { api, keys } from '@/api/endpoints'
import { describeError } from '@/api/errors'
import type { Comment, PostDetail } from '@/api/types'
import { useAuth } from '@/auth/context'
import { ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { buttonVariants } from '@/components/ui/button-variants'
import { TextArea } from '@/components/ui/field'
import { Avatar, Card, Skeleton } from '@/components/ui/misc'
import { canDeleteComment, canEditComment } from '@/lib/permissions'
import { timeAgo } from '@/lib/utils'

const MAX_LENGTH = 5000
const PAGE = 20

function useRefreshThread(post: PostDetail) {
  const queryClient = useQueryClient()
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: keys.comments(post.id) }),
      queryClient.invalidateQueries({ queryKey: keys.post(post.slug) }), // comment_count
      queryClient.invalidateQueries({ queryKey: ['posts'] }),
    ])
}

function CommentForm({
  initial = '',
  submitLabel,
  onSubmit,
  onCancel,
  focusOnMount = false,
}: {
  initial?: string
  submitLabel: string
  onSubmit: (body: string) => Promise<unknown>
  onCancel?: () => void
  focusOnMount?: boolean
}) {
  const id = useId()
  const input = useRef<HTMLTextAreaElement>(null)
  const [body, setBody] = useState(initial)
  const mutation = useMutation({ mutationFn: onSubmit })
  const trimmed = body.trim()

  // Opened by an explicit "Edit" click, so moving focus into the box is expected here.
  useEffect(() => {
    if (focusOnMount) input.current?.focus()
  }, [focusOnMount])

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!trimmed) return
    mutation.mutate(trimmed, { onSuccess: () => !onCancel && setBody('') })
  }

  return (
    <form onSubmit={submit} className="space-y-2">
      <label className="sr-only" htmlFor={id}>
        Comment
      </label>
      <TextArea
        id={id}
        ref={input}
        value={body}
        maxLength={MAX_LENGTH}
        onChange={(event) => setBody(event.target.value)}
        placeholder="Share your thoughts…"
      />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs text-muted tabular-nums">
          {body.length.toLocaleString()} / {MAX_LENGTH.toLocaleString()}
        </span>
        <div className="flex gap-2">
          {onCancel && (
            <Button variant="ghost" size="sm" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button
            type="submit"
            variant="primary"
            size="sm"
            loading={mutation.isPending}
            disabled={!trimmed}
          >
            {submitLabel}
          </Button>
        </div>
      </div>
      {mutation.isError && (
        <p className="text-sm text-danger" role="alert">
          {describeError(mutation.error)}
        </p>
      )}
    </form>
  )
}

function CommentItem({ comment, post }: { comment: Comment; post: PostDetail }) {
  const { me } = useAuth()
  const refreshThread = useRefreshThread(post)
  const [mode, setMode] = useState<'view' | 'edit' | 'confirm-delete'>('view')
  const remove = useMutation({
    mutationFn: () => api.deleteComment(comment.id),
    onSuccess: refreshThread,
  })

  if (comment.is_deleted || !comment.author || comment.body === null) {
    return (
      <li className="rounded-xl border border-dashed border-edge px-4 py-3 text-sm text-muted italic">
        This comment was deleted.
      </li>
    )
  }

  const author = comment.author
  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl p-4 glass"
    >
      <div className="flex items-start gap-3">
        <Avatar name={author.display_name} seed={author.username} />
        <div className="min-w-0 flex-1 space-y-2">
          <p className="flex flex-wrap items-baseline gap-x-2 text-sm">
            <span className="font-medium">{author.display_name}</span>
            <span className="text-muted">@{author.username}</span>
            {author.username === post.author.username && (
              <span className="rounded-full bg-nova/15 px-1.5 text-xs text-nova">author</span>
            )}
            <time dateTime={comment.created_at} className="text-xs text-muted">
              {timeAgo(comment.created_at)}
            </time>
            {comment.edited && <span className="text-xs text-muted">(edited)</span>}
          </p>
          {mode === 'edit' ? (
            <CommentForm
              initial={comment.body}
              submitLabel="Save"
              focusOnMount
              onCancel={() => setMode('view')}
              onSubmit={async (body) => {
                await api.editComment(comment.id, body)
                await refreshThread()
                setMode('view')
              }}
            />
          ) : (
            // Plain text: React escapes it, and nothing here is ever parsed as HTML or Markdown.
            <p className="text-[0.95rem] leading-relaxed break-words whitespace-pre-wrap text-ink/90">
              {comment.body}
            </p>
          )}
          {mode === 'confirm-delete' ? (
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-muted">Delete this comment?</span>
              <Button
                variant="danger"
                size="sm"
                loading={remove.isPending}
                onClick={() => remove.mutate()}
              >
                Delete
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setMode('view')}>
                Keep
              </Button>
            </div>
          ) : (
            mode === 'view' && (
              <div className="flex gap-1">
                {canEditComment(me, comment) && (
                  <Button variant="ghost" size="sm" onClick={() => setMode('edit')}>
                    <Pencil /> Edit
                  </Button>
                )}
                {canDeleteComment(me, comment, post) && (
                  <Button variant="ghost" size="sm" onClick={() => setMode('confirm-delete')}>
                    <Trash2 /> Delete
                  </Button>
                )}
              </div>
            )
          )}
          {remove.isError && (
            <p className="text-sm text-danger" role="alert">
              {describeError(remove.error)}
            </p>
          )}
        </div>
      </div>
    </motion.li>
  )
}

export function Comments({ post }: { post: PostDetail }) {
  const { me } = useAuth()
  const location = useLocation()
  const refreshThread = useRefreshThread(post)
  const thread = useInfiniteQuery({
    queryKey: keys.comments(post.id),
    queryFn: ({ pageParam }) => api.comments(post.id, pageParam, PAGE),
    initialPageParam: 0,
    getNextPageParam: (last) => {
      const next = last.offset + last.items.length
      return next < last.total ? next : undefined
    },
  })
  const comments = thread.data?.pages.flatMap((page) => page.items) ?? []
  const published = post.status === 'published'

  return (
    <section className="space-y-6" aria-labelledby="comments-heading">
      <h2
        id="comments-heading"
        className="flex items-center gap-2 font-display text-2xl font-semibold"
      >
        <MessageCircle className="size-6 text-plasma" aria-hidden /> Comments
        <span className="text-base font-normal text-muted">{post.comment_count}</span>
      </h2>

      {!published ? (
        <Card className="p-5 text-sm text-muted">Comments open once this post is published.</Card>
      ) : me ? (
        <Card className="p-4">
          <CommentForm
            submitLabel="Comment"
            onSubmit={async (body) => {
              await api.addComment(post.id, body)
              await refreshThread()
            }}
          />
        </Card>
      ) : (
        <Card className="flex flex-col items-center justify-between gap-3 p-5 text-sm sm:flex-row">
          <p className="text-muted">Sign in to join the conversation.</p>
          <Link
            to={`/login?next=${encodeURIComponent(location.pathname)}`}
            className={buttonVariants({ variant: 'primary', size: 'sm' })}
          >
            Sign in to comment
          </Link>
        </Card>
      )}

      {thread.isPending ? (
        <div className="space-y-3" aria-hidden>
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      ) : thread.isError ? (
        <ErrorState error={thread.error} onRetry={() => void thread.refetch()} />
      ) : comments.length === 0 ? (
        published && <p className="text-center text-muted">No comments yet. Be the first!</p>
      ) : (
        <ul className="space-y-3">
          <AnimatePresence initial={false}>
            {comments.map((comment) => (
              <CommentItem key={comment.id} comment={comment} post={post} />
            ))}
          </AnimatePresence>
        </ul>
      )}

      {thread.hasNextPage && (
        <div className="text-center">
          <Button loading={thread.isFetchingNextPage} onClick={() => void thread.fetchNextPage()}>
            Show more comments
          </Button>
        </div>
      )}
    </section>
  )
}
