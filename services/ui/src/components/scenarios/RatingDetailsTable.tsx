import { useState } from 'react'
import StarRating from '@/components/common/StarRating'
import { useRatingDetails } from '@/hooks/useRatingsAnalytics'
import { RatingDetailModal } from './RatingDetailModal'
import type { RatingDetailsParams } from '@/types/ratingsAnalytics'

type TabType = 'all' | 'low'

export function RatingDetailsTable() {
  const [tab, setTab] = useState<TabType>('all')
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null)
  const [params, setParams] = useState<RatingDetailsParams>({
    page: 1,
    pageSize: 20,
    sortBy: 'created_at',
    sortOrder: 'desc',
  })

  const effectiveParams: RatingDetailsParams = {
    ...params,
    ...(tab === 'low' ? { minRating: 1, maxRating: 2 } : {}),
  }

  const { data, isLoading } = useRatingDetails(effectiveParams)

  const handleSort = (col: string) => {
    setParams((p) => ({
      ...p,
      sortBy: col,
      sortOrder: p.sortBy === col && p.sortOrder === 'desc' ? 'asc' : 'desc',
      page: 1,
    }))
  }

  const sortIcon = (col: string) => {
    if (params.sortBy !== col) return ''
    return params.sortOrder === 'asc' ? ' ↑' : ' ↓'
  }

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Tabs + Filters */}
      <div className="border-b px-6 pt-4 flex items-center justify-between">
        <div className="flex gap-4">
          <button
            onClick={() => { setTab('all'); setParams((p) => ({ ...p, page: 1, minRating: undefined, maxRating: undefined })) }}
            className={`pb-3 text-sm font-medium border-b-2 ${
              tab === 'all' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            전체
          </button>
          <button
            onClick={() => { setTab('low'); setParams((p) => ({ ...p, page: 1 })) }}
            className={`pb-3 text-sm font-medium border-b-2 ${
              tab === 'low' ? 'border-red-500 text-red-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            낮은 별점 (1~2)
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600">
            <tr>
              <th className="px-4 py-3 text-left">세션</th>
              <th className="px-4 py-3 text-left">질문</th>
              <th className="px-4 py-3 text-left">응답 요약</th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:text-gray-900"
                onClick={() => handleSort('rating')}
              >
                별점{sortIcon('rating')}
              </th>
              <th className="px-4 py-3 text-left">피드백</th>
              <th
                className="px-4 py-3 text-left cursor-pointer hover:text-gray-900"
                onClick={() => handleSort('created_at')}
              >
                시간{sortIcon('created_at')}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {isLoading ? (
              [...Array(5)].map((_, i) => (
                <tr key={i}>
                  {[...Array(6)].map((__, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-gray-200 rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            ) : data?.items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  데이터가 없습니다
                </td>
              </tr>
            ) : (
              data?.items.map((item) => (
                <tr
                  key={item.requestId}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => setSelectedRequestId(item.requestId)}
                >
                  <td className="px-4 py-3 max-w-[140px] truncate" title={item.sessionTitle || ''}>
                    {item.sessionTitle || '-'}
                  </td>
                  <td className="px-4 py-3 max-w-[200px] truncate" title={item.userQuestion || ''}>
                    {item.userQuestion || '-'}
                  </td>
                  <td className="px-4 py-3 max-w-[200px] truncate" title={item.aiResponseSummary || ''}>
                    {item.aiResponseSummary || '-'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <StarRating rating={item.rating} readonly size="sm" />
                  </td>
                  <td className="px-4 py-3 max-w-[160px] truncate" title={item.feedback || ''}>
                    {item.feedback || (
                      <span className="text-gray-300">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                    {item.createdAt
                      ? new Date(item.createdAt).toLocaleString('ko-KR')
                      : '-'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {data && data.totalPages > 1 && (
        <div className="flex items-center justify-between px-6 py-3 border-t text-sm">
          <span className="text-gray-500">
            총 {data.total}건 (페이지 {data.page}/{data.totalPages})
          </span>
          <div className="flex gap-1">
            <button
              disabled={data.page <= 1}
              onClick={() => setParams((p) => ({ ...p, page: (p.page || 1) - 1 }))}
              className="px-3 py-1 rounded border disabled:opacity-40 hover:bg-gray-50"
            >
              이전
            </button>
            <button
              disabled={data.page >= data.totalPages}
              onClick={() => setParams((p) => ({ ...p, page: (p.page || 1) + 1 }))}
              className="px-3 py-1 rounded border disabled:opacity-40 hover:bg-gray-50"
            >
              다음
            </button>
          </div>
        </div>
      )}

      {/* Rating Detail Modal */}
      {selectedRequestId && (
        <RatingDetailModal
          requestId={selectedRequestId}
          onClose={() => setSelectedRequestId(null)}
        />
      )}
    </div>
  )
}
