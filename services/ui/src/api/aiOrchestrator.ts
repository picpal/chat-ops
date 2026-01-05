import { aiClient } from './client'
import { ChatRequest, ChatResponse } from '@/types/chat'
import { HealthCheckResponse } from '@/types/api'

export const aiOrchestratorApi = {
  /**
   * Send a chat message to the AI Orchestrator
   */
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await aiClient.post<ChatResponse>('/api/v1/chat', request)
    return response.data
  },

  /**
   * Check AI Orchestrator health status
   */
  healthCheck: async (): Promise<HealthCheckResponse> => {
    const response = await aiClient.get<HealthCheckResponse>('/health')
    return response.data
  },

  /**
   * Test connectivity to AI Orchestrator
   */
  testConnection: async (): Promise<{ status: string; message: string }> => {
    const response = await aiClient.get<{ status: string; message: string }>(
      '/api/v1/chat/test'
    )
    return response.data
  },
}
