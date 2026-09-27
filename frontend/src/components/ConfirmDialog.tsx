// A small modal question with a safe default: focus starts on Cancel and Escape cancels.
import { useEffect, useId, useRef, type ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/misc'

type ConfirmDialogProps = {
  open: boolean
  title: string
  children: ReactNode
  confirmLabel: string
  cancelLabel?: string
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const id = useId()
  const cancel = useRef<HTMLButtonElement>(null)
  const cancelRef = useRef(onCancel) // latest handler, without re-running the effect
  useEffect(() => {
    cancelRef.current = onCancel
  })
  useEffect(() => {
    if (!open) return
    cancel.current?.focus() // the safe choice gets focus
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') cancelRef.current()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-void/70 p-4 backdrop-blur-sm">
      <Card
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={`${id}-title`}
        aria-describedby={`${id}-body`}
        className="w-full max-w-sm space-y-4 p-6 shadow-glow"
      >
        <h2 id={`${id}-title`} className="font-display text-lg font-semibold">
          {title}
        </h2>
        <div id={`${id}-body`} className="text-sm text-muted">
          {children}
        </div>
        <div className="flex justify-end gap-2">
          <Button ref={cancel} variant="ghost" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button variant="danger" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </Card>
    </div>
  )
}
