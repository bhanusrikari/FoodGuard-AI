import type { LucideIcon } from 'lucide-react'
import { BarChart3, Building2, FileText, LayoutDashboard, MessageSquare, ShieldCheck, User } from 'lucide-react'
import type { TranslationKey } from '@/i18n/en'
import type { UserRole } from '@/types/user'

export interface NavItem {
  labelKey: TranslationKey
  to: string
  icon: LucideIcon
  end?: boolean
}

const CUSTOMER_NAV: NavItem[] = [
  { labelKey: 'nav.dashboard', to: '/dashboard', icon: LayoutDashboard, end: true },
  { labelKey: 'nav.reports', to: '/reports', icon: FileText },
  { labelKey: 'nav.complaints', to: '/complaints', icon: MessageSquare },
  { labelKey: 'nav.profile', to: '/profile', icon: User },
]

const RESTAURANT_NAV: NavItem[] = [
  { labelKey: 'nav.myRestaurants', to: '/restaurant', icon: Building2, end: true },
  { labelKey: 'nav.profile', to: '/profile', icon: User },
]

const REVIEWER_NAV: NavItem[] = [
  { labelKey: 'nav.dashboard', to: '/reviewer', icon: LayoutDashboard, end: true },
  { labelKey: 'nav.reports', to: '/reviewer/reports', icon: FileText },
  { labelKey: 'nav.complaints', to: '/reviewer/complaints', icon: MessageSquare },
  { labelKey: 'nav.restaurants', to: '/reviewer/restaurants', icon: Building2 },
  { labelKey: 'nav.profile', to: '/profile', icon: User },
]

// Admin gets its own platform-level dashboard, but keeps access to the same
// underlying reports/complaints/restaurants management pages reviewers use
// (those routes already allow ADMIN via RoleGuard) — a distinct landing
// experience, not a duplicated set of CRUD pages.
const ADMIN_NAV: NavItem[] = [
  { labelKey: 'nav.dashboard', to: '/admin', icon: BarChart3, end: true },
  { labelKey: 'nav.reports', to: '/reviewer/reports', icon: FileText },
  { labelKey: 'nav.complaints', to: '/reviewer/complaints', icon: MessageSquare },
  { labelKey: 'nav.restaurants', to: '/reviewer/restaurants', icon: Building2 },
  { labelKey: 'nav.profile', to: '/profile', icon: User },
]

export function getNavItems(role: UserRole): NavItem[] {
  switch (role) {
    case 'CUSTOMER':
      return CUSTOMER_NAV
    case 'RESTAURANT_USER':
      return RESTAURANT_NAV
    case 'REVIEWER':
      return REVIEWER_NAV
    case 'ADMIN':
      return ADMIN_NAV
    default:
      return []
  }
}

export const BRAND = { name: 'FoodGuard AI', icon: ShieldCheck }
