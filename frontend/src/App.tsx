import { Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { RoleGuard } from '@/components/auth/RoleGuard'
import { GuestRoute } from '@/components/auth/GuestRoute'

import Landing from '@/pages/Landing'
import Login from '@/pages/Login'
import Register from '@/pages/Register'
import Profile from '@/pages/Profile'
import NotFound from '@/pages/NotFound'

import Dashboard from '@/pages/customer/Dashboard'
import ReportsList from '@/pages/customer/ReportsList'
import ReportCreate from '@/pages/customer/ReportCreate'
import ReportEdit from '@/pages/customer/ReportEdit'
import ReportDetail from '@/pages/customer/ReportDetail'
import ReportAIAnalysis from '@/pages/customer/ReportAIAnalysis'
import ComplaintsList from '@/pages/customer/ComplaintsList'
import ComplaintCreate from '@/pages/customer/ComplaintCreate'
import ComplaintDetail from '@/pages/customer/ComplaintDetail'

import RestaurantDashboard from '@/pages/restaurant/RestaurantDashboard'
import RestaurantCreate from '@/pages/restaurant/RestaurantCreate'
import RestaurantEdit from '@/pages/restaurant/RestaurantEdit'

import ReviewerDashboard from '@/pages/reviewer/ReviewerDashboard'
import ReviewerReportsList from '@/pages/reviewer/ReviewerReportsList'
import ReviewerReportDetail from '@/pages/reviewer/ReviewerReportDetail'
import ReviewerComplaintsList from '@/pages/reviewer/ReviewerComplaintsList'
import ReviewerComplaintDetail from '@/pages/reviewer/ReviewerComplaintDetail'
import ReviewerRestaurants from '@/pages/reviewer/ReviewerRestaurants'

import AdminDashboard from '@/pages/admin/AdminDashboard'

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<Landing />} />
      <Route
        path="/login"
        element={
          <GuestRoute>
            <Login />
          </GuestRoute>
        }
      />
      <Route
        path="/register"
        element={
          <GuestRoute>
            <Register />
          </GuestRoute>
        }
      />

      {/* Shared authenticated */}
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        }
      />

      {/* Customer */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['CUSTOMER']}>
              <Dashboard />
            </RoleGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['CUSTOMER']}>
              <ReportsList />
            </RoleGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports/new"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['CUSTOMER']}>
              <ReportCreate />
            </RoleGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports/:id"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['CUSTOMER']}>
              <ReportDetail />
            </RoleGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports/:id/edit"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['CUSTOMER']}>
              <ReportEdit />
            </RoleGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports/:id/ai-analysis"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['CUSTOMER']}>
              <ReportAIAnalysis />
            </RoleGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/complaints"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['CUSTOMER']}>
              <ComplaintsList />
            </RoleGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/complaints/new"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['CUSTOMER']}>
              <ComplaintCreate />
            </RoleGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/complaints/:id"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['CUSTOMER']}>
              <ComplaintDetail />
            </RoleGuard>
          </ProtectedRoute>
        }
      />

      {/* Restaurant user */}
      <Route
        path="/restaurant"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['RESTAURANT_USER']}>
              <RestaurantDashboard />
            </RoleGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/restaurant/new"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['RESTAURANT_USER']}>
              <RestaurantCreate />
            </RoleGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/restaurant/:id/edit"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['RESTAURANT_USER']}>
              <RestaurantEdit />
            </RoleGuard>
          </ProtectedRoute>
        }
      />

      {/* Reviewer / Admin */}
      <Route
        path="/reviewer"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['REVIEWER', 'ADMIN']}>
              <ReviewerDashboard />
            </RoleGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reviewer/reports"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['REVIEWER', 'ADMIN']}>
              <ReviewerReportsList />
            </RoleGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reviewer/reports/:id"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['REVIEWER', 'ADMIN']}>
              <ReviewerReportDetail />
            </RoleGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reviewer/complaints"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['REVIEWER', 'ADMIN']}>
              <ReviewerComplaintsList />
            </RoleGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reviewer/complaints/:id"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['REVIEWER', 'ADMIN']}>
              <ReviewerComplaintDetail />
            </RoleGuard>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reviewer/restaurants"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['REVIEWER', 'ADMIN']}>
              <ReviewerRestaurants />
            </RoleGuard>
          </ProtectedRoute>
        }
      />

      {/* Admin — platform-level dashboard; reuses reviewer routes above for
          reports/complaints/restaurants management (those already allow
          ADMIN via RoleGuard), so nothing there needed to change. */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <RoleGuard allow={['ADMIN']}>
              <AdminDashboard />
            </RoleGuard>
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
