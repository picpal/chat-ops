import { aiClient } from './client'
import type {
  AnalyticsPeriod,
  RatingSummary,
  RatingDistribution,
  RatingTrend,
  RatingDetailsPage,
  RatingDetailsParams,
  RatingContext,
} from '@/types/ratingsAnalytics'

export const ratingsAnalyticsApi = {
  getSummary: async (period: AnalyticsPeriod = 'all'): Promise<RatingSummary> => {
    const response = await aiClient.get('/api/v1/ratings/analytics/summary', {
      params: { period },
    })
    return response.data
  },

  getDistribution: async (period: AnalyticsPeriod = '30d'): Promise<RatingDistribution> => {
    const response = await aiClient.get('/api/v1/ratings/analytics/distribution', {
      params: { period },
    })
    return response.data
  },

  getTrend: async (period: AnalyticsPeriod = '30d', granularity: string = 'day'): Promise<RatingTrend> => {
    const response = await aiClient.get('/api/v1/ratings/analytics/trend', {
      params: { period, granularity },
    })
    return response.data
  },

  getDetails: async (params: RatingDetailsParams = {}): Promise<RatingDetailsPage> => {
    const response = await aiClient.get('/api/v1/ratings/analytics/details', {
      params: {
        page: params.page ?? 1,
        page_size: params.pageSize ?? 20,
        sort_by: params.sortBy ?? 'created_at',
        sort_order: params.sortOrder ?? 'desc',
        min_rating: params.minRating,
        max_rating: params.maxRating,
        has_feedback: params.hasFeedback,
      },
    })
    return response.data
  },

  getContext: async (requestId: string): Promise<RatingContext> => {
    const response = await aiClient.get(`/api/v1/ratings/${requestId}/context`)
    return response.data
  },

  updateFeedback: async (requestId: string, feedback: string): Promise<void> => {
    await aiClient.patch(`/api/v1/ratings/${requestId}/feedback`, { feedback })
  },
}
