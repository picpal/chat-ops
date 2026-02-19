/**
 * 로그 분석 설정 타입
 */

export interface LogPath {
  id: string
  name: string
  path: string
  enabled: boolean
}

export interface MaskingPattern {
  name: string
  regex: string
  replacement: string
}

export interface MaskingConfig {
  enabled: boolean
  patterns: MaskingPattern[]
}

export interface LogAnalysisDefaults {
  maxLines: number
  timeRangeMinutes: number
}

export interface LogAnalysisSettings {
  enabled: boolean
  paths: LogPath[]
  masking: MaskingConfig
  defaults: LogAnalysisDefaults
}

export interface LogAnalysisSettingsUpdate {
  enabled?: boolean
  masking?: MaskingConfig
  defaults?: LogAnalysisDefaults
}

export interface LogAnalysisStatusResponse {
  enabled: boolean
  pathCount: number
  activePathCount: number
  maskingEnabled: boolean
}

export interface LogPathCreate {
  name: string
  path: string
  enabled?: boolean
}

export interface LogPathUpdate {
  name?: string
  path?: string
  enabled?: boolean
}

export interface PathTestResult {
  success: boolean
  message: string
  fileSize?: number
  lastModified?: string
}
