// Form controls: labelled input and textarea with an accessible error message.
import { useId, type ComponentProps, type ReactNode } from 'react'

import { cn } from '@/lib/utils'

const control =
  'w-full rounded-xl border border-edge bg-ink/[0.03] px-3.5 text-ink placeholder:text-muted/60 transition outline-none focus:border-nova/60 focus:bg-ink/[0.05] focus:ring-4 focus:ring-nova/15 aria-invalid:border-danger/70'

type FieldProps = { label: string; error?: string; hint?: ReactNode }

function Field({
  label,
  error,
  hint,
  id,
  children,
}: FieldProps & { id: string; children: ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-ink/90">
        {label}
      </label>
      {children}
      {error ? (
        <p id={`${id}-error`} className="text-sm text-danger" role="alert">
          {error}
        </p>
      ) : (
        hint && <p className="text-xs text-muted">{hint}</p>
      )}
    </div>
  )
}

export function TextField({
  label,
  error,
  hint,
  className,
  ...props
}: FieldProps & ComponentProps<'input'>) {
  const id = useId()
  return (
    <Field label={label} error={error} hint={hint} id={id}>
      <input
        id={id}
        className={cn(control, 'h-11', className)}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        {...props}
      />
    </Field>
  )
}

export function TextArea({ className, ...props }: ComponentProps<'textarea'>) {
  return (
    <textarea
      className={cn(control, 'min-h-24 resize-y py-3 leading-relaxed', className)}
      {...props}
    />
  )
}

export function TextAreaField({
  label,
  error,
  hint,
  className,
  ...props
}: FieldProps & ComponentProps<'textarea'>) {
  const id = useId()
  return (
    <Field label={label} error={error} hint={hint} id={id}>
      <TextArea
        id={id}
        className={className}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        {...props}
      />
    </Field>
  )
}
