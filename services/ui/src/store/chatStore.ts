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
import {
  chatPersistenceApi,
  SessionResponse,
  MessageResponse,
} from '@/api/chatPersistenceApi'
import { ratingsApi } from '@/api/ratings'
import { aiOrchestratorApi } from '@/api/aiOrchestrator'

// localStorage key for persisting current session
const CURRENT_SESSION_KEY = 'chatCurrentSessionId'

interface ChatState {
  currentSessionId: string | null
  sessions: ConversationSession[]
  isLoading: boolean
  error: string | null

  // Server sync state
  currentUserId: string | null
  isSyncing: boolean

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
  ) => Promise<void>

  // Rating
  setMessageRating: (sessionId: string, messageId: string, rating: number) => void

  // Server sync actions
  setCurrentUser: (userId: string) => void
  loadSessionsFromServer: () => Promise<void>
  loadSessionMessages: (sessionId: string) => Promise<void>
  syncCreateSession: (title: string, subtitle?: string, icon?: string) => Promise<string>
  syncAddMessage: (sessionId: string, message: ChatMessage) => Promise<void>
  syncDeleteSession: (sessionId: string) => Promise<void>
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

// Helper to convert server response to local session format
const convertServerSessionToLocal = (
  serverSession: SessionResponse
): ConversationSession => {
  const timestamp = serverSession.updatedAt || serverSession.createdAt
  return {
    id: serverSession.sessionId,
    title: serverSession.title,
    subtitle: serverSession.subtitle,
    icon: serverSession.icon,
    timestamp,
    category: getSessionCategory(timestamp),
    messages: serverSession.messages
      ? serverSession.messages.map(convertServerMessageToLocal)
      : [],
  }
}

// Helper to convert server message to local format
const convertServerMessageToLocal = (
  serverMessage: MessageResponse
): ChatMessage => {
  return {
    id: serverMessage.messageId,
    role: serverMessage.role as 'user' | 'assistant',
    content: serverMessage.content,
    renderSpec: serverMessage.renderSpec as ChatMessage['renderSpec'],
    queryResult: serverMessage.queryResult as ChatMessage['queryResult'],
    queryPlan: serverMessage.queryPlan as ChatMessage['queryPlan'],
    timestamp: serverMessage.createdAt,
    status: (serverMessage.status as ChatMessage['status']) || 'success',
  }
}

