import { http, HttpResponse } from 'msw'
import { mockChatResponse, mockTableResult } from './fixtures'

export const handlers = [
  // AI Orchestrator endpoints
  http.post('/api/v1/chat', () => {
    return HttpResponse.json(mockChatResponse)
  }),

  http.get('/health', () => {
    return HttpResponse.json({ status: 'healthy', version: '1.0.0' })
  }),

  // Core API endpoints
  http.get('/api/v1/query/page/:token', () => {
    return HttpResponse.json(mockTableResult)
  }),

  http.get('/api/v1/query/health', () => {
    return HttpResponse.json({ status: 'healthy' })
  }),
]
