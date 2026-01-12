/**
 * 문서 필터 컴포넌트
 */
import { useDocumentStore } from '@/store/documentStore'
import { DocType, DocumentStatus, DOC_TYPE_LABELS, STATUS_LABELS } from '@/types/document'

export function DocumentFilters() {
  const { filters, setFilters, resetFilters, viewMode } = useDocumentStore()

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex flex-wrap gap-4 items-end">
        {/* 검색 */}
        <div className="flex-1 min-w-[200px]">
          <label className="block text-sm font-medium text-gray-700 mb-1">검색</label>
          <input
            type="text"
            value={filters.search}
            onChange={(e) => setFilters({ search: e.target.value })}
            placeholder="제목 또는 내용 검색..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* 문서 타입 */}
        <div className="w-40">
          <label className="block text-sm font-medium text-gray-700 mb-1">문서 타입</label>
          <select
            value={filters.doc_type || ''}
            onChange={(e) => setFilters({ doc_type: (e.target.value || null) as DocType | null })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">전체</option>
            {Object.entries(DOC_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {/* 상태 (전체 모드에서만) */}
        {viewMode === 'all' && (
          <div className="w-32">
            <label className="block text-sm font-medium text-gray-700 mb-1">상태</label>
            <select
              value={filters.status || ''}
              onChange={(e) =>
                setFilters({ status: (e.target.value || null) as DocumentStatus | null })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">전체</option>
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* 임베딩 상태 */}
        <div className="w-36">
          <label className="block text-sm font-medium text-gray-700 mb-1">임베딩</label>
          <select
            value={filters.has_embedding === null ? '' : filters.has_embedding.toString()}
            onChange={(e) =>
              setFilters({
                has_embedding: e.target.value === '' ? null : e.target.value === 'true',
              })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">전체</option>
            <option value="true">있음</option>
            <option value="false">없음</option>
          </select>
        </div>

        {/* 정렬 */}
        <div className="w-36">
          <label className="block text-sm font-medium text-gray-700 mb-1">정렬</label>
          <select
            value={filters.sort_by}
            onChange={(e) => setFilters({ sort_by: e.target.value as typeof filters.sort_by })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="created_at">생성일</option>
            <option value="updated_at">수정일</option>
            <option value="title">제목</option>
            <option value="doc_type">타입</option>
          </select>
        </div>

        {/* 정렬 방향 */}
        <div className="w-24">
          <label className="block text-sm font-medium text-gray-700 mb-1">방향</label>
          <select
            value={filters.sort_order}
            onChange={(e) => setFilters({ sort_order: e.target.value as 'asc' | 'desc' })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="desc">최신순</option>
            <option value="asc">오래된순</option>
          </select>
        </div>

        {/* 초기화 버튼 */}
        <button
          onClick={resetFilters}
          className="px-4 py-2 text-gray-600 hover:text-gray-900 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          초기화
        </button>
      </div>
    </div>
  )
}
