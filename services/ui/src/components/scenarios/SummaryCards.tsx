import StarRating from '@/components/common/StarRating'
import type { RatingSummary } from '@/types/ratingsAnalytics'

interface SummaryCardsProps {
  data?: RatingSummary
  isLoading: boolean
}

export function SummaryCards({ data, isLoading }: SummaryCardsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-4" />
            <div className="h-8 bg-gray-200 rounded w-1/3" />
          </div>
        ))}
      </div>
    )
  }

  if (!data) return null

  const lowRatingCount =
    (data.distribution['1'] || 0) + (data.distribution['2'] || 0)

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-sm font-medium text-gray-500">전체 평가 수</div>
        <div className="mt-2 text-3xl font-bold text-gray-900">
          {data.totalCount}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-sm font-medium text-gray-500">평균 별점</div>
        <div className="mt-2 flex items-center gap-2">
          <span className="text-3xl font-bold text-gray-900">
            {data.averageRating.toFixed(1)}
          </span>
          <StarRating rating={Math.round(data.averageRating)} readonly size="sm" />
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-sm font-medium text-gray-500">피드백 수</div>
        <div className="mt-2 text-3xl font-bold text-blue-600">
          {data.withFeedbackCount}
        </div>
        <div className="text-xs text-gray-400 mt-1">
          {data.totalCount > 0
            ? `${Math.round((data.withFeedbackCount / data.totalCount) * 100)}%`
            : '0%'}
        </div>
      </div>

      <div className="bg-red-50 rounded-lg shadow p-6 border-l-4 border-red-400">
        <div className="text-sm font-medium text-red-700">낮은 별점 (1~2점)</div>
        <div className="mt-2 text-3xl font-bold text-red-900">
          {lowRatingCount}
        </div>
        <div className="text-xs text-red-500 mt-1">
          {data.totalCount > 0
            ? `${Math.round((lowRatingCount / data.totalCount) * 100)}%`
            : '0%'}
        </div>
      </div>
    </div>
  )
}
