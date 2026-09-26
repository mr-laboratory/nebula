// Tag rules shared by the editor: the same limits the API enforces, checked before sending.
export const MAX_TAGS = 5
const TAG = /^[a-z0-9-]{1,40}$/

/** "Machine Learning" → "machine-learning"; null if it still breaks the API's rule. */
export function normalizeTag(raw: string): string | null {
  const tag = raw.trim().toLowerCase().replace(/^#/, '').replace(/\s+/g, '-')
  return TAG.test(tag) ? tag : null
}
