import { MessageSquare } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { ComplaintCard } from '@/components/complaints/ComplaintCard'
import { Reveal } from '@/components/motion/Reveal'
import { EmptyState } from '@/components/states/EmptyState'
import { ErrorState } from '@/components/states/ErrorState'
import { ListSkeleton } from '@/components/states/LoadingSkeleton'
import { LinkButton } from '@/components/ui/LinkButton'
import { useComplaints } from '@/hooks/useComplaints'

export default function ComplaintsList() {
  const { data, isLoading, isError, isSuccess, refetch } = useComplaints()

  return (
    <AppShell title="Complaints">
      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-semibold text-neutral-900">Your complaints</h2>
          <p className="mt-1 text-sm text-neutral-500">Formal complaints filed against submitted reports.</p>
        </div>
        <LinkButton to="/complaints/new">File a Complaint</LinkButton>
      </div>

      {isLoading && <ListSkeleton items={4} />}
      {isError && <ErrorState message="We couldn't load your complaints." onRetry={() => refetch()} />}
      {isSuccess && data.length === 0 && (
        <EmptyState
          icon={<MessageSquare className="size-6" aria-hidden="true" />}
          title="No complaints filed yet"
          description="Complaints can be filed once a food safety report has been submitted for review."
          action={<LinkButton to="/complaints/new" size="sm">File a Complaint</LinkButton>}
        />
      )}
      {isSuccess && data.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((complaint, i) => (
            <Reveal key={complaint.id} delay={i * 60}>
              <ComplaintCard complaint={complaint} />
            </Reveal>
          ))}
        </div>
      )}
    </AppShell>
  )
}
