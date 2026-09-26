// Tag picker: type and press Enter or comma, or pick a popular tag. Mirrors the API's tag rules.
import { useQuery } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { useId, useState, type KeyboardEvent } from 'react'

import { api, keys } from '@/api/endpoints'
import { MAX_TAGS, normalizeTag } from '@/lib/tags'
import { cn } from '@/lib/utils'

export function TagInput({
  value,
  onChange,
  error,
}: {
  value: string[]
  onChange: (tags: string[]) => void
  error?: string
}) {
  const id = useId()
  const [text, setText] = useState('')
  const [problem, setProblem] = useState<string | null>(null)
  const popular = useQuery({
    queryKey: keys.tags,
    queryFn: () => api.tags(),
    staleTime: 5 * 60_000,
  })
  const full = value.length >= MAX_TAGS
  const suggestions = (popular.data ?? []).map((t) => t.name).filter((n) => !value.includes(n))

  function add(raw: string) {
    if (!raw.trim()) return
    const tag = normalizeTag(raw)
    if (!tag) return setProblem('Tags use a–z, 0–9 and hyphens (up to 40 characters).')
    if (!value.includes(tag) && !full) onChange([...value, tag])
    setText('')
    setProblem(null)
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault()
      add(text)
    } else if (event.key === 'Backspace' && !text && value.length > 0) {
      onChange(value.slice(0, -1))
    }
  }

  const message = problem ?? error
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="block text-sm font-medium text-ink/90">
        Tags{' '}
        <span className="font-normal text-muted">
          ({value.length}/{MAX_TAGS})
        </span>
      </label>
      <div
        className={cn(
          'flex min-h-11 flex-wrap items-center gap-1.5 rounded-xl border border-edge bg-ink/[0.03] px-2 py-1.5 transition focus-within:border-nova/60 focus-within:ring-4 focus-within:ring-nova/15',
          message && 'border-danger/70',
        )}
      >
        {value.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-full bg-nova/15 py-0.5 pr-1 pl-2.5 text-sm text-nova"
          >
            #{tag}
            <button
              type="button"
              onClick={() => onChange(value.filter((t) => t !== tag))}
              className="rounded-full p-0.5 hover:bg-ink/10"
              aria-label={`Remove tag ${tag}`}
            >
              <X className="size-3.5" aria-hidden />
            </button>
          </span>
        ))}
        <input
          id={id}
          value={text}
          disabled={full}
          maxLength={41}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
          onBlur={() => add(text)}
          placeholder={full ? 'Tag limit reached' : 'Add a tag and press Enter'}
          aria-invalid={message ? true : undefined}
          aria-describedby={message ? `${id}-error` : undefined}
          className="h-8 min-w-32 flex-1 bg-transparent px-1.5 text-sm outline-none placeholder:text-muted/60"
        />
      </div>
      {message && (
        <p id={`${id}-error`} className="text-sm text-danger" role="alert">
          {message}
        </p>
      )}
      {!full && suggestions.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted">
          <span>Popular:</span>
          {suggestions.slice(0, 8).map((name) => (
            <button
              key={name}
              type="button"
              onClick={() => add(name)}
              className="inline-flex items-center gap-0.5 rounded-full border border-edge px-2 py-0.5 transition hover:border-nova/50 hover:text-ink"
            >
              <Plus className="size-3" aria-hidden />
              {name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
