/**
 * 문서 목록 테이블 컴포넌트
 */
import { useDocumentStore } from '@/store/documentStore'
import { useDocuments, usePendingDocuments } from '@/hooks/useDocuments'
import { DOC_TYPE_LABELS, STATUS_LABELS } from '@/types/document'

export function DocumentList() {
  const { viewMode, filters, page, pageSize, setPage, selectedIds, toggleSelection, selectAll, clearSelection, openModal } =
    useDocumentStore()

  // 뷰 모드에 따라 다른 쿼리 사용
  const listParams = {
    page,
    page_size: pageSize,
    doc_type: filters.doc_type || undefined,
    status: viewMode === 'all' ? filters.status || undefined : undefined,
    has_embedding: filters.has_embedding ?? undefined,
    search: filters.search || undefined,
    sort_by: filters.sort_by,
    sort_order: filters.sort_order,
  }

  const allDocsQuery = useDocuments(listParams)
  const pendingDocsQuery = usePendingDocuments(listParams)

  const { data, isLoading, error } = viewMode === 'all' ? allDocsQuery : pendingDocsQuery

  // 전체 선택/해제
  const handleSelectAll = () => {
    if (!data) return
    const allIds = data.items.map((item) => item.id)
    if (selectedIds.length === allIds.length) {
      clearSelection()
    } else {
      selectAll(allIds)
    }
  }

  // 상태 배지 색상
  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      case 'active':
        return 'bg-green-100 text-green-800'
      case 'rejected':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow">
        <div className="p-8 text-center">
          <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
          <p className="mt-4 text-gray-500">문서를 불러오는 중...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        문서를 불러오는 데 실패했습니다: {(error as Error).message}
      </div>
    )
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <p className="text-gray-500">문서가 없습니다.</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* 테이블 */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 w-12">
                <input
                  type="checkbox"
                  checked={selectedIds.length > 0 && selectedIds.length === data.items.length}
                  onChange={handleSelectAll}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ID
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                제목
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                타입
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                상태
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                임베딩
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                제출자
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                생성일
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                액션
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.items.map((doc) => (
              <tr
                key={doc.id}
                className={`hover:bg-gray-50 ${selectedIds.includes(doc.id) ? 'bg-blue-50' : ''}`}
              >
                <td className="px-4 py-4">
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(doc.id)}
                    onChange={() => toggleSelection(doc.id)}
                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                </td>
                <td className="px-4 py-4 text-sm text-gray-500">{doc.id}</td>
                <td className="px-4 py-4">
                  <div
                    className="text-sm font-medium text-gray-900 cursor-pointer hover:text-blue-600"
                    onClick={() => openModal('detail', doc)}
                  >
                    {doc.title}
                  </div>
                  <div className="text-sm text-gray-500 truncate max-w-xs">{doc.content_preview}</div>
                </td>
                <td className="px-4 py-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {DOC_TYPE_LABELS[doc.doc_type] || doc.doc_type}
                  </span>
                </td>
                <td className="px-4 py-4">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeClass(
                      doc.status
                    )}`}
                  >
                    {STATUS_LABELS[doc.status] || doc.status}
                  </span>
                </td>
                <td className="px-4 py-4">
                  {doc.has_embedding ? (
                    <span className="text-green-600">O</span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>
                <td className="px-4 py-4 text-sm text-gray-500">{doc.submitted_by || '-'}</td>
                <td className="px-4 py-4 text-sm text-gray-500">
                  {doc.created_at ? new Date(doc.created_at).toLocaleDateString('ko-KR') : '-'}
                </td>
                <td className="px-4 py-4 text-sm">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => openModal('detail', doc)}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      상세
                    </button>
                    {doc.status === 'pending' && (
                      <button
                        onClick={() => openModal('review', doc)}
                        className="text-green-600 hover:text-green-900"
                      >
                        검토
                      </button>
                    )}
                    <button
                      onClick={() => openModal('edit', doc)}
                      className="text-gray-600 hover:text-gray-900"
                    >
                      수정
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 페이지네이션 */}
      <div className="bg-gray-50 px-4 py-3 flex items-center justify-between border-t border-gray-200">
        <div className="text-sm text-gray-700">
          총 <span className="font-medium">{data.total}</span>개 중{' '}
          <span className="font-medium">{(page - 1) * pageSize + 1}</span>-
          <span className="font-medium">{Math.min(page * pageSize, data.total)}</span>개 표시
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPage(page - 1)}
            disabled={!data.has_prev}
            className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
          >
            이전
          </button>
          <span className="text-sm text-gray-700">
            {page} / {data.total_pages}
          </span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={!data.has_next}
            className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
          >
            다음
          </button>
        </div>
      </div>
    </div>
  )
}
