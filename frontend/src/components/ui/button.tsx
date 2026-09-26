// Button with visual variants (shadcn-style: the code lives in the repo, variants via cva).
import type { VariantProps } from 'class-variance-authority'
import { Loader2 } from 'lucide-react'
import type { ComponentProps } from 'react'

import { cn } from '@/lib/utils'

import { buttonVariants } from './button-variants'

type ButtonProps = ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & { loading?: boolean }

export function Button({
  className,
  variant,
  size,
  loading = false,
  disabled,
  children,
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <Loader2 className="animate-spin" aria-hidden />}
      {children}
    </button>
  )
}
