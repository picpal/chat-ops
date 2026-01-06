import { describe, it, expect, beforeEach } from 'vitest'
import { useChatStore } from './chatStore'
import { ChatMessage } from '@/types/chat'

describe('chatStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useChatStore.setState({
      currentSessionId: null,
      sessions: [],
      isLoading: false,
      error: null,
    })
  })

  describe('createSession', () => {
    it('creates a new session with generated ID', () => {
      const { createSession } = useChatStore.getState()

      const sessionId = createSession('Test Session', 'Subtitle', 'chart')

      expect(sessionId).toMatch(/^session-\d+-[a-z0-9]+$/)

      const state = useChatStore.getState()
      expect(state.sessions).toHaveLength(1)
      expect(state.sessions[0].title).toBe('Test Session')
      expect(state.sessions[0].subtitle).toBe('Subtitle')
      expect(state.sessions[0].icon).toBe('chart')
      expect(state.currentSessionId).toBe(sessionId)
    })

    it('adds session to beginning of list', () => {
      const { createSession } = useChatStore.getState()

      createSession('First')
      createSession('Second')

      const { sessions } = useChatStore.getState()
      expect(sessions[0].title).toBe('Second')
      expect(sessions[1].title).toBe('First')
    })

    it('assigns correct category based on timestamp', () => {
      const { createSession } = useChatStore.getState()

      createSession('Today Session')

      const { sessions } = useChatStore.getState()
      expect(sessions[0].category).toBe('today')
    })

    it('uses default icon when not provided', () => {
      const { createSession } = useChatStore.getState()

      createSession('Test')

      const { sessions } = useChatStore.getState()
      expect(sessions[0].icon).toBe('chat')
    })
  })

  describe('setCurrentSession', () => {
    it('updates current session ID', () => {
      const { createSession, setCurrentSession } = useChatStore.getState()

      createSession('Test')
      setCurrentSession('different-id')

      expect(useChatStore.getState().currentSessionId).toBe('different-id')
    })
  })

  describe('addMessage', () => {
    it('adds message to correct session', () => {
      const { createSession, addMessage } = useChatStore.getState()
      const sessionId = createSession('Test')

      const message: ChatMessage = {
        id: 'msg-1',
        role: 'user',
        content: 'Hello',
        timestamp: new Date().toISOString(),
        status: 'success',
      }

      addMessage(sessionId, message)

      const { sessions } = useChatStore.getState()
      const session = sessions.find((s) => s.id === sessionId)
      expect(session?.messages).toHaveLength(1)
      expect(session?.messages[0].content).toBe('Hello')
    })

    it('updates session timestamp on new message', () => {
      const { createSession, addMessage } = useChatStore.getState()
      const sessionId = createSession('Test')

      const newTimestamp = new Date(Date.now() + 1000).toISOString()
      const message: ChatMessage = {
        id: 'msg-1',
        role: 'user',
        content: 'Hello',
        timestamp: newTimestamp,
        status: 'success',
      }

      addMessage(sessionId, message)

      const { sessions } = useChatStore.getState()
      expect(sessions[0].timestamp).toBe(newTimestamp)
    })

    it('does not affect other sessions', () => {
      const { createSession, addMessage } = useChatStore.getState()
      const sessionId1 = createSession('First')
      const sessionId2 = createSession('Second')

      const message: ChatMessage = {
        id: 'msg-1',
        role: 'user',
        content: 'Hello',
        timestamp: new Date().toISOString(),
        status: 'success',
      }

      addMessage(sessionId1, message)

      const { sessions } = useChatStore.getState()
      const session2 = sessions.find((s) => s.id === sessionId2)
      expect(session2?.messages).toHaveLength(0)
    })
  })

  describe('updateMessage', () => {
    it('updates specific message in session', () => {
      const { createSession, addMessage, updateMessage } = useChatStore.getState()
      const sessionId = createSession('Test')

      const message: ChatMessage = {
        id: 'msg-1',
        role: 'user',
        content: 'Hello',
        timestamp: new Date().toISOString(),
        status: 'sending',
      }

      addMessage(sessionId, message)
      updateMessage(sessionId, 'msg-1', { status: 'success' })

      const { sessions } = useChatStore.getState()
      const session = sessions.find((s) => s.id === sessionId)
      expect(session?.messages[0].status).toBe('success')
    })

    it('updates content of message', () => {
      const { createSession, addMessage, updateMessage } = useChatStore.getState()
      const sessionId = createSession('Test')

      const message: ChatMessage = {
        id: 'msg-1',
        role: 'assistant',
        content: 'Original',
        timestamp: new Date().toISOString(),
        status: 'success',
      }

      addMessage(sessionId, message)
      updateMessage(sessionId, 'msg-1', { content: 'Updated content' })

      const { sessions } = useChatStore.getState()
      const session = sessions.find((s) => s.id === sessionId)
      expect(session?.messages[0].content).toBe('Updated content')
    })
  })

  describe('deleteSession', () => {
    it('removes session from list', () => {
      const { createSession, deleteSession } = useChatStore.getState()

      const sessionId = createSession('Test')
      expect(useChatStore.getState().sessions).toHaveLength(1)

      deleteSession(sessionId)
      expect(useChatStore.getState().sessions).toHaveLength(0)
    })

    it('clears currentSessionId if deleted session was current', () => {
      const { createSession, deleteSession } = useChatStore.getState()

      const sessionId = createSession('Test')
      expect(useChatStore.getState().currentSessionId).toBe(sessionId)

      deleteSession(sessionId)
      expect(useChatStore.getState().currentSessionId).toBeNull()
    })

    it('keeps currentSessionId if different session deleted', () => {
      const { createSession, deleteSession, setCurrentSession } = useChatStore.getState()

      const sessionId1 = createSession('First')
      const sessionId2 = createSession('Second')
      setCurrentSession(sessionId1)

      deleteSession(sessionId2)
      expect(useChatStore.getState().currentSessionId).toBe(sessionId1)
    })
  })

  describe('clearSessions', () => {
    it('removes all sessions', () => {
      const { createSession, clearSessions } = useChatStore.getState()

      createSession('Session 1')
      createSession('Session 2')
      expect(useChatStore.getState().sessions).toHaveLength(2)

      clearSessions()
      expect(useChatStore.getState().sessions).toHaveLength(0)
      expect(useChatStore.getState().currentSessionId).toBeNull()
    })
  })

  describe('getCurrentSession', () => {
    it('returns current session or null', () => {
      const { createSession, getCurrentSession } = useChatStore.getState()

      expect(getCurrentSession()).toBeNull()

      const sessionId = createSession('Test')
      expect(useChatStore.getState().getCurrentSession()?.id).toBe(sessionId)
    })
  })

  describe('setLoading and setError', () => {
    it('updates loading state', () => {
      const { setLoading } = useChatStore.getState()

      setLoading(true)
      expect(useChatStore.getState().isLoading).toBe(true)

      setLoading(false)
      expect(useChatStore.getState().isLoading).toBe(false)
    })

    it('updates error state', () => {
      const { setError } = useChatStore.getState()

      setError('Test error')
      expect(useChatStore.getState().error).toBe('Test error')

      setError(null)
      expect(useChatStore.getState().error).toBeNull()
    })
  })
})
