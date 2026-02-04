/**
 * RAG 문서 관리 React Query Hooks
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { documentsApi } from '@/api/documents'
import {
  DocumentListParams,
  DocumentCreateRequest,
  DocumentUpdateRequest,
  DocumentReviewRequest,
  BulkReviewRequest,
  EmbeddingRefreshRequest,
  DocumentUploadData,
} from '@/types/document'

// Query Keys
export const documentKeys = {
  all: ['documents'] as const,
  lists: () => [...documentKeys.all, 'list'] as const,
  list: (params: DocumentListParams) => [...documentKeys.lists(), params] as const,
  pending: (params?: Omit<DocumentListParams, 'status'>) => [...documentKeys.all, 'pending', params] as const,
  details: () => [...documentKeys.all, 'detail'] as const,
  detail: (id: number) => [...documentKeys.details(), id] as const,
  stats: () => [...documentKeys.all, 'stats'] as const,
}

/**
 * 문서 목록 조회
 */
export function useDocuments(params: DocumentListParams = {}) {
  return useQuery({
    queryKey: documentKeys.list(params),
    queryFn: () => documentsApi.listDocuments(params),
  })
}

/**
 * 승인 대기 문서 목록 조회
 */
export function usePendingDocuments(params: Omit<DocumentListParams, 'status'> = {}) {
  return useQuery({
    queryKey: documentKeys.pending(params),
    queryFn: () => documentsApi.listPendingDocuments(params),
  })
}

/**
 * 문서 통계 조회
 */
export function useDocumentStats() {
  return useQuery({
    queryKey: documentKeys.stats(),
    queryFn: documentsApi.getStats,
  })
}

/**
 * 단일 문서 조회
 */
export function useDocument(id: number | null) {
  return useQuery({
    queryKey: documentKeys.detail(id!),
    queryFn: () => documentsApi.getDocument(id!),
    enabled: id !== null,
  })
}

/**
 * 문서 생성 mutation
 */
export function useCreateDocument() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: DocumentCreateRequest) => documentsApi.createDocument(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.all })
    },
  })
}

/**
 * 파일 업로드로 문서 생성 mutation
 */
export function useUploadDocument() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: DocumentUploadData) => documentsApi.uploadDocument(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.all })
    },
  })
}

/**
 * 문서 수정 mutation
 */
export function useUpdateDocument() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: DocumentUpdateRequest }) =>
      documentsApi.updateDocument(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: documentKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: documentKeys.lists() })
    },
  })
}

/**
 * 문서 삭제 mutation
 */
export function useDeleteDocument() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => documentsApi.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.all })
    },
  })
}

/**
 * 문서 승인/반려 mutation
 */
export function useReviewDocument() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: DocumentReviewRequest }) =>
      documentsApi.reviewDocument(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: documentKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: documentKeys.all })
    },
  })
}

/**
 * 대량 승인/반려 mutation
 */
export function useBulkReview() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: BulkReviewRequest) => documentsApi.bulkReview(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.all })
    },
  })
}

/**
 * 대량 삭제 mutation
 */
export function useBulkDelete() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (ids: number[]) => documentsApi.bulkDelete(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.all })
    },
  })
}

/**
 * 임베딩 갱신 mutation
 */
export function useRefreshEmbeddings() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: EmbeddingRefreshRequest) => documentsApi.refreshEmbeddings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.all })
    },
  })
}
