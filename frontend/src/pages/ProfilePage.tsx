// Public author profile: bio, stats and published posts; the owner can edit name and bio inline.
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { CalendarDays, ChevronLeft, ChevronRight, FileText, Pencil } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useParams, useSearchParams } from 'react-router'

import { api, keys } from '@/api/endpoints'
import { ApiError, describeError } from '@/api/errors'
import type { Profile } from '@/api/types'
import { useAuth } from '@/auth/context'
import { PostCard } from '@/components/PostCard'
import { EmptyState, ErrorState, PostCardSkeleton } from '@/components/States'
import { Button } from '@/components/ui/button'
import { TextAreaField, TextField } from '@/components/ui/field'
import { Avatar, Card, Skeleton } from '@/components/ui/misc'
import { cn, formatDate } from '@/lib/utils'
import { NotFoundPage } from '@/pages/NotFoundPage'

const PAGE_SIZE = 9
const BIO_MAX = 280
const NAME_MAX = 60

function EditProfile({ profile, onDone }: { profile: Profile; onDone: () => void }) {
  const { updateProfile } = useAuth()
  const [name, setName] = useState(profile.display_name)
  const [bio, setBio] = useState(profile.bio ?? '')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [pending, setPending] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!name.trim()) {
      setErrors({ display_name: 'Your name can’t be empty.' })
      return
    }
    setPending(true)
    setErrors({})
    try {
      await updateProfile({ display_name: name.trim(), bio: bio.trim() || null })
      onDone()
    } catch (error) {
      const fields = error instanceof ApiError ? error.fieldMessages() : {}
      setErrors(Object.keys(fields).length > 0 ? fields : { form: describeError(error) })
    } finally {
      setPending(false)
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="w-full space-y-4" noValidate>
      <TextField
        label="Display name"
        value={name}
        maxLength={NAME_MAX}
        onChange={(event) => setName(event.target.value)}
        error={errors.display_name}
        autoComplete="name"
      />
      <TextAreaField
        label="Bio"
        value={bio}
        maxLength={BIO_MAX}
        rows={3}
        onChange={(event) => setBio(event.target.value)}
        error={errors.bio}
        hint={`${bio.length}/${BIO_MAX}`}
        placeholder="A line or two about you"
      />
      {errors.form && (
        <p className="text-sm text-danger" role="alert">
          {errors.form}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onDone} disabled={pending}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={pending}>
          Save profile
        </Button>
      </div>
    </form>
  )
}

function ProfileHeader({ profile }: { profile: Profile }) {
  const { me } = useAuth()
  const [editing, setEditing] = useState(false)
  const own = me?.username === profile.username

  return (
    <Card className="relative overflow-hidden p-6 sm:p-8">
      <div
        aria-hidden
        className="absolute inset-x-0 top-0 h-24 opacity-60"
        style={{
          background:
            'radial-gradient(circle at 20% 0%, color-mix(in oklab, var(--nb-nova) 45%, transparent), transparent 60%)',
        }}
      />
      <div className="relative flex flex-col gap-6 sm:flex-row sm:items-start">
        <Avatar
          name={profile.display_name}
          seed={profile.username}
          className="size-20 text-2xl shadow-glow"
        />
        {editing ? (
          <EditProfile profile={profile} onDone={() => setEditing(false)} />
        ) : (
          <div className="min-w-0 flex-1 space-y-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h1 className="font-display text-3xl font-bold tracking-tight break-words">
                  {profile.display_name}
                </h1>
                <p className="text-muted">@{profile.username}</p>
              </div>
              {own && (
                <Button size="sm" onClick={() => setEditing(true)}>
                  <Pencil /> Edit profile
                </Button>
              )}
            </div>
            {profile.bio ? (
              <p className="max-w-2xl text-pretty whitespace-pre-line text-ink/90">{profile.bio}</p>
            ) : (
              own && <p className="text-muted italic">Add a bio so readers know who you are.</p>
            )}
            <p className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-muted">
              <span className="flex items-center gap-1.5">
                <FileText className="size-4" aria-hidden />
                {profile.post_count} {profile.post_count === 1 ? 'post' : 'posts'}
              </span>
              <span className="flex items-center gap-1.5">
                <CalendarDays className="size-4" aria-hidden /> Joined{' '}
                {formatDate(profile.created_at)}
              </span>
            </p>
          </div>
        )}
      </div>
    </Card>
  )
}

export function ProfilePage() {
  const { username = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const page = Math.max(1, Number(params.get('page')) || 1)
  const profile = useQuery({ queryKey: keys.user(username), queryFn: () => api.user(username) })
  const filters = { author: username, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  const posts = useQuery({
    queryKey: keys.feed(filters),
    queryFn: () => api.feed(filters),
    placeholderData: keepPreviousData,
    enabled: profile.isSuccess,
  })
  const totalPages = posts.data ? Math.max(1, Math.ceil(posts.data.total / PAGE_SIZE)) : 1

  if (profile.isPending) {
    return (
      <div className="space-y-8" aria-hidden>
        <Skeleton className="h-48 rounded-2xl" />
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          <PostCardSkeleton />
          <PostCardSkeleton />
          <PostCardSkeleton />
        </div>
      </div>
    )
  }
  if (profile.isError) {
    if (profile.error instanceof ApiError && profile.error.status === 404) return <NotFoundPage />
    return <ErrorState error={profile.error} onRetry={() => void profile.refetch()} />
  }

  function goTo(next: number) {
    setParams(next > 1 ? { page: String(next) } : {})
  }

  return (
    <div className="space-y-10">
      <title>{`${profile.data.display_name} (@${profile.data.username}) · Nebula`}</title>
      <ProfileHeader profile={profile.data} />

      <section aria-labelledby="posts-heading" className="space-y-5">
        <h2 id="posts-heading" className="font-display text-xl font-semibold">
          Posts
        </h2>
        <div aria-live="polite" aria-busy={posts.isFetching}>
          {posts.isPending ? (
            <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 3 }, (_, i) => (
                <PostCardSkeleton key={i} />
              ))}
            </div>
          ) : posts.isError ? (
            <ErrorState error={posts.error} onRetry={() => void posts.refetch()} />
          ) : posts.data.items.length === 0 ? (
            <EmptyState title="No published posts yet" />
          ) : (
            <div
              className={cn(
                'grid gap-5 md:grid-cols-2 lg:grid-cols-3',
                posts.isPlaceholderData && 'opacity-60',
              )}
            >
              {posts.data.items.map((post, index) => (
                <PostCard key={post.id} post={post} index={index} />
              ))}
            </div>
          )}
        </div>
        {posts.data && totalPages > 1 && (
          <nav className="flex items-center justify-center gap-3" aria-label="Pagination">
            <Button size="sm" disabled={page <= 1} onClick={() => goTo(page - 1)}>
              <ChevronLeft /> Previous
            </Button>
            <span className="text-sm text-muted">
              Page {page} of {totalPages}
            </span>
            <Button size="sm" disabled={page >= totalPages} onClick={() => goTo(page + 1)}>
              Next <ChevronRight />
            </Button>
          </nav>
        )}
      </section>
    </div>
  )
}
