import { NavLink } from 'react-router-dom'
import { X } from 'lucide-react'
import { cn } from '@/lib/cn'
import { useTranslation } from '@/i18n/LanguageContext'
import { BRAND, getNavItems } from './navConfig'
import type { UserRole } from '@/types/user'

interface MobileNavProps {
  role: UserRole
  open: boolean
  onClose: () => void
}

export function MobileNav({ role, open, onClose }: MobileNavProps) {
  const items = getNavItems(role)
  const t = useTranslation()

  if (!open) return null

  return (
    <div className="fixed inset-0 z-40 lg:hidden">
      <div className="absolute inset-0 bg-neutral-900/40" onClick={onClose} aria-hidden="true" />
      <div className="absolute inset-y-0 left-0 flex w-72 max-w-[80%] flex-col bg-white shadow-popover animate-fade-in">
        <div className="flex h-16 items-center justify-between border-b border-neutral-100 px-5">
          <div className="flex items-center gap-2">
            <BRAND.icon className="size-6 text-primary-700" aria-hidden="true" />
            <span className="text-base font-semibold text-neutral-900">{BRAND.name}</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={t('topbar.closeMenu')}
            className="rounded-md p-1.5 text-neutral-400 hover:bg-neutral-100"
          >
            <X className="size-5" aria-hidden="true" />
          </button>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4" aria-label="Primary">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-200',
                  isActive ? 'bg-primary-50 text-primary-800' : 'text-neutral-600 hover:bg-neutral-50',
                )
              }
            >
              <item.icon className="size-4.5 shrink-0" aria-hidden="true" />
              {t(item.labelKey)}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  )
}
