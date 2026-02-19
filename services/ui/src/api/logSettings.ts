/**
 * 로그 설정 API 클라이언트
 */

import { aiClient } from './client'
import type {
  LogAnalysisSettings,
  LogAnalysisSettingsUpdate,
  LogAnalysisStatusResponse,
  LogPath,
  LogPathCreate,
  LogPathUpdate,
  PathTestResult,
} from '@/types/logSettings'

const BASE_PATH = '/api/v1/settings/log-analysis'

export const logSettingsApi = {
  /**
   * 로그 분석 상태 조회
   */
  getStatus: async (): Promise<LogAnalysisStatusResponse> => {
    const response = await aiClient.get(`${BASE_PATH}/status`)
    return response.data
  },

  /**
   * 전체 설정 조회
   */
  getSettings: async (): Promise<LogAnalysisSettings> => {
    const response = await aiClient.get(BASE_PATH)
    return response.data
  },

  /**
   * 설정 업데이트
   */
  updateSettings: async (update: LogAnalysisSettingsUpdate): Promise<LogAnalysisSettings> => {
    const response = await aiClient.put(BASE_PATH, update)
    return response.data
  },

  /**
   * 경로 목록 조회
   */
  getPaths: async (): Promise<LogPath[]> => {
    const response = await aiClient.get(`${BASE_PATH}/paths`)
    return response.data
  },

  /**
   * 경로 추가
   */
  addPath: async (data: LogPathCreate): Promise<LogPath> => {
    const response = await aiClient.post(`${BASE_PATH}/paths`, data)
    return response.data
  },

  /**
   * 경로 수정
   */
  updatePath: async (pathId: string, data: LogPathUpdate): Promise<LogPath> => {
    const response = await aiClient.put(`${BASE_PATH}/paths/${pathId}`, data)
    return response.data
  },

  /**
   * 경로 삭제
   */
  deletePath: async (pathId: string): Promise<void> => {
    await aiClient.delete(`${BASE_PATH}/paths/${pathId}`)
  },

  /**
   * 경로 테스트
   */
  testPath: async (pathId: string): Promise<PathTestResult> => {
    const response = await aiClient.post(`${BASE_PATH}/paths/${pathId}/test`)
    return response.data
  },
}
