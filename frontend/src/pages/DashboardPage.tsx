// The signed-in author's posts: drafts and published, with publish, unpublish and delete.
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ChevronLeft,
  ChevronRight,
  Eye,
  FileText,
  Globe,
  Heart,
  MessageCircle,
  Pencil,
  PenLine,
  Trash2,
  Undo2,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'

import { api, keys } from '@/api/endpoints'
import { describeError } from '@/api/errors'
import type { PostStatus, PostSummary } from '@/api/types'
import { useAuth } from '@/auth/context'
import { EmptyState, ErrorState } from '@/components/States'
import { Button } from '@/components/ui/button'
import { buttonVariants } from '@/components/ui/button-variants'
import { Card, Skeleton } from '@/components/ui/misc'
import { cn, timeAgo } from '@/lib/utils'

const PAGE_SIZE = 10
const TABS: { value: PostStatus | null; label: string }[] = [
  { value: null, label: 'All' },
  { value: 'draft', label: 'Drafts' },
  { value: 'published', label: 'Published' },
]

function PostRow({ post }: { post: PostSummary }) {
  const queryClient = useQueryClient()
  const [confirming, setConfirming] = useState(false)
  const published = post.status === 'published'

  const action = useMutation({
    mutationFn: async (kind: 'toggle' | 'delete') => {
      if (kind === 'delete') await api.deletePost(post.id)
      else if (published) await api.unpublish(post.id)
      else await api.publish(post.id)
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['posts'] })
      void queryClient.invalidateQueries({ queryKey: keys.post(post.slug) })
      void queryClient.invalidateQueries({ queryKey: keys.tags })
      void queryClient.invalidateQueries({ queryKey: ['user'] })
    },
  })

  return (
    <li>
      <Card className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:p-5">
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span
              className={cn(
                'inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium',
                published ? 'bg-plasma/15 text-plasma' : 'bg-flare/15 text-flare',
              )}
            >
              {published ? (
                <Globe className="size-3" aria-hidden />
              ) : (
                <FileText className="size-3" aria-hidden />
              )}
              {published ? 'Published' : 'Draft'}
            </span>
            <span className="text-muted">Updated {timeAgo(post.updated_at)}</span>
          </div>
          <h2 className="truncate font-display text-lg font-semibold">
            <Link to={`/edit/${post.slug}`} className="hover:text-plasma">
              {post.title}
            </Link>
          </h2>
          <p className="flex items-center gap-4 text-sm text-muted">
            <span className="flex items-center gap-1">
              <Heart className="size-4" aria-hidden />
              <span className="sr-only">Likes:</span> {post.like_count}
            </span>
            <span className="flex items-center gap-1">
              <MessageCircle className="size-4" aria-hidden />
              <span className="sr-only">Comments:</span> {post.comment_count}
            </span>
            {post.tags.length > 0 && (
              <span className="truncate">{post.tags.map((tag) => `#${tag}`).join(' ')}</span>
            )}
          </p>
          {action.isError && (
            <p className="text-sm text-danger" role="alert">
              {describeError(action.error)}
            </p>
          )}
        </div>

        {confirming ? (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted">Delete this post?</span>
            <Button size="sm" variant="ghost" onClick={() => setConfirming(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              variant="danger"
              loading={action.isPending}
              onClick={() => action.mutate('delete')}
            >
              Delete
            </Button>
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-1.5">
            <Link to={`/edit/${post.slug}`} className={buttonVariants({ size: 'sm' })}>
              <Pencil /> Edit
            </Link>
            <Link
              to={`/p/${post.slug}`}
              className={buttonVariants({ variant: 'ghost', size: 'sm' })}
              title={published ? 'View' : 'Preview (only you can see drafts)'}
            >
              <Eye /> {published ? 'View' : 'Preview'}
            </Link>
            <Button
              size="sm"
              variant="ghost"
              loading={action.isPending && action.variables === 'toggle'}
              disabled={action.isPending}
              onClick={() => action.mutate('toggle')}
            >
              {published ? <Undo2 /> : <Globe />} {published ? 'Unpublish' : 'Publish'}
            </Button>
            <Button
              size="icon"
              variant="ghost"
              aria-label={`Delete “${post.title}”`}
              title="Delete"
              disabled={action.isPending}
              onClick={() => setConfirming(true)}
              className="hover:text-danger"
            >
              <Trash2 />
            </Button>
          </div>
        )}
      </Card>
    </li>
  )
}

export function DashboardPage() {
  const { me } = useAuth()
  const [params, setParams] = useSearchParams()
  const status = TABS.find((tab) => tab.value === params.get('status'))?.value ?? null
  const page = Math.max(1, Number(params.get('page')) || 1)
  const filters = {
    ...(status && { status }),
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  }
  const posts = useQuery({
    queryKey: keys.myPosts(filters),
    queryFn: () => api.myPosts(filters),
    placeholderData: keepPreviousData,
  })
  const totalPages = posts.data ? Math.max(1, Math.ceil(posts.data.total / PAGE_SIZE)) : 1

  function go(next: { status?: PostStatus | null; page?: number }) {
    const search = new URLSearchParams()
    const nextStatus = next.status === undefined ? status : next.status
    if (nextStatus) search.set('status', nextStatus)
    if (next.page && next.page > 1) search.set('page', String(next.page))
    setParams(search)
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <title>My posts · Nebula</title>
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">My posts</h1>
          <p className="text-muted">
            Drafts are private until you publish them.{' '}
            {me && (
              <Link to={`/u/${me.username}`} className="text-plasma hover:underline">
                View your public profile →
              </Link>
            )}
          </p>
        </div>
        <Link to="/write" className={buttonVariants({ variant: 'primary' })}>
          <PenLine /> New post
        </Link>
      </header>

      <nav className="flex w-fit gap-1 rounded-xl p-1 glass" aria-label="Filter by status">
        {TABS.map((tab) => (
          <button
            key={tab.label}
            type="button"
            aria-pressed={status === tab.value}
            onClick={() => go({ status: tab.value })}
            className={cn(
              'rounded-lg px-4 py-1.5 text-sm transition',
              status === tab.value ? 'bg-ink/10 text-ink' : 'text-muted hover:text-ink',
            )}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <section aria-live="polite" aria-busy={posts.isFetching}>
        {posts.isPending ? (
          <ul className="space-y-3" aria-hidden>
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-28 rounded-2xl" />
            ))}
          </ul>
        ) : posts.isError ? (
          <ErrorState error={posts.error} onRetry={() => void posts.refetch()} />
        ) : posts.data.items.length === 0 ? (
          <EmptyState title={status ? `No ${status} posts` : 'No posts yet'}>
            <p className="mb-6">Every nebula starts with a single spark.</p>
            <Link to="/write" className={buttonVariants({ variant: 'primary' })}>
              <PenLine /> Write your first post
            </Link>
          </EmptyState>
        ) : (
          <ul className={cn('space-y-3', posts.isPlaceholderData && 'opacity-60')}>
            {posts.data.items.map((post) => (
              <PostRow key={post.id} post={post} />
            ))}
          </ul>
        )}
      </section>

      {posts.data && totalPages > 1 && (
        <nav className="flex items-center justify-center gap-3" aria-label="Pagination">
          <Button size="sm" disabled={page <= 1} onClick={() => go({ page: page - 1 })}>
            <ChevronLeft /> Previous
          </Button>
          <span className="text-sm text-muted">
            Page {page} of {totalPages}
          </span>
          <Button size="sm" disabled={page >= totalPages} onClick={() => go({ page: page + 1 })}>
            Next <ChevronRight />
          </Button>
        </nav>
      )}
    </div>
  )
}
