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
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <h2 className="text-xl font-bold text-slate-800 mb-2">
            No active session
          </h2>
          <p className="text-slate-600">
            Click "New Analysis" in the sidebar to start a conversation
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Session Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <h2 className="text-lg font-bold text-slate-900">{currentSession.title}</h2>
        {currentSession.subtitle && (
          <p className="text-sm text-slate-500 mt-1">{currentSession.subtitle}</p>
        )}
      </div>

      {/* Messages */}
      <div className="space-y-6">
        {currentSession.messages.length === 0 && !isLoading && (
          <div className="text-center py-12">
            <p className="text-slate-500">
              No messages yet. Start by asking a question below.
            </p>
          </div>
        )}

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
    </div>
  )
}

export default ChatInterface
