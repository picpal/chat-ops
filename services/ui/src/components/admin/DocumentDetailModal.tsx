/**
 * 문서 상세 보기 모달 컴포넌트
 */
import { useDocumentStore } from '@/store/documentStore'
import { useDocument, useDeleteDocument } from '@/hooks/useDocuments'
import { DOC_TYPE_LABELS, STATUS_LABELS } from '@/types/document'

export function DocumentDetailModal() {
  const { selectedDocument, closeModal, openModal } = useDocumentStore()
  const { data: document, isLoading } = useDocument(selectedDocument?.id ?? null)
  const deleteMutation = useDeleteDocument()

  if (!selectedDocument) return null

  const doc = document || selectedDocument

  const handleDelete = async () => {
    if (!window.confirm('이 문서를 삭제하시겠습니까?')) return

    try {
      await deleteMutation.mutateAsync(doc.id)
      closeModal()
    } catch (error) {
      alert('삭제 중 오류가 발생했습니다.')
    }
  }

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

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
        {/* 백드롭 */}
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75" onClick={closeModal} />

        {/* 모달 */}
        <div className="relative bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden">
          {/* 헤더 */}
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">문서 상세</h2>
            <button
              onClick={closeModal}
              className="text-gray-400 hover:text-gray-500"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* 본문 */}
          <div className="px-6 py-4 overflow-y-auto max-h-[60vh]">
            {isLoading ? (
              <div className="text-center py-8">
                <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto" />
              </div>
            ) : (
              <div className="space-y-6">
                {/* 기본 정보 */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-500">ID</label>
                    <p className="mt-1 text-sm text-gray-900">{doc.id}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-500">문서 타입</label>
                    <p className="mt-1">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {DOC_TYPE_LABELS[doc.doc_type] || doc.doc_type}
                      </span>
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-500">상태</label>
                    <p className="mt-1">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeClass(
                          doc.status
                        )}`}
                      >
                        {STATUS_LABELS[doc.status] || doc.status}
                      </span>
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-500">임베딩</label>
                    <p className="mt-1 text-sm text-gray-900">
                      {doc.has_embedding ? '있음' : '없음'}
                    </p>
                  </div>
                </div>

                {/* 제목 */}
                <div>
                  <label className="block text-sm font-medium text-gray-500">제목</label>
                  <p className="mt-1 text-lg font-medium text-gray-900">{doc.title}</p>
                </div>

                {/* 내용 */}
                <div>
                  <label className="block text-sm font-medium text-gray-500">내용</label>
                  <div className="mt-1 p-4 bg-gray-50 rounded-lg text-sm text-gray-900 whitespace-pre-wrap">
                    {'content' in doc ? doc.content : doc.content_preview}
                  </div>
                </div>

                {/* 메타데이터 */}
                {'metadata' in doc && doc.metadata && Object.keys(doc.metadata).length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-500">메타데이터</label>
                    <pre className="mt-1 p-4 bg-gray-50 rounded-lg text-sm text-gray-900 overflow-x-auto">
                      {JSON.stringify(doc.metadata, null, 2)}
                    </pre>
                  </div>
                )}

                {/* 제출/검토 정보 */}
                <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                  <div>
                    <label className="block text-sm font-medium text-gray-500">제출자</label>
                    <p className="mt-1 text-sm text-gray-900">{doc.submitted_by || '-'}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-500">제출일</label>
                    <p className="mt-1 text-sm text-gray-900">
                      {doc.submitted_at
                        ? new Date(doc.submitted_at).toLocaleString('ko-KR')
                        : '-'}
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-500">검토자</label>
                    <p className="mt-1 text-sm text-gray-900">{doc.reviewed_by || '-'}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-500">검토일</label>
                    <p className="mt-1 text-sm text-gray-900">
                      {doc.reviewed_at
                        ? new Date(doc.reviewed_at).toLocaleString('ko-KR')
                        : '-'}
                    </p>
                  </div>
                </div>

                {/* 반려 사유 */}
                {'rejection_reason' in doc && doc.rejection_reason && (
                  <div className="pt-4 border-t">
                    <label className="block text-sm font-medium text-red-500">반려 사유</label>
                    <p className="mt-1 text-sm text-red-700 p-3 bg-red-50 rounded-lg">
                      {doc.rejection_reason}
                    </p>
                  </div>
                )}

                {/* 생성/수정일 */}
                <div className="grid grid-cols-2 gap-4 pt-4 border-t text-sm text-gray-500">
                  <div>
                    생성일:{' '}
                    {doc.created_at
                      ? new Date(doc.created_at).toLocaleString('ko-KR')
                      : '-'}
                  </div>
                  <div>
                    수정일:{' '}
                    {doc.updated_at
                      ? new Date(doc.updated_at).toLocaleString('ko-KR')
                      : '-'}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 푸터 */}
          <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between bg-gray-50">
            <button
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="px-4 py-2 text-red-600 hover:text-red-800 disabled:opacity-50"
            >
              {deleteMutation.isPending ? '삭제 중...' : '삭제'}
            </button>
            <div className="flex items-center gap-2">
              {doc.status === 'pending' && (
                <button
                  onClick={() => openModal('review', selectedDocument)}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  검토
                </button>
              )}
              <button
                onClick={() => openModal('edit', selectedDocument)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                수정
              </button>
              <button
                onClick={closeModal}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
