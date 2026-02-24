/**
 * RAG 문서 관리자 페이지
 */
import { useState } from 'react'
import { useDocumentStore } from '@/store/documentStore'
import { DocumentStats } from './DocumentStats'
import { DocumentFilters } from './DocumentFilters'
import { DocumentList } from './DocumentList'
import { BulkActions } from './BulkActions'
import { DocumentDetailModal } from './DocumentDetailModal'
import { DocumentForm } from './DocumentForm'
import { ReviewModal } from './ReviewModal'

export function AdminPage() {
  const { viewMode, setViewMode, modalType, selectedIds } = useDocumentStore()
  const [showStats, setShowStats] = useState(true)

  return (
    <div className="h-full overflow-y-auto bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">RAG 문서 관리</h1>
              <p className="mt-1 text-sm text-gray-500">
                문서 승인, 관리 및 임베딩 상태를 확인합니다
              </p>
            </div>
            <div className="flex items-center gap-4">
              {/* 통계 토글 */}
              <button
                onClick={() => setShowStats(!showStats)}
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                {showStats ? '통계 숨기기' : '통계 보기'}
              </button>
              {/* 새 문서 버튼 */}
              <button
                onClick={() => useDocumentStore.getState().openModal('create')}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                + 새 문서
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* 통계 대시보드 */}
        {showStats && <DocumentStats />}

        {/* 뷰 모드 탭 */}
        <div className="mt-6 border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setViewMode('all')}
              className={`pb-4 px-1 border-b-2 font-medium text-sm ${
                viewMode === 'all'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              전체 문서
            </button>
            <button
              onClick={() => setViewMode('pending')}
              className={`pb-4 px-1 border-b-2 font-medium text-sm ${
                viewMode === 'pending'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              승인 대기
            </button>
          </nav>
        </div>

        {/* 필터 */}
        <div className="mt-6">
          <DocumentFilters />
        </div>

        {/* 대량 작업 도구바 */}
        {selectedIds.length > 0 && (
          <div className="mt-4">
            <BulkActions />
          </div>
        )}

        {/* 문서 목록 */}
        <div className="mt-4">
          <DocumentList />
        </div>
      </main>

      {/* 모달들 */}
      {modalType === 'detail' && <DocumentDetailModal />}
      {(modalType === 'create' || modalType === 'edit') && <DocumentForm />}
      {(modalType === 'review' || modalType === 'bulk-review') && <ReviewModal />}
    </div>
  )
}
