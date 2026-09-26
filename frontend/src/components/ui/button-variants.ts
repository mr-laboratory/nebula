// Button styles as a class-name function, so links can look like buttons too.
import { cva } from 'class-variance-authority'

export const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-xl font-medium whitespace-nowrap transition duration-200 select-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        primary:
          'bg-gradient-to-r from-nova to-plasma text-void shadow-glow hover:brightness-110 active:scale-[0.98]',
        glass: 'glass text-ink hover:border-nova/50 hover:bg-ink/[0.06]',
        ghost: 'text-muted hover:bg-ink/5 hover:text-ink',
        danger: 'bg-danger/15 text-danger ring-1 ring-danger/30 hover:bg-danger/25',
      },
      size: {
        sm: 'h-8 px-3 text-sm',
        md: 'h-10 px-4 text-sm',
        lg: 'h-12 px-6 text-base',
        icon: 'size-9',
      },
    },
    defaultVariants: { variant: 'glass', size: 'md' },
  },
)
