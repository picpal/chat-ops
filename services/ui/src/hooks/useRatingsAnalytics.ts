import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ratingsAnalyticsApi } from '@/api/ratingsAnalytics'
import type { AnalyticsPeriod, RatingDetailsParams } from '@/types/ratingsAnalytics'

export const ratingsAnalyticsKeys = {
  all: ['ratingsAnalytics'] as const,
  summary: (period: AnalyticsPeriod) => [...ratingsAnalyticsKeys.all, 'summary', period] as const,
  distribution: (period: AnalyticsPeriod) => [...ratingsAnalyticsKeys.all, 'distribution', period] as const,
  trend: (period: AnalyticsPeriod, granularity: string) =>
    [...ratingsAnalyticsKeys.all, 'trend', period, granularity] as const,
  details: (params: RatingDetailsParams) => [...ratingsAnalyticsKeys.all, 'details', params] as const,
  context: (requestId: string) => [...ratingsAnalyticsKeys.all, 'context', requestId] as const,
}

export function useRatingSummary(period: AnalyticsPeriod) {
  return useQuery({
    queryKey: ratingsAnalyticsKeys.summary(period),
    queryFn: () => ratingsAnalyticsApi.getSummary(period),
  })
}

export function useRatingDistribution(period: AnalyticsPeriod) {
  return useQuery({
    queryKey: ratingsAnalyticsKeys.distribution(period),
    queryFn: () => ratingsAnalyticsApi.getDistribution(period),
  })
}

export function useRatingTrend(period: AnalyticsPeriod, granularity: string = 'day') {
  return useQuery({
    queryKey: ratingsAnalyticsKeys.trend(period, granularity),
    queryFn: () => ratingsAnalyticsApi.getTrend(period, granularity),
  })
}

export function useRatingDetails(params: RatingDetailsParams) {
  return useQuery({
    queryKey: ratingsAnalyticsKeys.details(params),
    queryFn: () => ratingsAnalyticsApi.getDetails(params),
  })
}

export function useRatingContext(requestId: string | null) {
  return useQuery({
    queryKey: ratingsAnalyticsKeys.context(requestId!),
    queryFn: () => ratingsAnalyticsApi.getContext(requestId!),
    enabled: !!requestId,
  })
}

export function useUpdateFeedback() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ requestId, feedback }: { requestId: string; feedback: string }) =>
      ratingsAnalyticsApi.updateFeedback(requestId, feedback),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ratingsAnalyticsKeys.context(variables.requestId) })
      queryClient.invalidateQueries({ queryKey: [...ratingsAnalyticsKeys.all, 'details'] })
    },
  })
}
