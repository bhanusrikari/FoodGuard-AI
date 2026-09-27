/** Shape of GET /api/v1/analytics/summary/ — every field is a direct DB
 * aggregation on the backend (analytics/views.py). No trends, percentages,
 * or derived metrics the API doesn't actually return. */
export interface AnalyticsSummary {
  reports: {
    total: number
    by_status: Record<string, number>
    by_priority: Record<string, number>
  }
  complaints: {
    total: number
    by_status: Record<string, number>
    by_priority: Record<string, number>
  }
  ai_analysis: {
    by_status: Record<string, number>
    by_risk: Record<string, number>
  }
  restaurants: {
    total: number
    pending_verification: number
  }
}
