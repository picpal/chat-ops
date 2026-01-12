/**
 * 대량 작업 도구바 컴포넌트
 */
import { useDocumentStore } from '@/store/documentStore'
import { useBulkDelete } from '@/hooks/useDocuments'

export function BulkActions() {
  const { selectedIds, clearSelection, openModal } = useDocumentStore()
  const bulkDeleteMutation = useBulkDelete()

  const handleBulkDelete = async () => {
    if (!window.confirm(`선택한 ${selectedIds.length}개의 문서를 삭제하시겠습니까?`)) {
      return
    }

    try {
      const result = await bulkDeleteMutation.mutateAsync(selectedIds)
      if (result.failed_count > 0) {
        alert(`${result.success_count}개 삭제 성공, ${result.failed_count}개 삭제 실패`)
      } else {
        alert(`${result.success_count}개 문서가 삭제되었습니다.`)
      }
      clearSelection()
    } catch (error) {
      alert('삭제 중 오류가 발생했습니다.')
    }
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="font-medium text-blue-900">{selectedIds.length}개 선택됨</span>
        <button onClick={clearSelection} className="text-sm text-blue-600 hover:text-blue-800">
          선택 해제
        </button>
      </div>

      <div className="flex items-center gap-2">
        {/* 대량 승인 */}
        <button
          onClick={() => openModal('bulk-review')}
          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
        >
          승인
        </button>

        {/* 대량 반려 */}
        <button
          onClick={() => {
            useDocumentStore.setState({
              modalType: 'bulk-review',
            })
          }}
          className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors text-sm"
        >
          반려
        </button>

        {/* 대량 삭제 */}
        <button
          onClick={handleBulkDelete}
          disabled={bulkDeleteMutation.isPending}
          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm disabled:opacity-50"
        >
          {bulkDeleteMutation.isPending ? '삭제 중...' : '삭제'}
        </button>
      </div>
    </div>
  )
}
