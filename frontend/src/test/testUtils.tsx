import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'
import { LanguageProvider } from '@/i18n/LanguageContext'

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

/** Renders with the real QueryClientProvider/AuthProvider/LanguageProvider
 * stack, inside a MemoryRouter. Tests that need a specific auth state
 * mock @/lib/tokenStorage + @/api/auth (see e.g. RoleGuard.test.tsx) so
 * AuthProvider's own hydrate effect populates a realistic user. */
export function renderWithProviders(
  ui: ReactElement,
  { route = '/', queryClient = createTestQueryClient() }: { route?: string; queryClient?: QueryClient } = {},
) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <AuthProvider>
          <LanguageProvider>{ui}</LanguageProvider>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
