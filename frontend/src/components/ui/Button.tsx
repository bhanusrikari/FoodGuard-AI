import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/cn'

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
export type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  isLoading?: boolean
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-primary-700 text-white hover:bg-primary-800 active:bg-primary-900 disabled:bg-primary-300',
  secondary:
    'bg-neutral-800 text-white hover:bg-neutral-900 active:bg-neutral-950 disabled:bg-neutral-300',
  outline:
    'border border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50 active:bg-neutral-100 disabled:text-neutral-400',
  ghost: 'text-neutral-600 hover:bg-neutral-100 active:bg-neutral-200 disabled:text-neutral-300',
  danger: 'bg-danger-600 text-white hover:bg-danger-700 active:bg-danger-700 disabled:bg-danger-100',
}

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-sm gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
  lg: 'h-12 px-6 text-base gap-2',
}

/** Shared with LinkButton so a styled `<a>` (e.g. a React Router `Link`)
 * can look identical to a real `<button>` without nesting one inside the
 * other — nesting interactive elements is invalid HTML and breaks
 * keyboard/screen-reader behavior. */
export function buttonClassNames({
  variant = 'primary',
  size = 'md',
  className,
}: {
  variant?: ButtonVariant
  size?: ButtonSize
  className?: string
}) {
  return cn(
    'inline-flex items-center justify-center rounded-lg font-medium transition-all duration-200 ease-out',
    'hover:-translate-y-px active:translate-y-0 active:scale-[0.98]',
    'motion-reduce:transition-none motion-reduce:hover:translate-y-0 motion-reduce:active:scale-100',
    'disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:active:scale-100',
    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500',
    variantStyles[variant],
    sizeStyles[size],
    className,
  )
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading, disabled, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={buttonClassNames({ variant, size, className })}
        disabled={disabled || isLoading}
        aria-busy={isLoading}
        {...props}
      >
        {isLoading && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
        {children}
      </button>
    )
  },
)
Button.displayName = 'Button'
