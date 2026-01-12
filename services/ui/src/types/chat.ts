import { RenderSpec } from './renderSpec'
import { QueryResult } from './queryResult'
import { QueryPlan } from './queryPlan'

export interface ChatRequest {
  message: string
  sessionId?: string
  conversationHistory?: ChatMessage[]
}

export interface ChatResponse {
  requestId: string
  renderSpec: RenderSpec
  queryResult: QueryResult
  queryPlan: QueryPlan  // 이번 쿼리 조건 (후속 질문용)
  aiMessage?: string
  timestamp: string
}

export type MessageRole = 'user' | 'assistant'
export type MessageStatus = 'sending' | 'success' | 'error'

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  renderSpec?: RenderSpec
  queryResult?: QueryResult
  queryPlan?: QueryPlan  // 이번 쿼리 조건 (후속 질문용)
  timestamp: string
  status?: MessageStatus
}

export type SessionCategory = 'today' | 'yesterday' | 'previous7days' | 'older'

export interface ConversationSession {
  id: string
  title: string
  subtitle?: string
  icon?: string
  timestamp: string
  category: SessionCategory
  messages: ChatMessage[]
}
