import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import ReportDetail from './ReportDetail'
import { createTestQueryClient } from '@/test/testUtils'
import { LanguageProvider } from '@/i18n/LanguageContext'
import type { FoodReport, ReportStatus } from '@/types/report'

const mockUseReport = vi.fn()
const mockDeleteMutateAsync = vi.fn()
const mockSubmitMutateAsync = vi.fn()
const mockNavigate = vi.fn()

const FAKE_CUSTOMER = {
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
    user: FAKE_CUSTOMER,
    isLoading: false,
    isAuthenticated: true,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
}))
vi.mock('@/hooks/useReports', () => ({
  useReport: (id: number) => mockUseReport(id),
  useDeleteReport: () => ({ mutateAsync: mockDeleteMutateAsync, isPending: false }),
  useSubmitReport: () => ({ mutateAsync: mockSubmitMutateAsync, isPending: false }),
}))
vi.mock('@/hooks/useAIAnalysis', () => ({
  useAIAnalysis: () => ({ isLoading: false, isSuccess: false, isError: true, error: { response: { status: 404 } } }),
  useRunAIAnalysis: () => ({ isPending: false, mutate: vi.fn() }),
}))
vi.mock('@/hooks/useComplaints', () => ({
  useComplaints: () => ({ data: [] }),
}))
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

function fakeReport(status: ReportStatus): FoodReport {
  return {
    id: 42,
    customer: { id: 1, email: 'c@example.com', first_name: 'C', last_name: 'User' },
    restaurant: { id: 1, name: 'Test Diner', city: 'Testville', state: 'Teststate' },
    title: 'Cold biryani',
    description: 'It was cold.',
    image: null,
    status,
    priority: 'LOW',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

function renderReportDetail() {
  const queryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/reports/42']}>
        <LanguageProvider>
          <Routes>
            <Route path="/reports/:id" element={<ReportDetail />} />
          </Routes>
        </LanguageProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ReportDetail — delete-draft UX', () => {
  beforeEach(() => {
    mockDeleteMutateAsync.mockReset().mockResolvedValue(undefined)
    mockSubmitMutateAsync.mockReset()
    mockNavigate.mockReset()
  })

  it('shows the Delete button for a DRAFT report', () => {
    mockUseReport.mockReturnValue({ data: fakeReport('DRAFT'), isLoading: false, isError: false, refetch: vi.fn() })
    renderReportDetail()
    expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument()
  })

  it('never shows the Delete button for a SUBMITTED report (immutable state)', () => {
    mockUseReport.mockReturnValue({ data: fakeReport('SUBMITTED'), isLoading: false, isError: false, refetch: vi.fn() })
    renderReportDetail()
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument()
  })

  it('never shows the Delete button for an UNDER_REVIEW report', () => {
    mockUseReport.mockReturnValue({ data: fakeReport('UNDER_REVIEW'), isLoading: false, isError: false, refetch: vi.fn() })
    renderReportDetail()
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument()
  })

  it('opens a confirmation dialog instead of deleting immediately', async () => {
    mockUseReport.mockReturnValue({ data: fakeReport('DRAFT'), isLoading: false, isError: false, refetch: vi.fn() })
    renderReportDetail()
    await userEvent.click(screen.getByRole('button', { name: /delete/i }))
    expect(await screen.findByText('Delete this draft report?')).toBeInTheDocument()
    expect(mockDeleteMutateAsync).not.toHaveBeenCalled()
  })

  it('cancelling the dialog does not delete', async () => {
    mockUseReport.mockReturnValue({ data: fakeReport('DRAFT'), isLoading: false, isError: false, refetch: vi.fn() })
    renderReportDetail()
    await userEvent.click(screen.getByRole('button', { name: /delete/i }))
    await screen.findByText('Delete this draft report?')
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(mockDeleteMutateAsync).not.toHaveBeenCalled()
    // Modal.tsx keeps its content mounted and toggles the native <dialog>
    // open/close instead of unmounting — assert on that, not DOM presence.
    expect(document.querySelector('dialog')).not.toHaveAttribute('open')
  })

  it('confirming deletes and navigates away on success', async () => {
    mockUseReport.mockReturnValue({ data: fakeReport('DRAFT'), isLoading: false, isError: false, refetch: vi.fn() })
    renderReportDetail()
    await userEvent.click(screen.getByRole('button', { name: /delete/i }))
    await screen.findByText('Delete this draft report?')
    // Two buttons named "Delete" now exist (page action + dialog confirm) —
    // the dialog's confirm button is the last one rendered.
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
    await userEvent.click(deleteButtons[deleteButtons.length - 1])
    await waitFor(() => expect(mockDeleteMutateAsync).toHaveBeenCalledWith(42))
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/reports', { replace: true }))
  })

  it('shows an error and keeps the dialog state sane when deletion fails', async () => {
    mockDeleteMutateAsync.mockRejectedValueOnce({ response: { data: { detail: 'Cannot delete.' } } })
    mockUseReport.mockReturnValue({ data: fakeReport('DRAFT'), isLoading: false, isError: false, refetch: vi.fn() })
    renderReportDetail()
    await userEvent.click(screen.getByRole('button', { name: /delete/i }))
    await screen.findByText('Delete this draft report?')
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
    await userEvent.click(deleteButtons[deleteButtons.length - 1])
    await waitFor(() => expect(mockDeleteMutateAsync).toHaveBeenCalled())
    expect(mockNavigate).not.toHaveBeenCalled()
    await waitFor(() => expect(document.querySelector('dialog')).not.toHaveAttribute('open'))
  })

  it('shows a loading skeleton while the report is loading', () => {
    mockUseReport.mockReturnValue({ data: undefined, isLoading: true, isError: false, refetch: vi.fn() })
    const { container } = renderReportDetail()
    expect(container.querySelector('.animate-skeleton')).not.toBeNull()
  })

  it('shows an error state with retry when the report fails to load', async () => {
    const refetch = vi.fn()
    mockUseReport.mockReturnValue({ data: undefined, isLoading: false, isError: true, refetch })
    renderReportDetail()
    expect(screen.getByText("We couldn't load this report.")).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(refetch).toHaveBeenCalled()
  })
})
