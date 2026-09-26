// A single post: cover, metadata, sanitized Markdown body, like button and comment thread.
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Clock, EyeOff, MessageCircle, Pencil } from 'lucide-react'
import { motion } from 'motion/react'
import { Link, useParams } from 'react-router'

import { api, keys } from '@/api/endpoints'
import { ApiError } from '@/api/errors'
import { useAuth } from '@/auth/context'
import { Cover } from '@/components/Cover'
import { Comments } from '@/components/Comments'
import { LikeButton } from '@/components/LikeButton'
import { Markdown } from '@/components/Markdown'
import { ErrorState } from '@/components/States'
import { buttonVariants } from '@/components/ui/button-variants'
import { Avatar, Card, Chip, Skeleton } from '@/components/ui/misc'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { isAuthor } from '@/lib/permissions'
import { formatDate, readingMinutes } from '@/lib/utils'

function PostSkeleton() {
  return (
    <div className="space-y-6" aria-hidden>
      <Skeleton className="h-56 rounded-3xl" />
      <Skeleton className="h-10 w-3/4" />
      <Skeleton className="h-4 w-1/3" />
      <div className="space-y-3 pt-4">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-11/12" />
        <Skeleton className="h-4 w-4/5" />
      </div>
    </div>
  )
}

export function PostPage() {
  const { slug = '' } = useParams()
  const { me } = useAuth()
  const query = useQuery({ queryKey: keys.post(slug), queryFn: () => api.post(slug) })

  if (query.isPending) return <PostSkeleton />
  if (query.isError) {
    if (query.error instanceof ApiError && query.error.status === 404) return <NotFoundPage />
    return <ErrorState error={query.error} onRetry={() => void query.refetch()} />
  }

  const post = query.data
  const date = post.published_at ?? post.created_at
  return (
    <article className="mx-auto max-w-3xl space-y-10">
      <title>{`${post.title} · Nebula`}</title>
      <div className="flex items-center justify-between gap-3">
        <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
          <ArrowLeft className="size-4" aria-hidden /> All posts
        </Link>
        {isAuthor(me, post) && (
          <Link to={`/edit/${post.slug}`} className={buttonVariants({ size: 'sm' })}>
            <Pencil /> Edit
          </Link>
        )}
      </div>

      <motion.header
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-6"
      >
        <div className="h-44 overflow-hidden rounded-3xl border border-edge sm:h-56">
          <Cover seed={post.slug} />
        </div>
        {post.status !== 'published' && (
          <Card className="flex items-center gap-2 border-flare/40 px-4 py-3 text-sm text-flare">
            <EyeOff className="size-4" aria-hidden /> Draft: only you can see this post.
          </Card>
        )}
        {post.tags.length > 0 && (
          <ul className="flex flex-wrap gap-2" aria-label="Tags">
            {post.tags.map((tag) => (
              <li key={tag}>
                <Link to={`/?tag=${encodeURIComponent(tag)}`}>
                  <Chip>#{tag}</Chip>
                </Link>
              </li>
            ))}
          </ul>
        )}
        <h1 className="font-display text-4xl leading-tight font-bold tracking-tight text-balance sm:text-5xl">
          {post.title}
        </h1>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted">
          <Link
            to={`/u/${encodeURIComponent(post.author.username)}`}
            className="flex items-center gap-2 hover:text-ink"
          >
            <Avatar name={post.author.display_name} seed={post.author.username} />
            <span className="font-medium text-ink">{post.author.display_name}</span>
          </Link>
          <time dateTime={date}>{formatDate(date)}</time>
          <span className="flex items-center gap-1">
            <Clock className="size-4" aria-hidden /> {readingMinutes(post.content)} min read
          </span>
        </div>
      </motion.header>

      <Markdown>{post.content}</Markdown>

      <div className="flex flex-wrap items-center justify-between gap-3 border-y border-edge py-4">
        <div className="flex items-center gap-3">
          <LikeButton post={post} />
          <a
            href="#comments-heading"
            className="flex items-center gap-1.5 text-sm text-muted hover:text-ink"
          >
            <MessageCircle className="size-4" aria-hidden /> {post.comment_count}
          </a>
        </div>
        <Link
          to={`/u/${encodeURIComponent(post.author.username)}`}
          className="text-sm text-plasma hover:underline"
        >
          More from {post.author.display_name} →
        </Link>
      </div>

      <Comments post={post} />
    </article>
  )
}
