/**
 * RAG 문서 관리 API 클라이언트
 */
import { aiClient } from './client'
import {
  DocumentResponse,
  PaginatedDocuments,
  DocumentStats,
  DocumentListParams,
  DocumentCreateRequest,
  DocumentUpdateRequest,
  DocumentReviewRequest,
  BulkReviewRequest,
  BulkOperationResult,
  EmbeddingRefreshRequest,
  EmbeddingRefreshResult,
  DocumentUploadData,
} from '@/types/document'

const BASE_PATH = '/api/v1/documents'

export const documentsApi = {
  /**
   * 문서 목록 조회
   */
  listDocuments: async (params: DocumentListParams = {}): Promise<PaginatedDocuments> => {
    const searchParams = new URLSearchParams()

    if (params.page) searchParams.set('page', params.page.toString())
    if (params.page_size) searchParams.set('page_size', params.page_size.toString())
    if (params.doc_type) searchParams.set('doc_type', params.doc_type)
    if (params.status) searchParams.set('status', params.status)
    if (params.has_embedding !== undefined) searchParams.set('has_embedding', params.has_embedding.toString())
    if (params.search) searchParams.set('search', params.search)
    if (params.sort_by) searchParams.set('sort_by', params.sort_by)
    if (params.sort_order) searchParams.set('sort_order', params.sort_order)

    const query = searchParams.toString()
    const url = query ? `${BASE_PATH}?${query}` : BASE_PATH

    const response = await aiClient.get<PaginatedDocuments>(url)
    return response.data
  },

  /**
   * 승인 대기 문서 목록 조회
   */
  listPendingDocuments: async (params: Omit<DocumentListParams, 'status'> = {}): Promise<PaginatedDocuments> => {
    const searchParams = new URLSearchParams()

    if (params.page) searchParams.set('page', params.page.toString())
    if (params.page_size) searchParams.set('page_size', params.page_size.toString())
    if (params.doc_type) searchParams.set('doc_type', params.doc_type)
    if (params.search) searchParams.set('search', params.search)
    if (params.sort_by) searchParams.set('sort_by', params.sort_by)
    if (params.sort_order) searchParams.set('sort_order', params.sort_order)

    const query = searchParams.toString()
    const url = query ? `${BASE_PATH}/pending?${query}` : `${BASE_PATH}/pending`

    const response = await aiClient.get<PaginatedDocuments>(url)
    return response.data
  },

  /**
   * 문서 통계 조회
   */
  getStats: async (): Promise<DocumentStats> => {
    const response = await aiClient.get<DocumentStats>(`${BASE_PATH}/stats`)
    return response.data
  },

  /**
   * 단일 문서 조회
   */
  getDocument: async (id: number): Promise<DocumentResponse> => {
    const response = await aiClient.get<DocumentResponse>(`${BASE_PATH}/${id}`)
    return response.data
  },

  /**
   * 문서 생성
   */
  createDocument: async (data: DocumentCreateRequest): Promise<DocumentResponse> => {
    const response = await aiClient.post<DocumentResponse>(BASE_PATH, data)
    return response.data
  },

  /**
   * 문서 수정
   */
  updateDocument: async (id: number, data: DocumentUpdateRequest): Promise<DocumentResponse> => {
    const response = await aiClient.put<DocumentResponse>(`${BASE_PATH}/${id}`, data)
    return response.data
  },

  /**
   * 문서 삭제
   */
  deleteDocument: async (id: number): Promise<void> => {
    await aiClient.delete(`${BASE_PATH}/${id}`)
  },

  /**
   * 문서 승인/반려
   */
  reviewDocument: async (id: number, data: DocumentReviewRequest): Promise<DocumentResponse> => {
    const response = await aiClient.post<DocumentResponse>(`${BASE_PATH}/${id}/review`, data)
    return response.data
  },

  /**
   * 대량 문서 승인/반려
   */
  bulkReview: async (data: BulkReviewRequest): Promise<BulkOperationResult> => {
    const response = await aiClient.post<BulkOperationResult>(`${BASE_PATH}/bulk/review`, data)
    return response.data
  },

  /**
   * 대량 문서 삭제
   */
  bulkDelete: async (ids: number[]): Promise<BulkOperationResult> => {
    const response = await aiClient.post<BulkOperationResult>(`${BASE_PATH}/bulk/delete`, { ids })
    return response.data
  },

  /**
   * 임베딩 갱신
   */
  refreshEmbeddings: async (data: EmbeddingRefreshRequest = {}): Promise<EmbeddingRefreshResult> => {
    const response = await aiClient.post<EmbeddingRefreshResult>(`${BASE_PATH}/embeddings/refresh`, data)
    return response.data
  },

  /**
   * 파일 업로드로 문서 생성
   */
  uploadDocument: async (data: DocumentUploadData): Promise<DocumentResponse> => {
    const formData = new FormData()
    formData.append('file', data.file)
    formData.append('doc_type', data.doc_type)
    if (data.title) formData.append('title', data.title)
    if (data.skip_embedding) formData.append('skip_embedding', 'true')
    if (data.status) formData.append('status', data.status)
    if (data.submitted_by) formData.append('submitted_by', data.submitted_by)

    // axios가 FormData를 감지하면 자동으로 Content-Type과 boundary를 설정
    const response = await aiClient.post<DocumentResponse>(
      `${BASE_PATH}/upload`,
      formData
    )
    return response.data
  },
}
