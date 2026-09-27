import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import ReportsList from './ReportsList'
import { LanguageProvider } from '@/i18n/LanguageContext'
import { createTestQueryClient } from '@/test/testUtils'
import type { FoodReport } from '@/types/report'

const mockUseReports = vi.fn()

const FAKE_USER = {
  id: 1,
  email: 'c@example.com',
  first_name: 'Test',
  last_name: 'Customer',
  phone: '',
  role: 'CUSTOMER' as const,
  preferred_language: 'en' as const,
  is_active: true,
  date_joined: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: FAKE_USER,
    isLoading: false,
    isAuthenticated: true,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
}))
vi.mock('@/hooks/useReports', () => ({
  useReports: () => mockUseReports(),
}))

function fakeReport(id: number, title: string): FoodReport {
  return {
    id,
    customer: { id: 1, email: 'c@example.com', first_name: 'C', last_name: 'User' },
    restaurant: { id: 1, name: 'Test Diner', city: 'Testville', state: 'Teststate' },
    title,
    description: 'x',
    image: null,
    status: 'DRAFT',
    priority: 'LOW',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

function renderList() {
  const queryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/reports']}>
        <LanguageProvider>
          <ReportsList />
        </LanguageProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ReportsList — UI states', () => {
  it('shows a loading skeleton while fetching', () => {
    mockUseReports.mockReturnValue({ data: undefined, isLoading: true, isError: false, isSuccess: false, refetch: vi.fn() })
    const { container } = renderList()
    expect(container.querySelector('.animate-skeleton')).not.toBeNull()
  })

  it('shows an error state with a working retry button', async () => {
    const refetch = vi.fn()
    mockUseReports.mockReturnValue({ data: undefined, isLoading: false, isError: true, isSuccess: false, refetch })
    renderList()
    expect(screen.getByText("We couldn't load your reports.")).toBeInTheDocument()
    const { default: userEvent } = await import('@testing-library/user-event')
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(refetch).toHaveBeenCalled()
  })

  it('shows an empty state with a create-report action when there are zero reports', () => {
    mockUseReports.mockReturnValue({ data: [], isLoading: false, isError: false, isSuccess: true, refetch: vi.fn() })
    renderList()
    expect(screen.getByText('No food safety reports yet')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /create report/i })).toBeInTheDocument()
  })

  it('renders a card for every report when data is present', () => {
    mockUseReports.mockReturnValue({
      data: [fakeReport(1, 'Cold biryani'), fakeReport(2, 'Stale bread')],
      isLoading: false,
      isError: false,
      isSuccess: true,
      refetch: vi.fn(),
    })
    renderList()
    expect(screen.getByText('Cold biryani')).toBeInTheDocument()
    expect(screen.getByText('Stale bread')).toBeInTheDocument()
  })

  it('shows a distinct empty state when a filter matches nothing, not the zero-reports empty state', async () => {
    mockUseReports.mockReturnValue({
      data: [fakeReport(1, 'Cold biryani')],
      isLoading: false,
      isError: false,
      isSuccess: true,
      refetch: vi.fn(),
    })
    renderList()
    const { default: userEvent } = await import('@testing-library/user-event')
    await userEvent.selectOptions(screen.getByLabelText(/filter by status/i), 'RESOLVED')
    expect(screen.getByText('No reports match this filter')).toBeInTheDocument()
    expect(screen.queryByText('No food safety reports yet')).not.toBeInTheDocument()
  })
})
