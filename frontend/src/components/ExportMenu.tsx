// A download button with a small menu: export as Word (.docx) or PDF.
import { useMutation } from '@tanstack/react-query'
import { ChevronDown, Download as DownloadIcon } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'

import type { Download } from '@/api/client'
import { describeError } from '@/api/errors'
import type { ExportFormat } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/misc'
import { saveFile } from '@/lib/files'
import { cn } from '@/lib/utils'

const FORMATS: { format: ExportFormat; label: string }[] = [
  { format: 'docx', label: 'Word (.docx)' },
  { format: 'pdf', label: 'PDF' },
]

type ExportMenuProps = {
  label: string
  /** For screen readers when the visible label is short, e.g. "Export “Title”". */
  ariaLabel?: string
  run: (format: ExportFormat) => Promise<Download>
  size?: 'sm' | 'md'
  align?: 'left' | 'right'
}

export function ExportMenu({
  label,
  ariaLabel,
  run,
  size = 'sm',
  align = 'right',
}: ExportMenuProps) {
  const id = useId()
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const download = useMutation({ mutationFn: run, onSuccess: saveFile })

  useEffect(() => {
    if (!open) return
    function close(event: MouseEvent | KeyboardEvent) {
      if (
        event instanceof KeyboardEvent
          ? event.key === 'Escape'
          : !root.current?.contains(event.target as Node)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', close)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', close)
    }
  }, [open])

  return (
    <div ref={root} className="relative">
      <Button
        size={size}
        variant="ghost"
        loading={download.isPending}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={id}
        aria-label={ariaLabel}
        onClick={() => setOpen((current) => !current)}
      >
        <DownloadIcon /> {label} <ChevronDown />
      </Button>
      {open && (
        <Card
          id={id}
          role="menu"
          className={cn(
            'absolute top-full z-40 mt-1 w-44 p-1 shadow-glow',
            align === 'right' ? 'right-0' : 'left-0',
          )}
        >
          {FORMATS.map(({ format, label: name }) => (
            <button
              key={format}
              type="button"
              role="menuitem"
              className="block w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-ink/5"
              onClick={() => {
                setOpen(false)
                download.mutate(format)
              }}
            >
              {name}
            </button>
          ))}
        </Card>
      )}
      {download.isError && (
        <p
          className="absolute top-full right-0 z-30 mt-1 w-64 rounded-lg bg-danger/10 px-3 py-2 text-xs text-danger"
          role="alert"
        >
          {describeError(download.error)}
        </p>
      )}
    </div>
  )
}
