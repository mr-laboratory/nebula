// Public feed: search, tag and author filters, sort order and pagination, all kept in the URL.
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Search, X } from 'lucide-react'
import { motion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router'

import { api, keys } from '@/api/endpoints'
import type { FeedFilters } from '@/api/types'
import { PostCard } from '@/components/PostCard'
import { EmptyState, ErrorState, PostCardSkeleton } from '@/components/States'
import { Button } from '@/components/ui/button'
import { Chip } from '@/components/ui/misc'
import { cn } from '@/lib/utils'

const PAGE_SIZE = 12
const SORTS = [
  { value: 'newest', label: 'Newest' },
  { value: 'oldest', label: 'Oldest' },
] as const

function useFeedParams() {
  const [params, setParams] = useSearchParams()
  const page = Math.max(1, Number(params.get('page')) || 1)
  const filters: FeedFilters = {
    tag: params.get('tag') ?? undefined,
    author: params.get('author') ?? undefined,
    q: params.get('q') ?? undefined,
    sort: params.get('sort') === 'oldest' ? 'oldest' : 'newest',
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  }
  /** Change filters; any change except paging goes back to page 1. */
  function update(changes: Record<string, string | null>) {
    setParams((current) => {
      const next = new URLSearchParams(current)
      for (const [key, value] of Object.entries(changes)) {
        if (value) next.set(key, value)
        else next.delete(key)
      }
      if (!('page' in changes)) next.delete('page')
      return next
    })
  }
  return { filters, page, update }
}

function SearchBox({ value, onSearch }: { value: string; onSearch: (q: string) => void }) {
  const [text, setText] = useState(value)
  const [synced, setSynced] = useState(value)
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined)
  // The URL changed from outside (back button, tag link): show its query. Adjusting state during
  // render like this avoids an extra effect-driven render.
  if (value !== synced) {
    setSynced(value)
    if (value !== text.trim()) setText(value)
  }
  useEffect(() => () => clearTimeout(timer.current), [])

  function change(next: string) {
    setText(next)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => onSearch(next.trim()), 350) // debounce: one request per pause
  }

  return (
    <label className="flex h-11 flex-1 items-center gap-2 rounded-xl px-3.5 glass focus-within:border-nova/60 focus-within:ring-4 focus-within:ring-nova/15">
      <Search className="size-4 text-muted" aria-hidden />
      <span className="sr-only">Search posts</span>
      <input
        type="search"
        value={text}
        maxLength={100}
        onChange={(event) => change(event.target.value)}
        placeholder="Search titles and summaries…"
        className="h-full w-full bg-transparent outline-none placeholder:text-muted/60"
      />
    </label>
  )
}

export function FeedPage() {
  const { filters, page, update } = useFeedParams()
  const feed = useQuery({
    queryKey: keys.feed(filters),
    queryFn: () => api.feed(filters),
    placeholderData: keepPreviousData, // keep the old page visible while the next one loads
  })
  const tags = useQuery({ queryKey: keys.tags, queryFn: () => api.tags(), staleTime: 5 * 60_000 })
  const totalPages = feed.data ? Math.max(1, Math.ceil(feed.data.total / PAGE_SIZE)) : 1
  const filtered = Boolean(filters.q || filters.tag || filters.author)

  return (
    <div className="space-y-10">
      <title>Nebula · Where ideas take shape</title>
      <section className="space-y-4 pt-2 text-center sm:pt-6">
        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="font-display text-4xl font-bold tracking-tight text-balance sm:text-6xl"
        >
          Where ideas <span className="text-gradient">take shape</span>
        </motion.h1>
        <p className="mx-auto max-w-xl text-pretty text-muted sm:text-lg">
          Stories, guides and experiments from the Nebula community. Read freely; sign in to like
          and join the conversation.
        </p>
      </section>

      <section className="space-y-4" aria-label="Filters">
        <div className="flex flex-col gap-3 sm:flex-row">
          <SearchBox value={filters.q ?? ''} onSearch={(q) => update({ q: q || null })} />
          <fieldset className="flex h-11 shrink-0 rounded-xl p-1 glass">
            <legend className="sr-only">Sort</legend>
            {SORTS.map((sort) => (
              <button
                key={sort.value}
                type="button"
                aria-pressed={filters.sort === sort.value}
                onClick={() => update({ sort: sort.value === 'newest' ? null : sort.value })}
                className={cn(
                  'rounded-lg px-4 text-sm transition',
                  filters.sort === sort.value
                    ? 'bg-white/10 text-ink'
                    : 'text-muted hover:text-ink',
                )}
              >
                {sort.label}
              </button>
            ))}
          </fieldset>
        </div>
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0">
          {filters.author && (
            <button type="button" onClick={() => update({ author: null })}>
              <Chip active className="gap-1">
                by @{filters.author} <X className="size-3" aria-label="Remove author filter" />
              </Chip>
            </button>
          )}
          {tags.data?.map((tag) => {
            const active = filters.tag === tag.name
            return (
              <button
                key={tag.name}
                type="button"
                aria-pressed={active}
                onClick={() => update({ tag: active ? null : tag.name })}
                className="shrink-0"
              >
                <Chip active={active}>
                  #{tag.name} <span className="ml-1 opacity-60">{tag.post_count}</span>
                </Chip>
              </button>
            )
          })}
        </div>
      </section>

      <section aria-live="polite" aria-busy={feed.isFetching}>
        {feed.isPending ? (
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }, (_, i) => (
              <PostCardSkeleton key={i} />
            ))}
          </div>
        ) : feed.isError ? (
          <ErrorState error={feed.error} onRetry={() => void feed.refetch()} />
        ) : feed.data.items.length === 0 ? (
          <EmptyState title={filtered ? 'No posts match' : 'Nothing here yet'}>
            {filtered
              ? 'Try another search or remove a filter.'
              : 'The first story is yet to be told.'}
          </EmptyState>
        ) : (
          <div
            className={cn(
              'grid gap-5 md:grid-cols-2 lg:grid-cols-3',
              feed.isPlaceholderData && 'opacity-60',
            )}
          >
            {feed.data.items.map((post, index) => (
              <PostCard key={post.id} post={post} index={index} />
            ))}
          </div>
        )}
      </section>

      {feed.data && totalPages > 1 && (
        <nav className="flex items-center justify-center gap-3" aria-label="Pagination">
          <Button
            size="sm"
            disabled={page <= 1}
            onClick={() => update({ page: page - 1 > 1 ? String(page - 1) : null })}
          >
            <ChevronLeft /> Previous
          </Button>
          <span className="text-sm text-muted">
            Page {page} of {totalPages}
          </span>
          <Button
            size="sm"
            disabled={page >= totalPages}
            onClick={() => update({ page: String(page + 1) })}
          >
            Next <ChevronRight />
          </Button>
        </nav>
      )}
    </div>
  )
}
