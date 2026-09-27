import { screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { RoleGuard } from './RoleGuard'
import { createTestQueryClient } from '@/test/testUtils'
import type { User, UserRole } from '@/types/user'

const mockUseAuth = vi.fn()
vi.mock('@/context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

function fakeUser(role: UserRole): User {
  return {
    id: 1,
    email: 'x@example.com',
    first_name: 'Test',
    last_name: 'User',
    phone: '',
    role,
    preferred_language: 'en',
    is_active: true,
    date_joined: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

function renderGuardedRoutes(allow: UserRole[]) {
  const queryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/guarded']}>
        <Routes>
          <Route
            path="/guarded"
            element={
              <RoleGuard allow={allow}>
                <div>Guarded content</div>
              </RoleGuard>
            }
          />
          <Route path="/dashboard" element={<div>Customer dashboard</div>} />
          <Route path="/admin" element={<div>Admin dashboard</div>} />
          <Route path="/reviewer" element={<div>Reviewer dashboard</div>} />
          <Route path="/restaurant" element={<div>Restaurant dashboard</div>} />
          <Route path="/login" element={<div>Login page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('RoleGuard', () => {
  it('redirects to /login when there is no user at all', () => {
    mockUseAuth.mockReturnValue({ user: null })
    renderGuardedRoutes(['ADMIN'])
    expect(screen.getByText('Login page')).toBeInTheDocument()
  })

  it('renders children when the role is allowed', () => {
    mockUseAuth.mockReturnValue({ user: fakeUser('ADMIN') })
    renderGuardedRoutes(['ADMIN'])
    expect(screen.getByText('Guarded content')).toBeInTheDocument()
  })

  it('redirects an ADMIN to /admin, never to /reviewer, when the route does not allow ADMIN', () => {
    mockUseAuth.mockReturnValue({ user: fakeUser('ADMIN') })
    renderGuardedRoutes(['CUSTOMER'])
    expect(screen.getByText('Admin dashboard')).toBeInTheDocument()
    expect(screen.queryByText('Reviewer dashboard')).not.toBeInTheDocument()
  })

  it('redirects a CUSTOMER to /dashboard when the route does not allow CUSTOMER', () => {
    mockUseAuth.mockReturnValue({ user: fakeUser('CUSTOMER') })
    renderGuardedRoutes(['ADMIN'])
    expect(screen.getByText('Customer dashboard')).toBeInTheDocument()
  })

  it('redirects a RESTAURANT_USER to /restaurant when the route does not allow it', () => {
    mockUseAuth.mockReturnValue({ user: fakeUser('RESTAURANT_USER') })
    renderGuardedRoutes(['REVIEWER', 'ADMIN'])
    expect(screen.getByText('Restaurant dashboard')).toBeInTheDocument()
  })

  it('allows a REVIEWER through a route shared with ADMIN', () => {
    mockUseAuth.mockReturnValue({ user: fakeUser('REVIEWER') })
    renderGuardedRoutes(['REVIEWER', 'ADMIN'])
    expect(screen.getByText('Guarded content')).toBeInTheDocument()
  })

  it('does NOT allow a REVIEWER through an ADMIN-only route (e.g. /admin itself)', () => {
    mockUseAuth.mockReturnValue({ user: fakeUser('REVIEWER') })
    renderGuardedRoutes(['ADMIN'])
    expect(screen.getByText('Reviewer dashboard')).toBeInTheDocument()
    expect(screen.queryByText('Guarded content')).not.toBeInTheDocument()
  })
})
