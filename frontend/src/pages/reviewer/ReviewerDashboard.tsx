import { Link } from 'react-router-dom'
import { Building2, FileText, MessageSquare, ShieldAlert } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { StatCard } from '@/components/dashboard/StatCard'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { ReportTable } from '@/components/reports/ReportTable'
import { ComplaintTable } from '@/components/complaints/ComplaintTable'
import { ErrorState } from '@/components/states/ErrorState'
import { TableSkeleton } from '@/components/states/LoadingSkeleton'
import { EmptyState } from '@/components/states/EmptyState'
import { Reveal } from '@/components/motion/Reveal'
import { useReports } from '@/hooks/useReports'
import { useComplaints } from '@/hooks/useComplaints'
import { useRestaurants } from '@/hooks/useRestaurants'
import { useTranslation } from '@/i18n/LanguageContext'

export default function ReviewerDashboard() {
  const t = useTranslation()
  const reportsQuery = useReports()
  const complaintsQuery = useComplaints()
  const restaurantsQuery = useRestaurants()

  const reports = reportsQuery.data ?? []
  const complaints = complaintsQuery.data ?? []
  const restaurants = restaurantsQuery.data ?? []

  const reportsNeedingAttention = reports.filter((r) => r.status === 'SUBMITTED' || r.status === 'UNDER_REVIEW')
  const complaintsNeedingAttention = complaints.filter((c) => c.status === 'SUBMITTED' || c.status === 'UNDER_REVIEW')
  const pendingVerification = restaurants.filter((r) => !r.is_verified)

  return (
    <AppShell title="Reviewer Dashboard">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-neutral-900">{t('dashboard.reviewer.heading')}</h2>
        <p className="mt-1 text-sm text-neutral-500">{t('dashboard.reviewer.subtitle')}</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: 'Reports needing attention', value: reportsNeedingAttention.length, icon: ShieldAlert, tone: 'warning' as const },
          { label: 'Total reports', value: reports.length, icon: FileText, tone: 'primary' as const },
          { label: 'Complaints needing attention', value: complaintsNeedingAttention.length, icon: MessageSquare, tone: 'danger' as const },
          { label: 'Pending verification', value: pendingVerification.length, icon: Building2, tone: 'neutral' as const },
        ].map((stat, i) => (
          <Reveal key={stat.label} delay={i * 70}>
            <StatCard {...stat} />
          </Reveal>
        ))}
      </div>

      <div className="mt-10">
        <SectionHeader
          title="Reports needing attention"
          action={
            <Link to="/reviewer/reports" className="text-sm font-medium text-primary-700 hover:underline">
              View all
            </Link>
          }
        />
        {reportsQuery.isLoading && <TableSkeleton rows={4} />}
        {reportsQuery.isError && <ErrorState onRetry={() => reportsQuery.refetch()} />}
        {reportsQuery.isSuccess && reportsNeedingAttention.length === 0 && (
          <EmptyState title="Nothing needs attention" description="All reports have been reviewed or resolved." />
        )}
        {reportsNeedingAttention.length > 0 && <ReportTable reports={reportsNeedingAttention.slice(0, 6)} showCustomer />}
      </div>

      <div className="mt-10">
        <SectionHeader
          title="Complaints needing attention"
          action={
            <Link to="/reviewer/complaints" className="text-sm font-medium text-primary-700 hover:underline">
              View all
            </Link>
          }
        />
        {complaintsQuery.isLoading && <TableSkeleton rows={4} />}
        {complaintsQuery.isError && <ErrorState onRetry={() => complaintsQuery.refetch()} />}
        {complaintsQuery.isSuccess && complaintsNeedingAttention.length === 0 && (
          <EmptyState title="Nothing needs attention" description="All complaints have been reviewed or resolved." />
        )}
        {complaintsNeedingAttention.length > 0 && (
          <ComplaintTable complaints={complaintsNeedingAttention.slice(0, 6)} showCustomer />
        )}
      </div>
    </AppShell>
  )
}
