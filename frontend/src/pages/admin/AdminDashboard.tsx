import { Building2, FileText, MessageSquare, ShieldAlert } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { StatCard } from '@/components/dashboard/StatCard'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { ErrorState } from '@/components/states/ErrorState'
import { EmptyState } from '@/components/states/EmptyState'
import { Reveal } from '@/components/motion/Reveal'
import { useAnalyticsSummary } from '@/hooks/useAnalytics'
import { useTranslation } from '@/i18n/LanguageContext'

/** Renders a label -> count breakdown from a real API aggregation object.
 * Shows an honest empty state when the backend returns no rows for that
 * breakdown — never a fabricated placeholder value. */
function BreakdownCard({ title, counts }: { title: string; counts: Record<string, number> }) {
  const t = useTranslation()
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1])
  const total = entries.reduce((sum, [, count]) => sum + count, 0)

  return (
    <div className="rounded-2xl border border-neutral-100 bg-white p-5 shadow-card">
      <h3 className="text-sm font-semibold text-neutral-900">{title}</h3>
      {entries.length === 0 ? (
        <p className="mt-3 text-sm text-neutral-400">{t('dashboard.admin.noData')}</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {entries.map(([label, count]) => (
            <li key={label} className="flex items-center gap-3">
              <span className="w-32 shrink-0 truncate text-xs font-medium text-neutral-600">
                {label.replaceAll('_', ' ')}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-neutral-100">
                <div
                  className="h-full rounded-full bg-primary-500"
                  style={{ width: total > 0 ? `${(count / total) * 100}%` : '0%' }}
                />
              </div>
              <span className="w-8 shrink-0 text-right text-xs font-semibold text-neutral-900">{count}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function AdminDashboard() {
  const { data, isLoading, isError, refetch } = useAnalyticsSummary()
  const t = useTranslation()

  return (
    <AppShell title="Admin Dashboard">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-neutral-900">{t('dashboard.admin.heading')}</h2>
        <p className="mt-1 text-sm text-neutral-500">{t('dashboard.admin.subtitle')}</p>
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-2xl bg-neutral-100" />
          ))}
        </div>
      )}

      {isError && <ErrorState message={t('dashboard.admin.loadError')} onRetry={() => refetch()} />}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: 'Total reports', value: data.reports.total, icon: FileText, tone: 'primary' as const },
              { label: 'Total complaints', value: data.complaints.total, icon: MessageSquare, tone: 'danger' as const },
              { label: 'Total restaurants', value: data.restaurants.total, icon: Building2, tone: 'neutral' as const },
              {
                label: 'Restaurants pending verification',
                value: data.restaurants.pending_verification,
                icon: ShieldAlert,
                tone: 'warning' as const,
              },
            ].map((stat, i) => (
              <Reveal key={stat.label} delay={i * 70}>
                <StatCard {...stat} />
              </Reveal>
            ))}
          </div>

          <div className="mt-10">
            <SectionHeader title="Reports and complaints" />
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <BreakdownCard title="Reports by status" counts={data.reports.by_status} />
              <BreakdownCard title="Complaints by status" counts={data.complaints.by_status} />
            </div>
          </div>

          <div className="mt-10">
            <SectionHeader title="AI analysis outcomes" />
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <BreakdownCard title="Analyses by risk" counts={data.ai_analysis.by_risk} />
              <BreakdownCard title="Analyses by status" counts={data.ai_analysis.by_status} />
            </div>
            {Object.keys(data.ai_analysis.by_risk).length === 0 && (
              <div className="mt-4">
                <EmptyState
                  title="No AI analysis has run yet"
                  description="Risk and status breakdowns will appear here once reports are analyzed."
                />
              </div>
            )}
          </div>
        </>
      )}
    </AppShell>
  )
}
