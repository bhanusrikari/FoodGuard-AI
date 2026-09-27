import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import Login from './Login'
import { LanguageProvider } from '@/i18n/LanguageContext'
import { createTestQueryClient } from '@/test/testUtils'

const mockLogin = vi.fn()
const mockNavigate = vi.fn()

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    isLoading: false,
    isAuthenticated: false,
    login: mockLogin,
    register: vi.fn(),
    logout: vi.fn(),
  }),
}))
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

function renderLogin() {
  const queryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/login']}>
        <LanguageProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
          </Routes>
        </LanguageProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Login', () => {
  beforeEach(() => {
    mockLogin.mockReset()
    mockNavigate.mockReset()
  })

  it('renders email and password fields and a submit button', () => {
    renderLogin()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('redirects a CUSTOMER to /dashboard after a successful login', async () => {
    mockLogin.mockResolvedValue({ role: 'CUSTOMER' })
    renderLogin()
    await userEvent.type(screen.getByLabelText(/email/i), 'customer@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'StrongPass99')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true }))
  })

  it('redirects an ADMIN to /admin after a successful login', async () => {
    mockLogin.mockResolvedValue({ role: 'ADMIN' })
    renderLogin()
    await userEvent.type(screen.getByLabelText(/email/i), 'admin@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'StrongPass99')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/admin', { replace: true }))
  })

  it('redirects a REVIEWER to /reviewer (not /admin) after a successful login', async () => {
    mockLogin.mockResolvedValue({ role: 'REVIEWER' })
    renderLogin()
    await userEvent.type(screen.getByLabelText(/email/i), 'reviewer@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'StrongPass99')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/reviewer', { replace: true }))
  })

  it('shows the API error message and does not navigate on failed login', async () => {
    mockLogin.mockRejectedValue({ response: { data: { detail: 'Invalid credentials.' } } })
    renderLogin()
    await userEvent.type(screen.getByLabelText(/email/i), 'wrong@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'wrongpass')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('does not call login when the form is submitted empty (client-side validation)', async () => {
    renderLogin()
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => expect(mockLogin).not.toHaveBeenCalled())
  })
})