export const useChatStore = create<ChatState>((set, get) => ({
  currentSessionId: null,
  sessions: [],
  isLoading: false,
  error: null,

  // Server sync state
  currentUserId: null,
  isSyncing: false,

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
    // Persist to localStorage for restoration after refresh
    localStorage.setItem(CURRENT_SESSION_KEY, sessionId)
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

  handleClarificationSelect: async (
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

    // ========================================
    // timerange_selection: 원래 질문 + 선택한 기간으로 새 API 요청
    // ========================================
    if (metadata?.clarificationType === 'timerange_selection' && metadata?.originalQuestion) {
      const originalQuestion = metadata.originalQuestion
      const combinedMessage = `${option} ${originalQuestion}`

      console.log('[chatStore] Timerange selection - sending combined message:', combinedMessage)

      // 사용자 선택 메시지 추가
      const userMessage: ChatMessage = {
        id: `msg-${Date.now()}-user`,
        role: 'user',
        content: option,
        timestamp: new Date().toISOString(),
        status: 'success',
      }
      get().addMessage(currentSessionId, userMessage)

      // 로딩 메시지 추가
      const loadingMessageId = `msg-${Date.now() + 1}-assistant`
      const loadingMessage: ChatMessage = {
        id: loadingMessageId,
        role: 'assistant',
        content: '조회 중...',
        timestamp: new Date().toISOString(),
        status: 'sending',
      }
      get().addMessage(currentSessionId, loadingMessage)

      try {
        // 대화 이력 구성
        const conversationHistory = currentSession.messages.map((msg) => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp,
          renderSpec: msg.renderSpec,
          queryResult: msg.queryResult,
          queryPlan: msg.queryPlan,
        }))

        // API 호출 (원래 질문 + 선택한 기간)
        const response = await aiOrchestratorApi.sendMessage({
          message: combinedMessage,
          sessionId: currentSessionId,
          conversationHistory: conversationHistory,
        })

        // 성공 메시지로 업데이트
        get().updateMessage(currentSessionId, loadingMessageId, {
          content: response.aiMessage || `'${combinedMessage}'에 대한 결과입니다.`,
          renderSpec: response.renderSpec,
          queryResult: response.queryResult,
          queryPlan: response.queryPlan,
          status: 'success',
        })

        // 서버 동기화
        const { currentUserId } = get()
        if (currentUserId) {
          const updatedMessage = get().sessions
            .find((s) => s.id === currentSessionId)
            ?.messages.find((m) => m.id === loadingMessageId)
          if (updatedMessage) {
            get().syncAddMessage(currentSessionId, userMessage)
            get().syncAddMessage(currentSessionId, updatedMessage)
          }
        }
      } catch (error) {
        console.error('[chatStore] Timerange selection API error:', error)
        get().updateMessage(currentSessionId, loadingMessageId, {
          content: '조회 중 오류가 발생했습니다.',
          status: 'error',
        })
      }
      return
    }

    // ========================================
    // 기존 로직: filter_local / aggregate_local
    // ========================================
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

  // Rating
  setMessageRating: (sessionId: string, messageId: string, rating: number) => {
    // Optimistic update
    set((state) => ({
      sessions: state.sessions.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              messages: session.messages.map((msg) =>
                msg.id === messageId ? { ...msg, rating } : msg
              ),
            }
          : session
      ),
    }))

    // Find the message to get its requestId (use message id as requestId)
    const session = get().sessions.find((s) => s.id === sessionId)
    const message = session?.messages.find((m) => m.id === messageId)
    const requestId = message?.id || messageId

    // Persist to backend
    ratingsApi
      .saveRating({ requestId, rating, sessionId })
      .then(() => {
        console.log('[chatStore] Rating saved:', requestId, rating)
      })
      .catch((error) => {
        console.error('[chatStore] Failed to save rating:', error)
      })
  },

  // Server sync actions
  setCurrentUser: (userId: string) => {
    set({ currentUserId: userId })
  },

  loadSessionsFromServer: async () => {
    const { currentUserId } = get()
    if (!currentUserId) {
      console.warn('[chatStore] No current user ID, cannot load sessions')
      return
    }

    try {
      const serverSessions = await chatPersistenceApi.getSessions(currentUserId)
      const localSessions = serverSessions.map(convertServerSessionToLocal)

      // Sort by updatedAt descending
      localSessions.sort(
        (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      )

      set({ sessions: localSessions })
      console.log('[chatStore] Loaded sessions from server:', localSessions.length)
    } catch (error) {
      console.error('[chatStore] Failed to load sessions from server:', error)
      // Keep existing local sessions on error
    }
  },

  loadSessionMessages: async (sessionId: string) => {
    const { sessions } = get()
    const existingSession = sessions.find((s) => s.id === sessionId)

    // Skip if messages already loaded
    if (existingSession && existingSession.messages.length > 0) {
      console.log('[chatStore] Session already has messages, skipping load')
      return
    }

    try {
      const serverSession = await chatPersistenceApi.getSessionWithMessages(sessionId)
      const messages = serverSession.messages
        ? serverSession.messages.map(convertServerMessageToLocal)
        : []

      // Load ratings for the session and map to messages
      try {
        const ratings = await ratingsApi.getRatingsBySession(sessionId)
        if (ratings && ratings.length > 0) {
          const ratingsMap = new Map(ratings.map((r) => [r.requestId, r.rating]))
          messages.forEach((msg) => {
            const rating = ratingsMap.get(msg.id)
            if (rating !== undefined) {
              msg.rating = rating
            }
          })
          console.log('[chatStore] Loaded ratings for session:', sessionId, ratings.length)
        }
      } catch (ratingError) {
        console.warn('[chatStore] Failed to load ratings, messages will display without ratings:', ratingError)
      }

      set((state) => ({
        sessions: state.sessions.map((session) =>
          session.id === sessionId ? { ...session, messages } : session
        ),
      }))
      console.log('[chatStore] Loaded messages for session:', sessionId, messages.length)
    } catch (error) {
      console.error('[chatStore] Failed to load session messages:', error)
    }
  },

  syncCreateSession: async (
    title: string,
    subtitle?: string,
    icon?: string
  ): Promise<string> => {
    const { currentUserId, createSession } = get()

    // Optimistic update - create session locally first
    const localSessionId = createSession(title, subtitle, icon)

    if (!currentUserId) {
      console.warn('[chatStore] No current user ID, session created locally only')
      return localSessionId
    }

    try {
      const serverSession = await chatPersistenceApi.createSession(currentUserId, {
        title,
        subtitle,
        icon,
      })

      // Update local session with server ID
      set((state) => ({
        sessions: state.sessions.map((session) =>
          session.id === localSessionId
            ? { ...session, id: serverSession.sessionId }
            : session
        ),
        currentSessionId:
          state.currentSessionId === localSessionId
            ? serverSession.sessionId
            : state.currentSessionId,
      }))

      console.log('[chatStore] Session synced to server:', serverSession.sessionId)
      return serverSession.sessionId
    } catch (error) {
      console.error('[chatStore] Failed to sync session to server:', error)
      // Keep local session even if server sync fails
      return localSessionId
    }
  },

  syncAddMessage: async (sessionId: string, message: ChatMessage): Promise<void> => {
    const { currentUserId } = get()

    // Optimistic update is already done by addMessage
    // This just syncs to server

    if (!currentUserId) {
      console.warn('[chatStore] No current user ID, message stored locally only')
      return
    }

    try {
      await chatPersistenceApi.addMessage(sessionId, {
        messageId: message.id,
        role: message.role,
        content: message.content,
        renderSpec: message.renderSpec,
        queryResult: message.queryResult,
        queryPlan: message.queryPlan,
        status: message.status,
      })
      console.log('[chatStore] Message synced to server:', message.id)
    } catch (error) {
      console.error('[chatStore] Failed to sync message to server:', error)
      // Message is already in local state, just log the error
    }
  },

  syncDeleteSession: async (sessionId: string): Promise<void> => {
    const { deleteSession, currentSessionId } = get()

    // Clear localStorage if deleting the current session
    if (currentSessionId === sessionId) {
      localStorage.removeItem(CURRENT_SESSION_KEY)
    }

    // Optimistic update - delete locally first
    deleteSession(sessionId)

    try {
      await chatPersistenceApi.deleteSession(sessionId)
      console.log('[chatStore] Session deleted from server:', sessionId)
    } catch (error) {
      console.error('[chatStore] Failed to delete session from server:', error)
      // Session is already removed from local state
    }
  },
}))
