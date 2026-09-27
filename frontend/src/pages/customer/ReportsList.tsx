import { useMemo, useState } from 'react'
import { FileText, Plus } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { ReportCard } from '@/components/reports/ReportCard'
import { Reveal } from '@/components/motion/Reveal'
import { EmptyState } from '@/components/states/EmptyState'
import { ErrorState } from '@/components/states/ErrorState'
import { ListSkeleton } from '@/components/states/LoadingSkeleton'
import { LinkButton } from '@/components/ui/LinkButton'
import { Select } from '@/components/ui/Select'
import { useReports } from '@/hooks/useReports'
import { useTranslation } from '@/i18n/LanguageContext'
import type { ReportStatus } from '@/types/report'

const STATUS_FILTERS: Array<{ label: string; value: ReportStatus | 'ALL' }> = [
  { label: 'All statuses', value: 'ALL' },
  { label: 'Draft', value: 'DRAFT' },
  { label: 'Submitted', value: 'SUBMITTED' },
  { label: 'Under Review', value: 'UNDER_REVIEW' },
  { label: 'Resolved', value: 'RESOLVED' },
  { label: 'Closed', value: 'CLOSED' },
]

export default function ReportsList() {
  const { data, isLoading, isError, isSuccess, refetch } = useReports()
  const [statusFilter, setStatusFilter] = useState<ReportStatus | 'ALL'>('ALL')
  const t = useTranslation()

  const reports = useMemo(() => {
    const all = data ?? []
    return statusFilter === 'ALL' ? all : all.filter((r) => r.status === statusFilter)
  }, [data, statusFilter])

  return (
    <AppShell title="Reports">
      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-semibold text-neutral-900">{t('reports.list.heading')}</h2>
          <p className="mt-1 text-sm text-neutral-500">{t('reports.list.subtitle')}</p>
        </div>
        <LinkButton to="/reports/new">
          <Plus className="size-4" aria-hidden="true" />
          {t('reports.list.new')}
        </LinkButton>
      </div>

      {isSuccess && (data?.length ?? 0) > 0 && (
        <div className="mb-4 max-w-xs">
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as ReportStatus | 'ALL')}
            aria-label="Filter by status"
          >
            {STATUS_FILTERS.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </Select>
        </div>
      )}

      {isLoading && <ListSkeleton items={4} />}
      {isError && <ErrorState message={t('reports.list.loadError')} onRetry={() => refetch()} />}
      {isSuccess && (data?.length ?? 0) === 0 && (
        <EmptyState
          icon={<FileText className="size-6" aria-hidden="true" />}
          title={t('reports.list.emptyTitle')}
          description={t('reports.list.emptyDescription')}
          action={<LinkButton to="/reports/new" size="sm">{t('reports.list.createAction')}</LinkButton>}
        />
      )}
      {isSuccess && (data?.length ?? 0) > 0 && reports.length === 0 && (
        <EmptyState title={t('reports.list.emptyFilterTitle')} description={t('reports.list.emptyFilterDescription')} />
      )}
      {reports.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {reports.map((report, i) => (
            <Reveal key={report.id} delay={i * 60}>
              <ReportCard report={report} />
            </Reveal>
          ))}
        </div>
      )}
    </AppShell>
  )
}
