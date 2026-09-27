import { useNavigate } from 'react-router-dom'
import { LogOut, Menu, User as UserIcon } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { Dropdown } from '@/components/ui/Dropdown'
import { RoleBadge } from '@/components/badges/RoleBadge'
import { initials } from '@/lib/format'
import { LanguageSelector } from './LanguageSelector'
import { useTranslation } from '@/i18n/LanguageContext'

export function Topbar({ title, onMenuClick }: { title: string; onMenuClick: () => void }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const t = useTranslation()

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  if (!user) return null

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-neutral-100 bg-white/95 px-4 backdrop-blur sm:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          className="rounded-md p-2 text-neutral-500 hover:bg-neutral-100 lg:hidden"
          aria-label={t('topbar.openMenu')}
        >
          <Menu className="size-5" aria-hidden="true" />
        </button>
        <h1 className="text-base font-semibold text-neutral-900 sm:text-lg">{title}</h1>
      </div>

      <div className="flex items-center gap-1">
        <LanguageSelector />

        <Dropdown
          align="right"
          trigger={
            <span className="flex items-center gap-2.5 rounded-full py-1 pl-1 pr-3 hover:bg-neutral-50">
              <span className="flex size-8 items-center justify-center rounded-full bg-primary-700 text-xs font-semibold text-white">
                {initials(user.first_name, user.last_name)}
              </span>
              <span className="hidden flex-col items-start sm:flex">
                <span className="text-sm font-medium leading-tight text-neutral-900">
                  {user.first_name} {user.last_name}
                </span>
                <RoleBadge role={user.role} className="mt-0.5" />
              </span>
            </span>
          }
          items={[
            { label: t('nav.profile'), icon: <UserIcon className="size-4" />, onSelect: () => navigate('/profile') },
            { label: t('common.logOut'), icon: <LogOut className="size-4" />, danger: true, onSelect: handleLogout },
          ]}
        />
      </div>
    </header>
  )
}
