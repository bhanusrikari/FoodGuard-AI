import { useQuery } from '@tanstack/react-query'
import { analyticsApi } from '@/api/analytics'
import { queryKeys } from '@/lib/queryKeys'

export function useAnalyticsSummary() {
  return useQuery({
    queryKey: queryKeys.analytics.summary,
    queryFn: analyticsApi.summary,
  })
}
