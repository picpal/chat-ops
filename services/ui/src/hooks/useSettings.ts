import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { settingsApi } from '@/api/settings'
import type { QualityAnswerRagUpdate } from '@/types/settings'

export const settingsKeys = {
  all: ['settings'] as const,
  qualityAnswerRag: () => [...settingsKeys.all, 'quality-answer-rag'] as const,
  setting: (key: string) => [...settingsKeys.all, key] as const,
}

/**
 * Quality Answer RAG 상태 조회 훅
 */
export function useQualityAnswerRagStatus() {
  return useQuery({
    queryKey: settingsKeys.qualityAnswerRag(),
    queryFn: () => settingsApi.getQualityAnswerRagStatus(),
  })
}

/**
 * Quality Answer RAG 설정 업데이트 훅
 */
export function useUpdateQualityAnswerRag() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: QualityAnswerRagUpdate) => settingsApi.updateQualityAnswerRag(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.qualityAnswerRag() })
    },
  })
}

/**
 * 일반 설정 조회 훅
 */
export function useSetting(key: string) {
  return useQuery({
    queryKey: settingsKeys.setting(key),
    queryFn: () => settingsApi.getSetting(key),
    enabled: !!key,
  })
}

/**
 * 일반 설정 업데이트 훅
 */
export function useUpdateSetting() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: Record<string, unknown> }) =>
      settingsApi.updateSetting(key, value),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: settingsKeys.setting(variables.key) })
    },
  })
}
