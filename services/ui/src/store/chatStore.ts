import { create } from 'zustand'
import { ChatMessage, ConversationSession, SessionCategory } from '@/types/chat'
import { ClarificationRenderSpec } from '@/types/renderSpec'
import { applyFilters, formatFilterDescription } from '@/utils/filterUtils'
import {
  aggregateData,
  formatAggregationResultMarkdown,
  formatAggregationDescription,
  type Aggregation,
} from '@/utils/aggregateUtils'
import type { QueryFilter } from '@/types/queryPlan'

interface ChatState {
  currentSessionId: string | null
  sessions: ConversationSession[]
  isLoading: boolean
  error: string | null

  // Actions
  createSession: (title: string, subtitle?: string, icon?: string) => string
  setCurrentSession: (sessionId: string) => void
  addMessage: (sessionId: string, message: ChatMessage) => void
  updateMessage: (
    sessionId: string,
    messageId: string,
    updates: Partial<ChatMessage>
  ) => void
  deleteSession: (sessionId: string) => void
  clearSessions: () => void
  setLoading: (isLoading: boolean) => void
  setError: (error: string | null) => void
  getCurrentSession: () => ConversationSession | null
  handleClarificationSelect: (
    optionIndex: number,
    option: string,
    metadata?: ClarificationRenderSpec['metadata']
  ) => void
}

const getSessionCategory = (timestamp: string): SessionCategory => {
  const now = new Date()
  const messageDate = new Date(timestamp)
  const diffInHours = (now.getTime() - messageDate.getTime()) / (1000 * 60 * 60)

  if (diffInHours < 24) return 'today'
  if (diffInHours < 48) return 'yesterday'
  if (diffInHours < 168) return 'previous7days' // 7 days
  return 'older'
}

