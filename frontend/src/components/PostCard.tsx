// A post in the feed: generated cover art, title, excerpt, author and engagement counts.
import { Heart, MessageCircle } from 'lucide-react'
import { motion } from 'motion/react'
import { Link } from 'react-router'

import type { PostSummary } from '@/api/types'
import { Cover } from '@/components/Cover'
import { Avatar } from '@/components/ui/misc'
import { cn, formatDate, plainText } from '@/lib/utils'

export function PostCard({ post, index = 0 }: { post: PostSummary; index?: number }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: Math.min(index, 8) * 0.05, ease: 'easeOut' }}
      className="group relative flex flex-col overflow-hidden rounded-2xl glass transition duration-300 hover:-translate-y-1 hover:border-nova/40 hover:shadow-glow"
    >
      <div className="relative h-32 overflow-hidden border-b border-edge">
        <Cover seed={post.slug} className="transition duration-700 group-hover:scale-105" />
        {post.tags.length > 0 && (
          <ul className="absolute bottom-3 left-4 flex flex-wrap gap-1.5">
            {post.tags.slice(0, 3).map((tag) => (
              <li
                key={tag}
                className="rounded-full bg-void/70 px-2 py-0.5 text-xs text-ink backdrop-blur"
              >
                #{tag}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-3 p-5">
        <h2 className="font-display text-lg leading-snug font-semibold text-balance">
          {/* The stretched link makes the whole card clickable while keeping one focusable link. */}
          <Link
            to={`/p/${post.slug}`}
            className="after:absolute after:inset-0 focus-visible:outline-none"
          >
            {post.title}
          </Link>
        </h2>
        <p className="line-clamp-3 text-sm leading-relaxed text-muted">{plainText(post.excerpt)}</p>
        <footer className="mt-auto flex items-center justify-between gap-3 pt-2 text-sm">
          <span className="flex min-w-0 items-center gap-2">
            <Avatar
              name={post.author.display_name}
              seed={post.author.username}
              className="size-7"
            />
            <span className="min-w-0">
              <span className="block truncate text-ink/90">{post.author.display_name}</span>
              {post.published_at && (
                <time dateTime={post.published_at} className="block text-xs text-muted">
                  {formatDate(post.published_at)}
                </time>
              )}
            </span>
          </span>
          <span className="flex shrink-0 items-center gap-3 text-muted">
            <span className="flex items-center gap-1" title={`${post.like_count} likes`}>
              <Heart
                className={cn('size-4', post.liked_by_me && 'fill-flare text-flare')}
                aria-hidden
              />
              <span className="sr-only">Likes:</span>
              {post.like_count}
            </span>
            <span className="flex items-center gap-1" title={`${post.comment_count} comments`}>
              <MessageCircle className="size-4" aria-hidden />
              <span className="sr-only">Comments:</span>
              {post.comment_count}
            </span>
          </span>
        </footer>
      </div>
    </motion.article>
  )
}
