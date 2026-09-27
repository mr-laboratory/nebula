// Browser file helpers: save a downloaded Blob, and the file types the editor can import.
import type { Download } from '@/api/client'

export const IMPORT_ACCEPT = '.md,.markdown,.txt,.docx'
export const IMPORT_MAX_BYTES = 1024 * 1024 // the API's limit, checked here to fail fast

/** Hand a downloaded file to the browser's save flow. */
export function saveFile({ blob, filename }: Download): void {
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  link.rel = 'noopener'
  document.body.append(link)
  link.click()
  link.remove()
  // Revoke later: some browsers read the URL after click() returns.
  setTimeout(() => URL.revokeObjectURL(href), 60_000)
}

/** A message for files the API would reject anyway, or null when it's worth uploading. */
export function importProblem(file: File): string | null {
  const extension = file.name.toLowerCase().split('.').pop() ?? ''
  if (extension === 'pdf') {
    return 'PDFs can’t be imported. Save it as a Word document (.docx) and import that.'
  }
  if (!IMPORT_ACCEPT.split(',').includes(`.${extension}`)) {
    return 'Choose a .md, .txt or .docx file.'
  }
  if (file.size > IMPORT_MAX_BYTES) return 'That file is over 1 MB.'
  if (file.size === 0) return 'That file is empty.'
  return null
}
