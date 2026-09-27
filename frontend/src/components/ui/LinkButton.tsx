import { forwardRef } from 'react'
import { Link, type LinkProps } from 'react-router-dom'
import { buttonClassNames, type ButtonSize, type ButtonVariant } from './Button'

interface LinkButtonProps extends LinkProps {
  variant?: ButtonVariant
  size?: ButtonSize
}

/**
 * A single `<a>` (via React Router's Link) styled identically to Button —
 * use this instead of wrapping a <Button> inside a <Link>. Nesting a real
 * <button> inside an <a> is invalid HTML5 (interactive content inside
 * interactive content) and produces unpredictable keyboard/screen-reader
 * behavior — this component exists specifically so that pattern never
 * needs to happen.
 */
export const LinkButton = forwardRef<HTMLAnchorElement, LinkButtonProps>(
  ({ variant = 'primary', size = 'md', className, children, ...props }, ref) => {
    return (
      <Link ref={ref} className={buttonClassNames({ variant, size, className })} {...props}>
        {children}
      </Link>
    )
  },
)
LinkButton.displayName = 'LinkButton'
