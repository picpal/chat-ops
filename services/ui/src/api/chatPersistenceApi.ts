import axios from 'axios'

const CHAT_API_BASE = '/api/v1/chat'

// Separate client without baseURL to use Vite proxy
const chatApiClient = axios.create({
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request/Response interfaces
export interface UserLoginRequest {
  email: string
  displayName?: string
}

export interface UserLoginResponse {
  userId: string
  email: string
  displayName: string
  isNewUser: boolean
}

export interface SessionCreateRequest {
  title: string
  subtitle?: string
  icon?: string
}

export interface SessionResponse {
  sessionId: string
  title: string
  subtitle: string
  icon: string
  status: string
  createdAt: string
  updatedAt: string
  messages?: MessageResponse[]
}

export interface MessageCreateRequest {
  messageId: string
  role: string
  content: string
  renderSpec?: unknown
  queryResult?: unknown
  queryPlan?: unknown
  status?: string
}

export interface MessageResponse {
  messageId: string
  role: string
  content: string
  renderSpec: unknown
  queryResult: unknown
  queryPlan: unknown
  status: string
  createdAt: string
}

export const chatPersistenceApi = {
  /**
   * User login/creation
   */
  loginUser: async (email: string, displayName?: string): Promise<UserLoginResponse> => {
    const response = await chatApiClient.post<UserLoginResponse>(
      `${CHAT_API_BASE}/users/login`,
      { email, displayName }
    )
    return response.data
  },

  /**
   * Get all sessions for a user
   */
  getSessions: async (userId: string): Promise<SessionResponse[]> => {
    const response = await chatApiClient.get<SessionResponse[]>(
      `${CHAT_API_BASE}/sessions`,
      {
        headers: {
          'X-User-Id': userId,
        },
      }
    )
    return response.data
  },

  /**
   * Create a new session
   */
  createSession: async (
    userId: string,
    request: SessionCreateRequest
  ): Promise<SessionResponse> => {
    const response = await chatApiClient.post<SessionResponse>(
      `${CHAT_API_BASE}/sessions`,
      request,
      {
        headers: {
          'X-User-Id': userId,
        },
      }
    )
    return response.data
  },

  /**
   * Get a session with all messages
   */
  getSessionWithMessages: async (sessionId: string): Promise<SessionResponse> => {
    const response = await chatApiClient.get<SessionResponse>(
      `${CHAT_API_BASE}/sessions/${sessionId}`
    )
    return response.data
  },

  /**
   * Delete a session
   */
  deleteSession: async (sessionId: string): Promise<void> => {
    await chatApiClient.delete(`${CHAT_API_BASE}/sessions/${sessionId}`)
  },

  /**
   * Update session title
   */
  updateSessionTitle: async (
    sessionId: string,
    title: string
  ): Promise<SessionResponse> => {
    const response = await chatApiClient.patch<SessionResponse>(
      `${CHAT_API_BASE}/sessions/${sessionId}`,
      { title }
    )
    return response.data
  },

  /**
   * Add a message to a session
   */
  addMessage: async (
    sessionId: string,
    message: MessageCreateRequest
  ): Promise<MessageResponse> => {
    const response = await chatApiClient.post<MessageResponse>(
      `${CHAT_API_BASE}/sessions/${sessionId}/messages`,
      message
    )
    return response.data
  },
}
