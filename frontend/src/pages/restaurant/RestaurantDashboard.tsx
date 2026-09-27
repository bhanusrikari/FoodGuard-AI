import { Building2, Plus } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { RestaurantCard } from '@/components/restaurants/RestaurantCard'
import { Reveal } from '@/components/motion/Reveal'
import { EmptyState } from '@/components/states/EmptyState'
import { ErrorState } from '@/components/states/ErrorState'
import { ListSkeleton } from '@/components/states/LoadingSkeleton'
import { LinkButton } from '@/components/ui/LinkButton'
import { useAuth } from '@/context/AuthContext'
import { useRestaurants } from '@/hooks/useRestaurants'

export default function RestaurantDashboard() {
  const { user } = useAuth()
  const { data, isLoading, isError, isSuccess, refetch } = useRestaurants()

  const myRestaurants = (data ?? []).filter((r) => r.owner.id === user?.id)

  return (
    <AppShell title="My Restaurants">
      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-semibold text-neutral-900">My Restaurants</h2>
          <p className="mt-1 text-sm text-neutral-500">Manage the restaurants you own on FoodGuard AI.</p>
        </div>
        <LinkButton to="/restaurant/new">
          <Plus className="size-4" aria-hidden="true" />
          Add Restaurant
        </LinkButton>
      </div>

      {isLoading && <ListSkeleton items={3} />}
      {isError && <ErrorState message="We couldn't load your restaurants." onRetry={() => refetch()} />}
      {isSuccess && myRestaurants.length === 0 && (
        <EmptyState
          icon={<Building2 className="size-6" aria-hidden="true" />}
          title="No restaurants yet"
          description="Register your restaurant to appear on FoodGuard AI and manage its profile."
          action={<LinkButton to="/restaurant/new" size="sm">Add Restaurant</LinkButton>}
        />
      )}
      {myRestaurants.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {myRestaurants.map((r, i) => (
            <Reveal key={r.id} delay={i * 60}>
              <RestaurantCard restaurant={r} />
            </Reveal>
          ))}
        </div>
      )}

      {isSuccess && myRestaurants.length > 0 && (
        <p className="mt-6 text-xs text-neutral-400">
          Note: only active restaurants are shown here. A restaurant you deactivate will no longer appear in this
          list until reactivated.
        </p>
      )}
    </AppShell>
  )
}
