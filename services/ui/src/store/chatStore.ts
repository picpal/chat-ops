import { create } from 'zustand'
import { ChatMessage, ConversationSession, SessionCategory } from '@/types/chat'

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
}))
