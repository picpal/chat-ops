/**
 * 문서 승인/반려 모달 컴포넌트
 */
import { useState } from 'react'
import { useDocumentStore } from '@/store/documentStore'
import { useReviewDocument, useBulkReview } from '@/hooks/useDocuments'

export function ReviewModal() {
  const { modalType, selectedDocument, selectedIds, closeModal, clearSelection } = useDocumentStore()
  const isBulk = modalType === 'bulk-review'

  const reviewMutation = useReviewDocument()
  const bulkReviewMutation = useBulkReview()

  const [action, setAction] = useState<'approve' | 'reject'>('approve')
  const [reviewedBy, setReviewedBy] = useState('')
  const [rejectionReason, setRejectionReason] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})

  const validate = () => {
    const newErrors: Record<string, string> = {}

    if (!reviewedBy.trim()) {
      newErrors.reviewedBy = '검토자를 입력해주세요.'
    }
    if (action === 'reject' && !rejectionReason.trim()) {
      newErrors.rejectionReason = '반려 사유를 입력해주세요.'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) return

    try {
      if (isBulk) {
        const result = await bulkReviewMutation.mutateAsync({
          ids: selectedIds,
          action,
          reviewed_by: reviewedBy,
          rejection_reason: action === 'reject' ? rejectionReason : undefined,
        })

        if (result.failed_count > 0) {
          alert(
            `${result.success_count}개 ${action === 'approve' ? '승인' : '반려'} 성공, ${
              result.failed_count
            }개 실패`
          )
        } else {
          alert(
            `${result.success_count}개 문서가 ${action === 'approve' ? '승인' : '반려'}되었습니다.`
          )
        }
        clearSelection()
      } else if (selectedDocument) {
        await reviewMutation.mutateAsync({
          id: selectedDocument.id,
          data: {
            action,
            reviewed_by: reviewedBy,
            rejection_reason: action === 'reject' ? rejectionReason : undefined,
          },
        })
        alert(`문서가 ${action === 'approve' ? '승인' : '반려'}되었습니다.`)
      }
      closeModal()
    } catch (error) {
      alert('처리 중 오류가 발생했습니다.')
    }
  }

  const isPending = reviewMutation.isPending || bulkReviewMutation.isPending

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
        {/* 백드롭 */}
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75" onClick={closeModal} />

        {/* 모달 */}
        <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full">
          {/* 헤더 */}
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">
              {isBulk ? `${selectedIds.length}개 문서 검토` : '문서 검토'}
            </h2>
            <button onClick={closeModal} className="text-gray-400 hover:text-gray-500">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* 폼 */}
          <form onSubmit={handleSubmit} className="px-6 py-4">
            <div className="space-y-4">
              {/* 단일 문서 정보 */}
              {!isBulk && selectedDocument && (
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600">문서 ID: {selectedDocument.id}</p>
                  <p className="font-medium text-gray-900">{selectedDocument.title}</p>
                </div>
              )}

              {/* 액션 선택 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">검토 결과</label>
                <div className="flex gap-4">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="action"
                      value="approve"
                      checked={action === 'approve'}
                      onChange={() => setAction('approve')}
                      className="w-4 h-4 text-green-600 border-gray-300 focus:ring-green-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">승인</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="action"
                      value="reject"
                      checked={action === 'reject'}
                      onChange={() => setAction('reject')}
                      className="w-4 h-4 text-red-600 border-gray-300 focus:ring-red-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">반려</span>
                  </label>
                </div>
              </div>

              {/* 검토자 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  검토자 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={reviewedBy}
                  onChange={(e) => setReviewedBy(e.target.value)}
                  placeholder="검토자 이름/ID"
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                    errors.reviewedBy ? 'border-red-500' : 'border-gray-300'
                  }`}
                />
                {errors.reviewedBy && (
                  <p className="mt-1 text-sm text-red-500">{errors.reviewedBy}</p>
                )}
              </div>

              {/* 반려 사유 */}
              {action === 'reject' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    반려 사유 <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    placeholder="반려 사유를 입력하세요"
                    rows={3}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                      errors.rejectionReason ? 'border-red-500' : 'border-gray-300'
                    }`}
                  />
                  {errors.rejectionReason && (
                    <p className="mt-1 text-sm text-red-500">{errors.rejectionReason}</p>
                  )}
                </div>
              )}

              {/* 안내 메시지 */}
              <div
                className={`p-3 rounded-lg text-sm ${
                  action === 'approve'
                    ? 'bg-green-50 text-green-700'
                    : 'bg-red-50 text-red-700'
                }`}
              >
                {action === 'approve' ? (
                  <>
                    승인된 문서는 즉시 RAG 검색에 사용됩니다.
                    {isBulk && <br />}
                    {isBulk && '임베딩이 없는 문서는 자동으로 임베딩이 생성됩니다.'}
                  </>
                ) : (
                  <>
                    반려된 문서는 RAG 검색에서 제외됩니다.
                    {isBulk && <br />}
                    {isBulk && '반려 사유는 모든 선택된 문서에 동일하게 적용됩니다.'}
                  </>
                )}
              </div>
            </div>
          </form>

          {/* 푸터 */}
          <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-end gap-2 bg-gray-50">
            <button
              type="button"
              onClick={closeModal}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100"
            >
              취소
            </button>
            <button
              onClick={handleSubmit}
              disabled={isPending}
              className={`px-4 py-2 text-white rounded-lg disabled:opacity-50 ${
                action === 'approve'
                  ? 'bg-green-600 hover:bg-green-700'
                  : 'bg-red-600 hover:bg-red-700'
              }`}
            >
              {isPending
                ? '처리 중...'
                : action === 'approve'
                ? '승인'
                : '반려'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
