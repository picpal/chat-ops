/** 별점 분석 API 응답 타입 */

export type AnalyticsPeriod = 'today' | '7d' | '30d' | 'all'

export interface RatingSummary {
  totalCount: number
  averageRating: number
  distribution: Record<string, number>
  withFeedbackCount: number
  period: string
}

export interface DistributionItem {
  rating: number
  count: number
  percentage: number
}

export interface RatingDistribution {
  distribution: DistributionItem[]
  period: string
}

export interface TrendItem {
  date: string
  averageRating: number
  count: number
}

export interface RatingTrend {
  trend: TrendItem[]
  period: string
}

export interface RatingDetailItem {
  requestId: string
  sessionId?: string
  sessionTitle?: string
  userQuestion?: string
  aiResponseSummary?: string
  rating: number
  feedback?: string
  createdAt: string
}

export interface RatingDetailsPage {
  items: RatingDetailItem[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export interface RatingDetailsParams {
  page?: number
  pageSize?: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  minRating?: number
  maxRating?: number
  hasFeedback?: boolean
}

export interface ConversationPair {
  userQuestion: string
  aiResponse: string
  createdAt?: string
}

export interface RatingContext {
  requestId: string
  sessionId?: string
  sessionTitle?: string
  rating: number
  feedback?: string
  createdAt: string
  conversations: ConversationPair[]
}
