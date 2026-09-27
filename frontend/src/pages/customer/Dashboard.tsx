import { Link } from 'react-router-dom'
import { FileText, MessageSquare, Plus, ShieldAlert, CheckCircle2, Store, Sparkles, ArrowRight } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { StatCard } from '@/components/dashboard/StatCard'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { ReportCard } from '@/components/reports/ReportCard'
import { ComplaintCard } from '@/components/complaints/ComplaintCard'
import { EmptyState } from '@/components/states/EmptyState'
import { ErrorState } from '@/components/states/ErrorState'
import { ListSkeleton } from '@/components/states/LoadingSkeleton'
import { LinkButton } from '@/components/ui/LinkButton'
import { Reveal } from '@/components/motion/Reveal'
import { useAuth } from '@/context/AuthContext'
import { useReports } from '@/hooks/useReports'
import { useComplaints } from '@/hooks/useComplaints'
import { useRestaurants } from '@/hooks/useRestaurants'

export default function Dashboard() {
  const { user } = useAuth()
  const reportsQuery = useReports()
  const complaintsQuery = useComplaints()
  const restaurantsQuery = useRestaurants()

  const reports = reportsQuery.data ?? []
  const complaints = complaintsQuery.data ?? []
  const activeRestaurantCount = (restaurantsQuery.data ?? []).length

  const openReports = reports.filter((r) => r.status === 'SUBMITTED' || r.status === 'UNDER_REVIEW').length
  const resolvedReports = reports.filter((r) => r.status === 'RESOLVED' || r.status === 'CLOSED').length
  const openComplaints = complaints.filter((c) => c.status === 'SUBMITTED' || c.status === 'UNDER_REVIEW').length

  return (
    <AppShell title="Dashboard">
      {/* Welcome hero */}
      <Reveal
        variant="fade"
        className="relative mb-8 overflow-hidden rounded-2xl bg-primary-900 px-6 py-8 shadow-popover sm:px-8"
      >
        <div className="pointer-events-none absolute -right-10 -top-10 size-48 rounded-full bg-primary-500/20 blur-3xl animate-float" />
        <div className="relative flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-2xl font-semibold text-white">Welcome back, {user?.first_name}</h2>
            <p className="mt-1.5 text-sm text-white/70">
              Here's what's happening with your reports and complaints.
            </p>
          </div>
          <LinkButton to="/reports/new" size="lg">
            <Plus className="size-4" aria-hidden="true" />
            New Report
          </LinkButton>
        </div>
      </Reveal>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: 'Total reports', value: reports.length, icon: FileText, tone: 'primary' as const },
          { label: 'Awaiting review', value: openReports, icon: ShieldAlert, tone: 'warning' as const },
          { label: 'Resolved reports', value: resolvedReports, icon: CheckCircle2, tone: 'success' as const },
          { label: 'Open complaints', value: openComplaints, icon: MessageSquare, tone: 'danger' as const },
        ].map((stat, i) => (
          <Reveal key={stat.label} delay={i * 70}>
            <StatCard {...stat} />
          </Reveal>
        ))}
      </div>

      {/* Recent activity */}
      <div className="mt-10 grid grid-cols-1 gap-8 lg:grid-cols-2">
        <div>
          <SectionHeader
            title="Recent reports"
            action={
              <Link to="/reports" className="text-sm font-medium text-primary-700 hover:underline">
                View all
              </Link>
            }
          />
          {reportsQuery.isLoading && <ListSkeleton items={3} />}
          {reportsQuery.isError && <ErrorState onRetry={() => reportsQuery.refetch()} />}
          {reportsQuery.isSuccess && reports.length === 0 && (
            <EmptyState
              icon={<FileText className="size-6" aria-hidden="true" />}
              title="No food safety reports yet"
              description="If you've experienced a food safety concern, you can report it here."
              action={<LinkButton to="/reports/new" size="sm">Create Report</LinkButton>}
            />
          )}
          {reportsQuery.isSuccess && reports.length > 0 && (
            <div className="space-y-3">
              {reports.slice(0, 4).map((report, i) => (
                <Reveal key={report.id} delay={i * 60}>
                  <ReportCard report={report} />
                </Reveal>
              ))}
            </div>
          )}
        </div>

        <div>
          <SectionHeader
            title="Recent complaints"
            action={
              <Link to="/complaints" className="text-sm font-medium text-primary-700 hover:underline">
                View all
              </Link>
            }
          />
          {complaintsQuery.isLoading && <ListSkeleton items={3} />}
          {complaintsQuery.isError && <ErrorState onRetry={() => complaintsQuery.refetch()} />}
          {complaintsQuery.isSuccess && complaints.length === 0 && (
            <EmptyState
              icon={<MessageSquare className="size-6" aria-hidden="true" />}
              title="No complaints filed yet"
              description="Complaints can be filed once a report has been submitted for review."
            />
          )}
          {complaintsQuery.isSuccess && complaints.length > 0 && (
            <div className="space-y-3">
              {complaints.slice(0, 4).map((complaint, i) => (
                <Reveal key={complaint.id} delay={i * 60}>
                  <ComplaintCard complaint={complaint} />
                </Reveal>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Explore + AI insights */}
      <div className="mt-10 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Reveal>
          <div className="group relative overflow-hidden rounded-2xl border border-neutral-100 bg-white p-6 shadow-card transition-all duration-300 hover:-translate-y-0.5 hover:shadow-card-hover">
            <div className="pointer-events-none absolute -right-8 -top-8 size-32 rounded-full bg-primary-50 opacity-70 transition-opacity duration-300 group-hover:opacity-100" />
            <div className="relative flex items-center gap-3">
              <div className="flex size-11 items-center justify-center rounded-xl bg-primary-50 text-primary-700">
                <Store className="size-5" aria-hidden="true" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-neutral-900">Discover restaurants</h3>
                <p className="text-sm text-neutral-500">
                  {restaurantsQuery.isLoading
                    ? 'Loading network…'
                    : `${activeRestaurantCount} active restaurant${activeRestaurantCount === 1 ? '' : 's'} on FoodGuard`}
                </p>
              </div>
            </div>
            <Link
              to="/reports/new"
              className="relative mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary-700 transition-transform duration-200 hover:translate-x-1"
            >
              File a report against one
              <ArrowRight className="size-3.5" aria-hidden="true" />
            </Link>
          </div>
        </Reveal>

        <Reveal delay={80}>
          <div className="rounded-2xl border border-info-100 bg-info-50 p-6">
            <div className="flex items-center gap-3">
              <div className="flex size-11 items-center justify-center rounded-xl bg-white text-info-600">
                <Sparkles className="size-5" aria-hidden="true" />
              </div>
              <h3 className="text-base font-semibold text-neutral-900">AI-assisted insight</h3>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-neutral-600">
              Every submitted report can get a preliminary AI visual read — a fast, transparent first look
              at possible concerns. It's a preliminary assessment, not a food-safety certification; a human
              reviewer always has the final say.
            </p>
          </div>
        </Reveal>
      </div>
    </AppShell>
  )
}
