import { useEffect, useState, useRef } from 'react'
import { useChatStore } from '@/store'
import { chatPersistenceApi } from '@/api/chatPersistenceApi'

const CHAT_USER_ID_KEY = 'chatUserId'

export const useInitializeChat = () => {
  const { setCurrentUser, loadSessionsFromServer, currentUserId } = useChatStore()
  const [isInitializing, setIsInitializing] = useState(true)
  const initializedRef = useRef(false)

  useEffect(() => {
    // Skip if already initialized (useRef to prevent double execution in StrictMode)
    if (initializedRef.current) return
    initializedRef.current = true

    const initChat = async () => {
      setIsInitializing(true)
      try {
        // 1. Check localStorage for existing userId
        let userId = localStorage.getItem(CHAT_USER_ID_KEY)

        if (!userId) {
          // 2. Create guest user
          const guestEmail = `guest-${Date.now()}@chatops.local`
          try {
            const response = await chatPersistenceApi.loginUser(guestEmail, 'Guest')
            userId = response.userId
            localStorage.setItem(CHAT_USER_ID_KEY, userId)
            console.log('[useInitializeChat] Guest user created:', userId)
          } catch (error) {
            console.error('[useInitializeChat] Failed to create guest user:', error)
            // Continue without server sync
            setIsInitializing(false)
            return
          }
        }

        // 3. Set current user in store
        setCurrentUser(userId)

        // 4. Load sessions from server
        await loadSessionsFromServer()

        console.log('[useInitializeChat] Chat initialized with userId:', userId)
      } catch (error) {
        console.error('[useInitializeChat] Failed to initialize chat:', error)
      } finally {
        setIsInitializing(false)
      }
    }

    initChat()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    isInitialized: initializedRef.current,
    isInitializing,
    currentUserId,
  }
}
