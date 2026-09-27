import type { UserRole } from '@/types/user'

export function defaultRouteForRole(role: UserRole): string {
  switch (role) {
    case 'CUSTOMER':
      return '/dashboard'
    case 'RESTAURANT_USER':
      return '/restaurant'
    case 'REVIEWER':
      return '/reviewer'
    case 'ADMIN':
      return '/admin'
    default:
      return '/'
  }
}
