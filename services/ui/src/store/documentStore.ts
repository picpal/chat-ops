/**
 * RAG 문서 관리 상태 스토어 (Zustand)
 */
import { create } from 'zustand'
import { DocType, DocumentStatus, DocumentListItem } from '@/types/document'

// 필터 상태
interface DocumentFilters {
  doc_type: DocType | null
  status: DocumentStatus | null
  has_embedding: boolean | null
  search: string
  sort_by: 'created_at' | 'updated_at' | 'title' | 'doc_type' | 'id' | 'status'
  sort_order: 'asc' | 'desc'
}

// 모달 상태
type ModalType = 'create' | 'edit' | 'detail' | 'review' | 'bulk-review' | 'delete' | null

interface DocumentState {
  // 필터 상태
  filters: DocumentFilters

  // 페이지네이션
  page: number
  pageSize: number

  // 선택된 문서
  selectedIds: number[]
  selectedDocument: DocumentListItem | null

  // 모달 상태
  modalType: ModalType

  // 뷰 모드 (전체 / 대기)
  viewMode: 'all' | 'pending'

  // Actions
  setFilters: (filters: Partial<DocumentFilters>) => void
  resetFilters: () => void
  setPage: (page: number) => void
  setPageSize: (size: number) => void

  // 선택 관련
  toggleSelection: (id: number) => void
  selectAll: (ids: number[]) => void
  clearSelection: () => void
  setSelectedDocument: (doc: DocumentListItem | null) => void

  // 모달 관련
  openModal: (type: ModalType, doc?: DocumentListItem) => void
  closeModal: () => void

  // 뷰 모드
  setViewMode: (mode: 'all' | 'pending') => void
}

const initialFilters: DocumentFilters = {
  doc_type: null,
  status: null,
  has_embedding: null,
  search: '',
  sort_by: 'created_at',
  sort_order: 'desc',
}

export const useDocumentStore = create<DocumentState>((set) => ({
  // 초기 상태
  filters: initialFilters,
  page: 1,
  pageSize: 20,
  selectedIds: [],
  selectedDocument: null,
  modalType: null,
  viewMode: 'all',

  // 필터 액션
  setFilters: (newFilters) =>
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
      page: 1, // 필터 변경 시 첫 페이지로
    })),

  resetFilters: () =>
    set({
      filters: initialFilters,
      page: 1,
    }),

  // 페이지네이션 액션
  setPage: (page) => set({ page }),
  setPageSize: (pageSize) => set({ pageSize, page: 1 }),

  // 선택 액션
  toggleSelection: (id) =>
    set((state) => ({
      selectedIds: state.selectedIds.includes(id)
        ? state.selectedIds.filter((i) => i !== id)
        : [...state.selectedIds, id],
    })),

  selectAll: (ids) => set({ selectedIds: ids }),

  clearSelection: () => set({ selectedIds: [] }),

  setSelectedDocument: (doc) => set({ selectedDocument: doc }),

  // 모달 액션
  openModal: (type, doc) =>
    set({
      modalType: type,
      selectedDocument: doc || null,
    }),

  closeModal: () =>
    set({
      modalType: null,
      selectedDocument: null,
    }),

  // 뷰 모드 액션
  setViewMode: (mode) =>
    set({
      viewMode: mode,
      page: 1,
      selectedIds: [],
    }),
}))
