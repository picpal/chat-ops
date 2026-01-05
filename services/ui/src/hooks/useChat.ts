import { useMutation } from '@tanstack/react-query'
import { aiOrchestratorApi } from '@/api'
import { useChatStore } from '@/store'
import { ChatMessage, ChatRequest } from '@/types/chat'

export const useChat = () => {
  const { currentSessionId, addMessage, updateMessage, setLoading, setError } =
    useChatStore()

  const sendMessageMutation = useMutation({
    mutationFn: aiOrchestratorApi.sendMessage,
    onMutate: async (variables: ChatRequest) => {
      setLoading(true)
      setError(null)

      // Create optimistic user message
      const userMessageId = `msg-${Date.now()}-user`
      const userMessage: ChatMessage = {
        id: userMessageId,
        role: 'user',
        content: variables.message,
        timestamp: new Date().toISOString(),
        status: 'sending',
      }

      if (currentSessionId) {
        addMessage(currentSessionId, userMessage)
      }

      return { userMessageId }
    },
    onSuccess: (data, _variables, context) => {
      if (!currentSessionId) return

      // Update user message status
      if (context?.userMessageId) {
        updateMessage(currentSessionId, context.userMessageId, {
          status: 'success',
        })
      }

      // Add assistant message with renderSpec and queryResult
      const assistantMessage: ChatMessage = {
        id: `msg-${Date.now()}-assistant`,
        role: 'assistant',
        content: data.aiMessage || '',
        renderSpec: data.renderSpec,
        queryResult: data.queryResult,
        timestamp: data.timestamp,
        status: 'success',
      }

      addMessage(currentSessionId, assistantMessage)
      setLoading(false)
    },
    onError: (error: Error, _variables, context) => {
      const errorMessage =
        error instanceof Error ? error.message : 'Failed to send message'
      setError(errorMessage)
      setLoading(false)

      // Update user message status to error
      if (currentSessionId && context?.userMessageId) {
        updateMessage(currentSessionId, context.userMessageId, {
          status: 'error',
        })
      }
    },
  })

  return {
    sendMessage: sendMessageMutation.mutate,
    isLoading: sendMessageMutation.isPending,
    error: sendMessageMutation.error,
    isSuccess: sendMessageMutation.isSuccess,
  }
}
