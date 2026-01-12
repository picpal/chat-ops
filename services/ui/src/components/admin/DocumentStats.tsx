/**
 * 문서 통계 대시보드 컴포넌트
 */
import { useDocumentStats } from '@/hooks/useDocuments'
import { DOC_TYPE_LABELS } from '@/types/document'

export function DocumentStats() {
  const { data: stats, isLoading, error } = useDocumentStats()

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
            <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          </div>
        ))}
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        통계를 불러오는 데 실패했습니다.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 상태별 통계 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* 전체 문서 */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-500">전체 문서</div>
          <div className="mt-2 text-3xl font-bold text-gray-900">{stats.total_count}</div>
        </div>

        {/* 승인 대기 */}
        <div className="bg-yellow-50 rounded-lg shadow p-6 border-l-4 border-yellow-400">
          <div className="text-sm font-medium text-yellow-700">승인 대기</div>
          <div className="mt-2 text-3xl font-bold text-yellow-900">
            {stats.by_status?.pending || 0}
          </div>
        </div>

        {/* 승인됨 */}
        <div className="bg-green-50 rounded-lg shadow p-6 border-l-4 border-green-400">
          <div className="text-sm font-medium text-green-700">승인됨</div>
          <div className="mt-2 text-3xl font-bold text-green-900">
            {stats.by_status?.active || 0}
          </div>
        </div>

        {/* 반려됨 */}
        <div className="bg-red-50 rounded-lg shadow p-6 border-l-4 border-red-400">
          <div className="text-sm font-medium text-red-700">반려됨</div>
          <div className="mt-2 text-3xl font-bold text-red-900">
            {stats.by_status?.rejected || 0}
          </div>
        </div>
      </div>

      {/* 타입별 & 임베딩 통계 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 타입별 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-4">문서 타입별</h3>
          <div className="space-y-3">
            {Object.entries(stats.by_type || {}).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between">
                <span className="text-sm text-gray-700">
                  {DOC_TYPE_LABELS[type as keyof typeof DOC_TYPE_LABELS] || type}
                </span>
                <span className="font-medium text-gray-900">{count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 임베딩 상태 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-4">임베딩 상태</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">임베딩 있음</span>
              <span className="font-medium text-green-600">
                {stats.embedding_status?.with_embedding || 0}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">임베딩 없음</span>
              <span className="font-medium text-orange-600">
                {stats.embedding_status?.without_embedding || 0}
              </span>
            </div>
          </div>

          {/* 임베딩 진행률 바 */}
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-600 h-2 rounded-full"
                style={{
                  width: `${
                    stats.total_count > 0
                      ? ((stats.embedding_status?.with_embedding || 0) / stats.total_count) * 100
                      : 0
                  }%`,
                }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {stats.total_count > 0
                ? Math.round(
                    ((stats.embedding_status?.with_embedding || 0) / stats.total_count) * 100
                  )
                : 0}
              % 완료
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
