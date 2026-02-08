/** Settings API 타입 */

export interface QualityAnswerRagStatus {
  enabled: boolean
  minRating: number
  storedCount: number
  lastUpdated: string | null
}

export interface QualityAnswerRagUpdate {
  enabled?: boolean
  minRating?: number
}

export interface SettingResponse {
  key: string
  value: Record<string, unknown>
  description: string | null
  updatedAt: string | null
}
