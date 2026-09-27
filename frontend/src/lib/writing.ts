// "Check my writing": show issues in context and apply suggestions without breaking offsets.
import type { WritingIssue } from '@/api/types'

const CONTEXT = 40 // characters shown on each side of an issue

/** The flagged text with a little context on each side, never crossing a line break. */
export function issueContext(text: string, issue: WritingIssue) {
  const end = issue.offset + issue.length
  const from = Math.max(0, issue.offset - CONTEXT)
  const to = Math.min(text.length, end + CONTEXT)
  let before = text.slice(from, issue.offset)
  let after = text.slice(end, to)
  const lineStart = before.lastIndexOf('\n')
  const lineEnd = after.indexOf('\n')
  const cutBefore = lineStart === -1 && from > 0
  const cutAfter = lineEnd === -1 && to < text.length
  if (lineStart !== -1) before = before.slice(lineStart + 1)
  if (lineEnd !== -1) after = after.slice(0, lineEnd)
  return {
    before: (cutBefore ? '…' : '') + before,
    match: text.slice(issue.offset, end),
    after: after + (cutAfter ? '…' : ''),
  }
}

/**
 * Replace one issue's text and keep the rest usable: later issues move by the change in
 * length, and any that overlapped the replaced text are dropped.
 */
export function applySuggestion(
  text: string,
  issues: WritingIssue[],
  target: WritingIssue,
  replacement: string,
): { text: string; issues: WritingIssue[] } {
  const start = target.offset
  const end = start + target.length
  const shift = replacement.length - target.length
  const next = text.slice(0, start) + replacement + text.slice(end)
  const remaining = issues.flatMap((issue) => {
    if (issue === target) return []
    const issueEnd = issue.offset + issue.length
    if (issueEnd <= start) return [issue]
    if (issue.offset >= end) return [{ ...issue, offset: issue.offset + shift }]
    return [] // overlapped the replaced text
  })
  return { text: next, issues: remaining }
}

export const CATEGORY_LABELS: Record<WritingIssue['category'], string> = {
  spelling: 'Spelling',
  grammar: 'Grammar',
  style: 'Style',
  punctuation: 'Punctuation',
  other: 'Other',
}

export const MAX_CHECK_BYTES = 20_000 // the API's limit, in UTF-8 bytes

export function tooLongToCheck(text: string): boolean {
  return new TextEncoder().encode(text).length > MAX_CHECK_BYTES
}
