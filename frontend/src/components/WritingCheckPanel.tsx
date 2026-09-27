// "Check my writing": spelling, grammar and style suggestions for the draft, applied in place.
import { useMutation } from '@tanstack/react-query'
import { Check, RefreshCw, SpellCheck, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { api } from '@/api/endpoints'
import { describeError } from '@/api/errors'
import type { WritingIssue } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/misc'
import { cn } from '@/lib/utils'
import {
  applySuggestion,
  CATEGORY_LABELS,
  issueContext,
  MAX_CHECK_BYTES,
  tooLongToCheck,
} from '@/lib/writing'

type Result = { checked: string; issues: WritingIssue[] }

type WritingCheckPanelProps = {
  text: string
  onChange: (text: string) => void
  onShow: (issue: WritingIssue) => void
  onClose: () => void
}

export function WritingCheckPanel({ text, onChange, onShow, onClose }: WritingCheckPanelProps) {
  const [result, setResult] = useState<Result | null>(null)
  const check = useMutation({
    mutationFn: (checked: string) => api.checkWriting(checked),
    onSuccess: ({ issues }, checked) => setResult({ checked, issues }),
  })
  const tooLong = tooLongToCheck(text)
  // Offsets point into the text that was checked; any other edit makes them unreliable.
  const stale = result !== null && result.checked !== text

  // Check once when the panel opens; after that the author asks with "Check again".
  // A ref, not state: StrictMode runs effects twice in development, and each check counts
  // against the rate limit.
  const opening = useRef<string | null>(text)
  const { mutate } = check
  useEffect(() => {
    const first = opening.current
    opening.current = null
    if (first?.trim() && !tooLongToCheck(first)) mutate(first)
  }, [mutate])

  function apply(issue: WritingIssue, replacement: string) {
    if (!result) return
    const next = applySuggestion(result.checked, result.issues, issue, replacement)
    setResult({ checked: next.text, issues: next.issues })
    onChange(next.text)
  }

  function ignore(issue: WritingIssue) {
    setResult(
      (current) => current && { ...current, issues: current.issues.filter((i) => i !== issue) },
    )
  }

  let body
  if (!text.trim()) body = <p className="text-muted">Write something first, then check it.</p>
  else if (tooLong) {
    body = (
      <p className="text-muted">
        This post is too long to check in one go (over {MAX_CHECK_BYTES / 1000} KB). Check a shorter
        draft, or split it into parts.
      </p>
    )
  } else if (check.isPending) body = <p className="text-muted">Checking…</p>
  else if (check.isError) {
    body = (
      <p className="text-danger" role="alert">
        {describeError(check.error)}
      </p>
    )
  } else if (result && result.issues.length === 0) {
    body = (
      <p className="flex items-center gap-2 text-plasma">
        <Check className="size-4" aria-hidden /> No issues found.
      </p>
    )
  } else if (result) {
    body = (
      <>
        {stale && (
          <p className="rounded-lg bg-flare/10 px-3 py-2 text-flare">
            The text changed since the check. Check again to update the suggestions.
          </p>
        )}
        <ul className={cn('space-y-3', stale && 'pointer-events-none opacity-50')} inert={stale}>
          {result.issues.map((issue) => {
            const { before, match, after } = issueContext(result.checked, issue)
            return (
              <li
                key={`${issue.offset}-${issue.length}-${issue.message}`}
                className="space-y-2 rounded-xl border border-edge p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <p>
                    <span className="mr-2 rounded-full bg-nova/15 px-2 py-0.5 text-xs font-medium text-nova">
                      {CATEGORY_LABELS[issue.category]}
                    </span>
                    {issue.message}
                  </p>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => ignore(issue)}
                    aria-label={`Ignore: ${issue.message}`}
                    title="Ignore"
                  >
                    <X />
                  </Button>
                </div>
                <button
                  type="button"
                  onClick={() => onShow(issue)}
                  className="block w-full truncate rounded-lg bg-ink/[0.04] px-2.5 py-1.5 text-left font-mono text-xs text-muted hover:text-ink"
                  title="Show in the editor"
                >
                  {before}
                  <mark className="rounded bg-danger/20 px-0.5 text-ink">{match}</mark>
                  {after}
                </button>
                {issue.suggestions.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {issue.suggestions.map((suggestion) => (
                      <Button
                        key={suggestion}
                        size="sm"
                        onClick={() => apply(issue, suggestion)}
                        aria-label={`Replace “${match}” with “${suggestion}”`}
                      >
                        {suggestion || '(remove)'}
                      </Button>
                    ))}
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      </>
    )
  }

  return (
    <Card className="space-y-3 p-4 text-sm" aria-labelledby="writing-check-title">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="writing-check-title" className="flex items-center gap-2 font-medium">
          <SpellCheck className="size-4 text-nova" aria-hidden />
          Writing check
          {result && !check.isPending && result.issues.length > 0 && (
            <span className="text-muted">
              · {result.issues.length} {result.issues.length === 1 ? 'suggestion' : 'suggestions'}
            </span>
          )}
        </h2>
        <div className="flex gap-1">
          <Button
            size="sm"
            variant="ghost"
            loading={check.isPending}
            disabled={tooLong || !text.trim()}
            onClick={() => check.mutate(text)}
          >
            <RefreshCw /> Check again
          </Button>
          <Button size="sm" variant="ghost" onClick={onClose} aria-label="Close writing check">
            <X />
          </Button>
        </div>
      </div>
      <div aria-live="polite" className="max-h-96 space-y-3 overflow-auto">
        {body}
      </div>
      <p className="text-xs text-muted">
        Your text is sent to LanguageTool to check it. Nebula doesn’t store it.
      </p>
    </Card>
  )
}
