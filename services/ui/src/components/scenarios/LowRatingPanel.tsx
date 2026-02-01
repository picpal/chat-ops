import StarRating from '@/components/common/StarRating'
import { useRatingDetails } from '@/hooks/useRatingsAnalytics'

export function LowRatingPanel() {
  const { data, isLoading } = useRatingDetails({
    page: 1,
    pageSize: 10,
    sortBy: 'created_at',
    sortOrder: 'desc',
    minRating: 1,
    maxRating: 2,
  })

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-4" />
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-100 rounded" />
          ))}
        </div>
      </div>
    )
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-sm font-medium text-gray-500 mb-4">낮은 별점 분석 (1~2점)</h3>
        <p className="text-gray-400 text-sm">낮은 별점 데이터가 없습니다</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-sm font-medium text-gray-500 mb-4">
        낮은 별점 분석 (1~2점) — 최근 {data.items.length}건
      </h3>
      <div className="space-y-3">
        {data.items.map((item) => (
          <div
            key={item.requestId}
            className="border border-red-100 rounded-lg p-4 bg-red-50"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-500">
                {item.sessionTitle || '세션 제목 없음'}
              </span>
              <div className="flex items-center gap-2">
                <StarRating rating={item.rating} readonly size="sm" />
                <span className="text-xs text-gray-400">
                  {item.createdAt
                    ? new Date(item.createdAt).toLocaleString('ko-KR')
                    : ''}
                </span>
              </div>
            </div>
            <div className="text-sm mb-1">
              <span className="font-medium text-gray-700">Q: </span>
              <span className="text-gray-600">{item.userQuestion || '-'}</span>
            </div>
            <div className="text-sm mb-1">
              <span className="font-medium text-gray-700">A: </span>
              <span className="text-gray-500">{item.aiResponseSummary || '-'}</span>
            </div>
            {item.feedback && (
              <div className="text-sm mt-2 pt-2 border-t border-red-200">
                <span className="font-medium text-red-700">피드백: </span>
                <span className="text-red-600">{item.feedback}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
