import { aiClient } from './client'
import type {
  QualityAnswerRagStatus,
  QualityAnswerRagUpdate,
  SettingResponse,
} from '@/types/settings'

export const settingsApi = {
  /**
   * Quality Answer RAG 상태 조회
   */
  getQualityAnswerRagStatus: async (): Promise<QualityAnswerRagStatus> => {
    const response = await aiClient.get('/api/v1/settings/quality-answer-rag/status')
    return response.data
  },

  /**
   * Quality Answer RAG 설정 업데이트
   */
  updateQualityAnswerRag: async (data: QualityAnswerRagUpdate): Promise<SettingResponse> => {
    const response = await aiClient.put('/api/v1/settings/quality-answer-rag', data)
    return response.data
  },

  /**
   * 일반 설정 조회
   */
  getSetting: async (key: string): Promise<SettingResponse> => {
    const response = await aiClient.get(`/api/v1/settings/${key}`)
    return response.data
  },

  /**
   * 일반 설정 업데이트
   */
  updateSetting: async (key: string, value: Record<string, unknown>): Promise<SettingResponse> => {
    const response = await aiClient.put(`/api/v1/settings/${key}`, { value })
    return response.data
  },
}
