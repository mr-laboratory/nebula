// Write and edit posts: Markdown with live preview, drafts, publishing and an unsaved-changes guard.
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Eye, FileText, Globe, Save, Undo2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useBeforeUnload, useBlocker, useNavigate, useParams } from 'react-router'

import { api, keys } from '@/api/endpoints'
import { ApiError, describeError } from '@/api/errors'
import type { PostDetail } from '@/api/types'
import { useAuth } from '@/auth/context'
import { Markdown } from '@/components/Markdown'
import { ErrorState } from '@/components/States'
import { TagInput } from '@/components/TagInput'
import { Button } from '@/components/ui/button'
import { buttonVariants } from '@/components/ui/button-variants'
import { TextAreaField, TextField } from '@/components/ui/field'
import { Card, Skeleton } from '@/components/ui/misc'
import {
  changedFields,
  draftFrom,
  EMPTY_DRAFT,
  isDirty,
  LIMITS,
  validate,
  type Draft,
  type DraftErrors,
} from '@/lib/draft'
import { isAuthor } from '@/lib/permissions'
import { cn, timeAgo } from '@/lib/utils'
import { NotFoundPage } from '@/pages/NotFoundPage'

type Intent = 'save' | 'publish' | 'unpublish'

function StatusBadge({ post }: { post: PostDetail | null }) {
  const published = post?.status === 'published'
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
        published ? 'bg-plasma/15 text-plasma' : 'bg-flare/15 text-flare',
      )}
    >
      {published ? (
        <Globe className="size-3" aria-hidden />
      ) : (
        <FileText className="size-3" aria-hidden />
      )}
      {post ? (published ? 'Published' : 'Draft') : 'New draft'}
    </span>
  )
}