export const useChatStore = create<ChatState>((set, get) => ({
  currentSessionId: null,
  sessions: [],
  isLoading: false,
  error: null,

  createSession: (title: string, subtitle?: string, icon?: string) => {
    const timestamp = new Date().toISOString()
    const newSession: ConversationSession = {
      id: `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      title,
      subtitle,
      icon: icon || 'chat',
      timestamp,
      category: getSessionCategory(timestamp),
      messages: [],
    }

    set((state) => ({
      sessions: [newSession, ...state.sessions],
      currentSessionId: newSession.id,
    }))

    return newSession.id
  },

  setCurrentSession: (sessionId: string) => {
    set({ currentSessionId: sessionId })
  },

  addMessage: (sessionId: string, message: ChatMessage) => {
    set((state) => ({
      sessions: state.sessions.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              messages: [...session.messages, message],
              timestamp: message.timestamp, // Update session timestamp
              category: getSessionCategory(message.timestamp),
            }
          : session
      ),
    }))
  },

  updateMessage: (sessionId: string, messageId: string, updates: Partial<ChatMessage>) => {
    set((state) => ({
      sessions: state.sessions.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              messages: session.messages.map((msg) =>
                msg.id === messageId ? { ...msg, ...updates } : msg
              ),
            }
          : session
      ),
    }))
  },

  deleteSession: (sessionId: string) => {
    set((state) => ({
      sessions: state.sessions.filter((s) => s.id !== sessionId),
      currentSessionId:
        state.currentSessionId === sessionId ? null : state.currentSessionId,
    }))
  },

  clearSessions: () => {
    set({ sessions: [], currentSessionId: null })
  },

  setLoading: (isLoading: boolean) => set({ isLoading }),

  setError: (error: string | null) => set({ error }),

  getCurrentSession: () => {
    const state = get()
    return state.sessions.find((s) => s.id === state.currentSessionId) || null
  },

  handleClarificationSelect: (
    optionIndex: number,
    option: string,
    metadata?: ClarificationRenderSpec['metadata']
  ) => {
    const state = get()
    const { currentSessionId } = state

    if (!currentSessionId) {
      console.error('[chatStore] No current session for clarification')
      return
    }

    const currentSession = state.sessions.find((s) => s.id === currentSessionId)
    if (!currentSession) {
      console.error('[chatStore] Session not found:', currentSessionId)
      return
    }

    console.log('[chatStore] handleClarificationSelect:', {
      optionIndex,
      option,
      metadata,
    })

    // metadata에서 대상 결과 인덱스 추출
    const targetResultIndices = metadata?.targetResultIndices || []

    // 대상 결과 인덱스 결정 (옵션 인덱스에 해당하는 targetResultIndex 사용)
    const targetMessageIndex = targetResultIndices[optionIndex]

    if (targetMessageIndex === undefined) {
      console.error('[chatStore] No target index for option:', optionIndex)
      // 에러 메시지 추가
      const errorMessage: ChatMessage = {
        id: `msg-${Date.now()}-assistant`,
        role: 'assistant',
        content: '선택한 결과를 찾을 수 없습니다.',
        timestamp: new Date().toISOString(),
        status: 'error',
      }
      get().addMessage(currentSessionId, errorMessage)
      return
    }

    console.log('[chatStore] Finding target message:', {
      targetMessageIndex,
      totalMessages: currentSession.messages.length,
    })

    // targetMessageIndex로 대상 메시지 찾기
    // targetResultIndices는 전체 messages 배열 기준 인덱스
    const targetMessage = currentSession.messages[targetMessageIndex]

    if (!targetMessage?.queryResult?.data?.rows) {
      console.error('[chatStore] Target message not found:', targetMessageIndex)
      const errorMessage: ChatMessage = {
        id: `msg-${Date.now()}-assistant`,
        role: 'assistant',
        content: '처리할 대상 결과를 찾을 수 없습니다.',
        timestamp: new Date().toISOString(),
        status: 'error',
      }
      get().addMessage(currentSessionId, errorMessage)
      return
    }

    const originalData = targetMessage.queryResult.data.rows

    // 사용자 선택 메시지 추가
    const userSelectionMessage: ChatMessage = {
      id: `msg-${Date.now()}-user`,
      role: 'user',
      content: option,
      timestamp: new Date().toISOString(),
      status: 'success',
    }
    get().addMessage(currentSessionId, userSelectionMessage)

    // aggregationType에 따라 분기 처리
    if (metadata?.aggregationType === 'aggregate_local') {
      // 집계 처리
      const pendingAggregations = metadata?.pendingAggregations || []
      const aggregations = pendingAggregations as Aggregation[]
      const aggregationResult = aggregateData(originalData, aggregations)
      const aggDesc = formatAggregationDescription(aggregations)
      const resultMarkdown = formatAggregationResultMarkdown(aggregationResult, aggregations)

      console.log('[chatStore] Aggregation applied:', {
        originalCount: originalData.length,
        aggregationResult,
        aggregations,
      })

      // 집계 결과를 새 메시지로 추가
      const assistantMessage: ChatMessage = {
        id: `msg-${Date.now() + 1}-assistant`,
        role: 'assistant',
        content: `${originalData.length}건의 데이터를 집계했습니다. (${aggDesc})`,
        renderSpec: {
          type: 'text',
          requestId: `req-${Date.now()}`,
          text: {
            content: resultMarkdown,
            format: 'markdown',
          },
        },
        timestamp: new Date().toISOString(),
        status: 'success',
      }

      get().addMessage(currentSessionId, assistantMessage)
    } else {
      // 기존 필터 처리
      const pendingFilters = metadata?.pendingFilters || []
      const filters = pendingFilters as QueryFilter[]
      const filteredData = applyFilters(originalData, filters)
      const filterDesc = formatFilterDescription(filters)

      console.log('[chatStore] Filter applied:', {
        originalCount: originalData.length,
        filteredCount: filteredData.length,
        filters,
      })

      // 필터링된 결과를 새 메시지로 추가
      const assistantMessage: ChatMessage = {
        id: `msg-${Date.now() + 1}-assistant`,
        role: 'assistant',
        content: `${filteredData.length}건의 결과를 필터링했습니다. (${filterDesc})`,
        renderSpec: targetMessage.renderSpec, // 원본과 같은 렌더 타입 사용
        queryResult: {
          ...targetMessage.queryResult,
          data: {
            ...targetMessage.queryResult.data,
            rows: filteredData,
          },
          metadata: {
            ...targetMessage.queryResult.metadata,
            rowsReturned: filteredData.length,
          },
        },
        timestamp: new Date().toISOString(),
        status: 'success',
      }

      get().addMessage(currentSessionId, assistantMessage)
    }
  },
}))
