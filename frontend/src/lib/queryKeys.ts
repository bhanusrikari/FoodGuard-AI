export const queryKeys = {
  reports: {
    all: ['reports'] as const,
    detail: (id: number) => ['reports', id] as const,
  },
  complaints: {
    all: ['complaints'] as const,
    detail: (id: number) => ['complaints', id] as const,
  },
  restaurants: {
    all: ['restaurants'] as const,
    detail: (id: number) => ['restaurants', id] as const,
  },
  aiAnalysis: {
    detail: (reportId: number) => ['ai-analysis', reportId] as const,
  },
  analytics: {
    summary: ['analytics', 'summary'] as const,
  },
}
