// Like toggle with an optimistic update: the heart changes at once and rolls back on failure.
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Heart } from 'lucide-react'
import { motion } from 'motion/react'
import { useNavigate } from 'react-router'

import { api, keys } from '@/api/endpoints'
import { describeError } from '@/api/errors'
import type { PostDetail } from '@/api/types'
import { useAuth } from '@/auth/context'
import { canLike } from '@/lib/permissions'
import { cn } from '@/lib/utils'

export function LikeButton({ post }: { post: PostDetail }) {
  const { me } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const key = keys.post(post.slug)

  const mutation = useMutation({
    mutationFn: (like: boolean) => (like ? api.like(post.id) : api.unlike(post.id)),
    onMutate: async (like) => {
      await queryClient.cancelQueries({ queryKey: key })
      const previous = queryClient.getQueryData<PostDetail>(key)
      queryClient.setQueryData<PostDetail>(
        key,
        (current) =>
          current && {
            ...current,
            liked_by_me: like,
            like_count: Math.max(0, current.like_count + (like ? 1 : -1)),
          },
      )
      return { previous }
    },
    onError: (_error, _like, context) => queryClient.setQueryData(key, context?.previous),
    onSuccess: (status) =>
      queryClient.setQueryData<PostDetail>(key, (current) => current && { ...current, ...status }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['posts'] }),
  })

  const allowed = canLike(me, post)
  const liked = post.liked_by_me === true
  const label = !me
    ? 'Sign in to like this post'
    : !allowed
      ? post.status === 'published'
        ? "You can't like your own post"
        : 'Publish the post to receive likes'
      : liked
        ? 'Unlike'
        : 'Like'

  function onClick() {
    if (!me) {
      void navigate(`/login?next=${encodeURIComponent(`/p/${post.slug}`)}`)
      return
    }
    mutation.mutate(!liked)
  }

  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        onClick={onClick}
        disabled={me !== null && !allowed}
        aria-pressed={me ? liked : undefined}
        aria-label={label}
        title={label}
        className={cn(
          'group inline-flex h-11 items-center gap-2 rounded-full px-4 glass transition disabled:cursor-not-allowed disabled:opacity-60',
          liked
            ? 'border-flare/50 text-flare shadow-[0_0_24px_-6px_var(--color-flare)]'
            : 'hover:border-flare/40',
        )}
      >
        <motion.span
          key={String(liked)}
          initial={{ scale: 0.6 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 500, damping: 15 }}
        >
          <Heart
            className={cn('size-5', liked ? 'fill-flare' : 'group-hover:text-flare')}
            aria-hidden
          />
        </motion.span>
        <span className="font-medium tabular-nums">{post.like_count}</span>
      </button>
      {mutation.isError && (
        <p className="text-sm text-danger" role="alert">
          {describeError(mutation.error)}
        </p>
      )}
    </div>
  )
}
