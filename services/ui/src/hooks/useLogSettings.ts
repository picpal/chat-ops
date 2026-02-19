/**
 * 로그 분석 설정 React Query 훅
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { logSettingsApi } from '@/api/logSettings'
import type {
  LogAnalysisSettingsUpdate,
  LogPathCreate,
  LogPathUpdate,
} from '@/types/logSettings'

export const logSettingsKeys = {
  all: ['logSettings'] as const,
  settings: () => [...logSettingsKeys.all, 'settings'] as const,
  status: () => [...logSettingsKeys.all, 'status'] as const,
  paths: () => [...logSettingsKeys.all, 'paths'] as const,
}

/**
 * 로그 분석 설정 조회 훅
 */
export function useLogSettings() {
  return useQuery({
    queryKey: logSettingsKeys.settings(),
    queryFn: () => logSettingsApi.getSettings(),
  })
}

/**
 * 로그 분석 상태 조회 훅
 */
export function useLogSettingsStatus() {
  return useQuery({
    queryKey: logSettingsKeys.status(),
    queryFn: () => logSettingsApi.getStatus(),
  })
}

/**
 * 로그 분석 설정 업데이트 훅
 */
export function useUpdateLogSettings() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: LogAnalysisSettingsUpdate) => logSettingsApi.updateSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: logSettingsKeys.settings() })
      queryClient.invalidateQueries({ queryKey: logSettingsKeys.status() })
    },
  })
}

/**
 * 로그 경로 목록 조회 훅
 */
export function useLogPaths() {
  return useQuery({
    queryKey: logSettingsKeys.paths(),
    queryFn: () => logSettingsApi.getPaths(),
  })
}

/**
 * 로그 경로 추가 훅
 */
export function useAddLogPath() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: LogPathCreate) => logSettingsApi.addPath(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: logSettingsKeys.paths() })
      queryClient.invalidateQueries({ queryKey: logSettingsKeys.settings() })
      queryClient.invalidateQueries({ queryKey: logSettingsKeys.status() })
    },
  })
}

/**
 * 로그 경로 수정 훅
 */
export function useUpdateLogPath() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ pathId, data }: { pathId: string; data: LogPathUpdate }) =>
      logSettingsApi.updatePath(pathId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: logSettingsKeys.paths() })
      queryClient.invalidateQueries({ queryKey: logSettingsKeys.settings() })
      queryClient.invalidateQueries({ queryKey: logSettingsKeys.status() })
    },
  })
}

/**
 * 로그 경로 삭제 훅
 */
export function useDeleteLogPath() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (pathId: string) => logSettingsApi.deletePath(pathId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: logSettingsKeys.paths() })
      queryClient.invalidateQueries({ queryKey: logSettingsKeys.settings() })
      queryClient.invalidateQueries({ queryKey: logSettingsKeys.status() })
    },
  })
}

/**
 * 로그 경로 테스트 훅
 */
export function useTestLogPath() {
  return useMutation({
    mutationFn: (pathId: string) => logSettingsApi.testPath(pathId),
  })
}
