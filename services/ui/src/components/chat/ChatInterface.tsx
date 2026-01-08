import React, { useEffect, useRef } from 'react'
import { useChatStore } from '@/store'
import ChatMessage from './ChatMessage'
import { LoadingSpinner } from '@/components/common'

const ChatInterface: React.FC = () => {
  const { currentSessionId, sessions, isLoading } = useChatStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const currentSession = sessions.find((s) => s.id === currentSessionId)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [currentSession?.messages])

  if (!currentSessionId || !currentSession) {
    return (
      <div className="absolute inset-0 flex items-center justify-center -mt-16">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-stone-800 mb-2">
            No active session
          </h2>
          <p className="text-stone-500">
            Click "새 채팅" in the sidebar to start a conversation
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {currentSession.messages.map((message) => (
        <ChatMessage key={message.id} message={message} />
      ))}

      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner size="lg" />
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  )
}

export default ChatInterface