function LeaveGuard({ blocker }: { blocker: ReturnType<typeof useBlocker> }) {
  const stay = useRef<HTMLButtonElement>(null)
  const open = blocker.state === 'blocked'
  useEffect(() => {
    if (!open) return
    stay.current?.focus() // the safe choice gets focus
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') blocker.reset?.()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, blocker])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-void/70 p-4 backdrop-blur-sm">
      <Card
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="leave-title"
        className="w-full max-w-sm space-y-4 p-6 shadow-glow"
      >
        <h2 id="leave-title" className="font-display text-lg font-semibold">
          Leave without saving?
        </h2>
        <p className="text-sm text-muted">Your unsaved changes to this post will be lost.</p>
        <div className="flex justify-end gap-2">
          <Button ref={stay} variant="ghost" onClick={() => blocker.reset?.()}>
            Keep editing
          </Button>
          <Button variant="danger" onClick={() => blocker.proceed?.()}>
            Discard changes
          </Button>
        </div>
      </Card>
    </div>
  )
}

function Editor({ initial }: { initial: PostDetail | null }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [post, setPost] = useState(initial) // the last version the server confirmed
  const [draft, setDraft] = useState<Draft>(() => (initial ? draftFrom(initial) : EMPTY_DRAFT))
  const [errors, setErrors] = useState<DraftErrors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [pending, setPending] = useState<Intent | null>(null)
  const [tab, setTab] = useState<'write' | 'preview'>('write')

  const saved = post ? draftFrom(post) : EMPTY_DRAFT
  const dirty = isDirty(saved, draft)
  // Read by the navigation blocker. A ref, so a save can clear it right before navigating.
  const dirtyRef = useRef(dirty)
  useEffect(() => {
    dirtyRef.current = dirty
  }, [dirty])

  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      dirtyRef.current && currentLocation.pathname !== nextLocation.pathname,
  )
  useBeforeUnload((event) => {
    if (dirtyRef.current) event.preventDefault() // browser shows its own "leave site?" prompt
  })

  function edit<K extends keyof Draft>(field: K, value: Draft[K]) {
    setDraft((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({ ...current, [field]: undefined }))
  }

  async function submit(intent: Intent) {
    const problems = validate(draft)
    setErrors(problems)
    setFormError(null)
    if (Object.keys(problems).length > 0) return
    setPending(intent)
    try {
      let result: PostDetail
      if (!post) {
        result = await api.createPost({
          title: draft.title.trim(),
          content: draft.content,
          excerpt: draft.excerpt.trim() || null,
          tags: draft.tags,
        })
      } else {
        const changes = changedFields(saved, draft)
        result = Object.keys(changes).length > 0 ? await api.updatePost(post.id, changes) : post
      }
      if (intent === 'publish' && result.status !== 'published')
        result = await api.publish(result.id)
      if (intent === 'unpublish' && result.status === 'published') {
        result = await api.unpublish(result.id)
      }

      queryClient.setQueryData(keys.post(result.slug), result)
      void queryClient.invalidateQueries({ queryKey: ['posts'] })
      void queryClient.invalidateQueries({ queryKey: keys.tags })
      void queryClient.invalidateQueries({ queryKey: ['user'] })
      setPost(result)
      setDraft(draftFrom(result))
      dirtyRef.current = false

      if (intent === 'publish') void navigate(`/p/${result.slug}`)
      else if (result.slug !== initial?.slug) {
        // New post, or a draft's slug followed its new title: keep the URL pointing at it.
        void navigate(`/edit/${result.slug}`, { replace: true })
      }
    } catch (error) {
      const fields = error instanceof ApiError ? error.fieldMessages() : {}
      setErrors(fields)
      if (Object.keys(fields).length === 0) setFormError(describeError(error))
    } finally {
      setPending(null)
    }
  }

  // Cmd/Ctrl+S saves, like any editor.
  const submitRef = useRef(submit)
  useEffect(() => {
    submitRef.current = submit
  })
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
        event.preventDefault()
        void submitRef.current('save')
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const published = post?.status === 'published'
  const busy = pending !== null
  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-24">
      <title>{`${post ? `Edit: ${post.title}` : 'New post'} · Nebula`}</title>
      <LeaveGuard blocker={blocker} />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink"
        >
          <ArrowLeft className="size-4" aria-hidden /> My posts
        </Link>
        <div className="flex items-center gap-3 text-sm text-muted">
          <StatusBadge post={post} />
          <span aria-live="polite">
            {dirty ? 'Unsaved changes' : post ? `Saved ${timeAgo(post.updated_at)}` : ''}
          </span>
        </div>
      </div>

      <div className="space-y-5">
        <TextField
          label="Title"
          value={draft.title}
          maxLength={LIMITS.title}
          onChange={(event) => edit('title', event.target.value)}
          placeholder="A title that sparks curiosity"
          error={errors.title}
          className="h-14 font-display text-2xl font-semibold sm:text-3xl"
        />
        <div className="grid gap-5 md:grid-cols-2">
          <TextAreaField
            label="Excerpt (optional)"
            value={draft.excerpt}
            maxLength={LIMITS.excerpt}
            rows={2}
            onChange={(event) => edit('excerpt', event.target.value)}
            placeholder="Shown on post cards. Leave empty to use the opening lines."
            error={errors.excerpt}
            hint={`${draft.excerpt.length}/${LIMITS.excerpt}`}
            className="min-h-11"
          />
          <TagInput
            value={draft.tags}
            onChange={(tags) => edit('tags', tags)}
            error={errors.tags}
          />
        </div>
      </div>

      {/* Phones: switch between writing and preview. Large screens: side by side. */}
      <div
        className="flex gap-1 rounded-xl p-1 glass lg:hidden"
        role="tablist"
        aria-label="Editor view"
      >
        {(['write', 'preview'] as const).map((name) => (
          <button
            key={name}
            type="button"
            role="tab"
            aria-selected={tab === name}
            onClick={() => setTab(name)}
            className={cn(
              'flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-sm capitalize transition',
              tab === name ? 'bg-ink/10 text-ink' : 'text-muted hover:text-ink',
            )}
          >
            {name === 'write' ? (
              <FileText className="size-4" aria-hidden />
            ) : (
              <Eye className="size-4" aria-hidden />
            )}
            {name}
          </button>
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className={cn(tab !== 'write' && 'hidden lg:block')}>
          <TextAreaField
            label="Content"
            value={draft.content}
            maxLength={LIMITS.content}
            onChange={(event) => edit('content', event.target.value)}
            placeholder={
              '# Start with a heading\n\nWrite in **Markdown**: lists, links, `code`, tables…'
            }
            error={errors.content}
            hint="Markdown supported. Cmd/Ctrl + S saves."
            spellCheck
            className="min-h-[28rem] font-mono text-sm lg:min-h-[36rem]"
          />
        </div>
        <section
          aria-label="Preview"
          className={cn('space-y-1.5', tab !== 'preview' && 'hidden lg:block')}
        >
          <p className="text-sm font-medium text-ink/90">Preview</p>
          <Card className="min-h-[28rem] overflow-auto p-6 lg:max-h-[36rem] lg:min-h-[36rem]">
            {draft.content.trim() ? (
              <Markdown>{draft.content}</Markdown>
            ) : (
              <p className="text-muted">Your formatted post will appear here.</p>
            )}
          </Card>
        </section>
      </div>

      {formError && (
        <p className="rounded-xl bg-danger/10 px-3 py-2 text-sm text-danger" role="alert">
          {formError}
        </p>
      )}

      <div className="sticky bottom-4 z-30">
        <Card className="flex flex-wrap items-center justify-end gap-2 p-3 shadow-glow">
          {post && published && (
            <Link
              to={`/p/${post.slug}`}
              className={cn(buttonVariants({ variant: 'ghost', size: 'md' }), 'mr-auto')}
            >
              <Eye /> View
            </Link>
          )}
          {published ? (
            <>
              <Button
                onClick={() => void submit('unpublish')}
                loading={pending === 'unpublish'}
                disabled={busy}
              >
                <Undo2 /> Unpublish
              </Button>
              <Button
                variant="primary"
                onClick={() => void submit('save')}
                loading={pending === 'save'}
                disabled={busy || !dirty}
              >
                <Save /> Update
              </Button>
            </>
          ) : (
            <>
              <Button
                onClick={() => void submit('save')}
                loading={pending === 'save'}
                disabled={busy || (post !== null && !dirty)}
              >
                <Save /> Save draft
              </Button>
              <Button
                variant="primary"
                onClick={() => void submit('publish')}
                loading={pending === 'publish'}
                disabled={busy}
              >
                <Globe /> Publish
              </Button>
            </>
          )}
        </Card>
      </div>
    </div>
  )
}

function EditorSkeleton() {
  return (
    <div className="mx-auto max-w-6xl space-y-6" aria-hidden>
      <Skeleton className="h-14" />
      <Skeleton className="h-24" />
      <Skeleton className="h-96" />
    </div>
  )
}

function EditExisting({ slug }: { slug: string }) {
  const { me } = useAuth()
  const query = useQuery({ queryKey: keys.post(slug), queryFn: () => api.post(slug) })
  if (query.isPending) return <EditorSkeleton />
  if (query.isError) {
    if (query.error instanceof ApiError && query.error.status === 404) return <NotFoundPage />
    return <ErrorState error={query.error} onRetry={() => void query.refetch()} />
  }
  // Only authors edit (moderators may delete, never rewrite). The API enforces this too.
  if (!isAuthor(me, query.data)) return <NotFoundPage />
  return <Editor key={query.data.id} initial={query.data} />
}

export function EditorPage() {
  const { slug } = useParams()
  return slug ? <EditExisting slug={slug} /> : <Editor key="new" initial={null} />
}
