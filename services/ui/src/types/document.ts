/**
 * RAG 문서 관리 관련 타입 정의
 */

// 문서 타입
export type DocType = 'entity' | 'business_logic' | 'error_code' | 'faq'

// 문서 상태
export type DocumentStatus = 'pending' | 'active' | 'rejected'

// 단일 문서 응답
export interface DocumentResponse {
  id: number
  doc_type: DocType
  title: string
  content: string
  metadata: Record<string, unknown>
  status: DocumentStatus
  has_embedding: boolean
  submitted_by: string | null
  submitted_at: string | null
  reviewed_by: string | null
  reviewed_at: string | null
  rejection_reason: string | null
  created_at: string | null
  updated_at: string | null
}

// 문서 목록 아이템 (content 축약)
export interface DocumentListItem {
  id: number
  doc_type: DocType
  title: string
  content_preview: string
  status: DocumentStatus
  has_embedding: boolean
  submitted_by: string | null
  submitted_at: string | null
  reviewed_by: string | null
  reviewed_at: string | null
  created_at: string | null
  updated_at: string | null
}

// 페이지네이션된 문서 목록
export interface PaginatedDocuments {
  items: DocumentListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

// 문서 통계
export interface DocumentStats {
  total_count: number
  by_type: Record<DocType, number>
  by_status: Record<DocumentStatus, number>
  embedding_status: {
    with_embedding: number
    without_embedding: number
  }
  last_updated: string | null
}

// === Request Types ===

// 문서 생성 요청
export interface DocumentCreateRequest {
  doc_type: DocType
  title: string
  content: string
  metadata?: Record<string, unknown>
  skip_embedding?: boolean
  status?: DocumentStatus
  submitted_by?: string
}

// 문서 수정 요청
export interface DocumentUpdateRequest {
  doc_type?: DocType
  title?: string
  content?: string
  metadata?: Record<string, unknown>
  regenerate_embedding?: boolean
}

// 문서 승인/반려 요청
export interface DocumentReviewRequest {
  action: 'approve' | 'reject'
  reviewed_by: string
  rejection_reason?: string
}

// 대량 승인/반려 요청
export interface BulkReviewRequest {
  ids: number[]
  action: 'approve' | 'reject'
  reviewed_by: string
  rejection_reason?: string
}

// 대량 작업 결과
export interface BulkOperationResult {
  success_count: number
  failed_count: number
  failed_ids: number[]
  errors: Array<{ id?: number; error: string }>
}

// 임베딩 갱신 요청
export interface EmbeddingRefreshRequest {
  force_all?: boolean
  doc_types?: DocType[]
  batch_size?: number
}

// 임베딩 갱신 결과
export interface EmbeddingRefreshResult {
  processed: number
  updated: number
  failed: number
  remaining: number
}

// 문서 목록 조회 파라미터
export interface DocumentListParams {
  page?: number
  page_size?: number
  doc_type?: DocType
  status?: DocumentStatus
  has_embedding?: boolean
  search?: string
  sort_by?: 'created_at' | 'updated_at' | 'title' | 'doc_type' | 'id' | 'status'
  sort_order?: 'asc' | 'desc'
}

// 문서 타입 라벨 (한글)
export const DOC_TYPE_LABELS: Record<DocType, string> = {
  entity: '엔티티',
  business_logic: '비즈니스 로직',
  error_code: '에러 코드',
  faq: 'FAQ',
}

// 문서 상태 라벨 (한글)
export const STATUS_LABELS: Record<DocumentStatus, string> = {
  pending: '승인 대기',
  active: '승인됨',
  rejected: '반려됨',
}

// 문서 상태 색상
export const STATUS_COLORS: Record<DocumentStatus, string> = {
  pending: 'yellow',
  active: 'green',
  rejected: 'red',
}
