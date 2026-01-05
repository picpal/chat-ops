import { ChatRequest, ChatResponse } from './chat'
import { QueryResult } from './queryResult'

export interface ApiError {
  message: string
  code?: string
  details?: any
}

export interface ApiResponse<T> {
  data?: T
  error?: ApiError
  status: number
}

// AI Orchestrator API types
export type SendMessageRequest = ChatRequest
export type SendMessageResponse = ChatResponse

// Core API types
export interface GetPageRequest {
  queryToken: string
}

export type GetPageResponse = QueryResult

// Health check response
export interface HealthCheckResponse {
  status: 'ok' | 'error'
  timestamp: string
  version?: string
}
