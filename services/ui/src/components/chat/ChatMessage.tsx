import React from 'react'
import { ChatMessage as ChatMessageType } from '@/types/chat'
import { formatTimeAgo } from '@/utils'
import { Badge, LoadingSpinner, StarRating } from '@/components/common'
import { RenderSpecDispatcher } from '@/components/renderers'
import { useChatStore } from '@/store/chatStore'

interface ChatMessageProps {
  message: ChatMessageType
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user'
  const setMessageRating = useChatStore((state) => state.setMessageRating)
  const currentSessionId = useChatStore((state) => state.currentSessionId)

  const handleRate = (rating: number) => {
    if (currentSessionId) {
      setMessageRating(currentSessionId, message.id, rating)
    }
  }

  return (
    <div className="space-y-4">
      {/* Message bubble */}
      <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Message Content */}
        <div className={`flex-1 ${isUser ? 'flex justify-end' : ''}`}>
          <div
            className={`inline-block max-w-[80%] rounded-lg px-4 py-3 ${
              isUser
                ? 'bg-primary text-white'
                : 'bg-white border border-slate-200 text-slate-800'
            }`}
          >
            <div className="text-sm whitespace-pre-wrap break-words">{message.content}</div>

            {/* Status */}
            <div
              className={`flex items-center gap-2 mt-2 text-xs ${
                isUser ? 'text-blue-100' : 'text-slate-500'
              }`}
            >
              {message.status === 'sending' && (
                <>
                  <LoadingSpinner size="sm" className="text-current" />
                  <span>Sending...</span>
                </>
              )}
              {message.status === 'error' && (
                <Badge variant="error">Failed to send</Badge>
              )}
              {message.status === 'success' && (
                <span>{formatTimeAgo(message.timestamp)}</span>
              )}
            </div>

            {/* Star Rating for AI messages */}
            {!isUser && message.status === 'success' && (
              <div className="flex justify-end mt-2">
                <StarRating
                  rating={message.rating || 0}
                  onRate={handleRate}
                />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Rendered Result */}
      {message.renderSpec && (message.queryResult || message.renderSpec.type === 'clarification' || message.renderSpec.type === 'text') && (
        <div className="w-full">
          <RenderSpecDispatcher
            renderSpec={message.renderSpec}
            queryResult={message.queryResult || {
              requestId: '',
              status: 'success',
              data: { rows: [] },
              metadata: { executionTimeMs: 0, rowsReturned: 0 }
            }}
          />
        </div>
      )}
    </div>
  )
}

export default ChatMessage
