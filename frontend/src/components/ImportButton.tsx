// "Import file": turn a .md, .txt or .docx file into the editor's title and content.
import { useMutation } from '@tanstack/react-query'
import { FileUp } from 'lucide-react'
import { useRef, useState } from 'react'

import { api } from '@/api/endpoints'
import { describeError } from '@/api/errors'
import type { ImportedPost } from '@/api/types'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Button } from '@/components/ui/button'
import { IMPORT_ACCEPT, importProblem } from '@/lib/files'

type ImportButtonProps = {
  /** Asks before replacing a draft that already has something in it. */
  hasContent: boolean
  onImported: (post: ImportedPost, filename: string) => void
  onError: (message: string) => void
  disabled?: boolean
}

export function ImportButton({ hasContent, onImported, onError, disabled }: ImportButtonProps) {
  const input = useRef<HTMLInputElement>(null)
  const [pending, setPending] = useState<File | null>(null) // waiting for "replace?"
  const upload = useMutation({
    mutationFn: (file: File) => api.importPost(file),
    onSuccess: (post, file) => onImported(post, file.name),
    onError: (error) => onError(describeError(error)),
  })

  function choose(file: File | undefined) {
    if (input.current) input.current.value = '' // choosing the same file again still fires
    if (!file) return
    const problem = importProblem(file)
    if (problem) onError(problem)
    else if (hasContent) setPending(file)
    else upload.mutate(file)
  }

  return (
    <>
      <input
        ref={input}
        type="file"
        accept={IMPORT_ACCEPT}
        className="hidden"
        aria-hidden
        tabIndex={-1}
        onChange={(event) => choose(event.target.files?.[0])}
      />
      <Button
        size="sm"
        variant="ghost"
        loading={upload.isPending}
        disabled={disabled}
        onClick={() => input.current?.click()}
        title="Import a .md, .txt or .docx file (up to 1 MB)"
      >
        <FileUp /> Import file
      </Button>
      <ConfirmDialog
        open={pending !== null}
        title="Replace this draft?"
        confirmLabel="Replace"
        onCancel={() => setPending(null)}
        onConfirm={() => {
          if (pending) upload.mutate(pending)
          setPending(null)
        }}
      >
        The title and content will be replaced with “{pending?.name}”. Nothing is saved until you
        save the draft.
      </ConfirmDialog>
    </>
  )
}
