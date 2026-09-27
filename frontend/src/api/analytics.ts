import { http } from '@/lib/http'
import type { AnalyticsSummary } from '@/types/analytics'

export const analyticsApi = {
  summary: () => http.get<AnalyticsSummary>('/analytics/summary/').then((r) => r.data),
}
