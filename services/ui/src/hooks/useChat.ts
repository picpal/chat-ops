import { useMutation } from '@tanstack/react-query'
import { aiOrchestratorApi } from '@/api'
import { useChatStore } from '@/store'
import { ChatMessage, ChatRequest } from '@/types/chat'
import { applyFilters, formatFilterDescription } from '@/utils/filterUtils'
import {
  aggregateData,
  formatAggregationResultMarkdown,
  formatAggregationDescription,
  type Aggregation,
} from '@/utils/aggregateUtils'
import type { QueryFilter } from '@/types/queryPlan'

export const useChat = () => {
  const { currentSessionId, addMessage, updateMessage, setLoading, setError, getCurrentSession } =
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

      // Handle filter_local response: 클라이언트에서 이전 결과 필터링
      if (data.renderSpec?.type === 'filter_local') {
        const currentSession = getCurrentSession()
        const filterLocalSpec = data.renderSpec as { filter: QueryFilter[]; targetResultIndex: number }
        const filters = filterLocalSpec.filter || []
        const targetIndex = filterLocalSpec.targetResultIndex

        // Debug: filter_local 응답 로깅
        console.log('[useChat] filter_local response:', {
          filters,
          targetIndex,
          sessionMessages: currentSession?.messages.length,
        })

        // 이전 결과에서 queryResult가 있는 assistant 메시지들 찾기
        const resultMessages = currentSession?.messages.filter(
          (msg) => msg.role === 'assistant' && msg.queryResult?.data?.rows
        ) || []

        // Debug: resultMessages 로깅
        console.log('[useChat] resultMessages found:', {
          count: resultMessages.length,
          messages: currentSession?.messages.map((m, i) => ({
            index: i,
            role: m.role,
            hasQueryResult: !!m.queryResult,
            hasRows: !!m.queryResult?.data?.rows,
            rowsCount: m.queryResult?.data?.rows?.length,
          })),
        })

        // targetIndex 처리:
        // - 음수(-1): 가장 최근 결과 사용
        // - 양수: 현재 세션의 resultMessages 배열에서 해당 인덱스 찾기
        //   (백엔드가 conversationHistory 기준 인덱스를 반환하므로, 안전하게 마지막 결과 사용)
        let targetMessage = resultMessages[resultMessages.length - 1] // 기본: 마지막 결과

        if (targetIndex >= 0 && targetIndex < resultMessages.length) {
          targetMessage = resultMessages[targetIndex]
        }

        if (targetMessage?.queryResult?.data?.rows) {
          const originalData = targetMessage.queryResult.data.rows
          const filteredData = applyFilters(originalData, filters)
          const filterDesc = formatFilterDescription(filters)

          // 필터링된 결과를 새 메시지로 추가
          const assistantMessage: ChatMessage = {
            id: `msg-${Date.now()}-assistant`,
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
            queryPlan: data.queryPlan,
            timestamp: data.timestamp,
            status: 'success',
          }

          addMessage(currentSessionId, assistantMessage)
        } else {
          // 대상 결과를 찾지 못한 경우
          const errorMessage: ChatMessage = {
            id: `msg-${Date.now()}-assistant`,
            role: 'assistant',
            content: '필터링할 이전 결과를 찾을 수 없습니다.',
            timestamp: data.timestamp,
            status: 'error',
          }
          addMessage(currentSessionId, errorMessage)
        }

        setLoading(false)
        return
      }

      // Handle aggregate_local response: 클라이언트에서 이전 결과 집계
      if (data.renderSpec?.type === 'aggregate_local') {
        const currentSession = getCurrentSession()
        const aggregateLocalSpec = data.renderSpec as {
          aggregations: Aggregation[]
          targetResultIndex: number
        }
        const aggregations = aggregateLocalSpec.aggregations || []
        const targetIndex = aggregateLocalSpec.targetResultIndex

        // Debug: aggregate_local 응답 로깅
        console.log('[useChat] aggregate_local response:', {
          aggregations,
          targetIndex,
          sessionMessages: currentSession?.messages.length,
        })

        // 이전 결과에서 queryResult가 있는 assistant 메시지들 찾기
        const resultMessages =
          currentSession?.messages.filter(
            (msg) => msg.role === 'assistant' && msg.queryResult?.data?.rows
          ) || []

        // Debug: resultMessages 로깅
        console.log('[useChat] resultMessages for aggregation:', {
          count: resultMessages.length,
          messages: currentSession?.messages.map((m, i) => ({
            index: i,
            role: m.role,
            hasQueryResult: !!m.queryResult,
            hasRows: !!m.queryResult?.data?.rows,
            rowsCount: m.queryResult?.data?.rows?.length,
          })),
        })

        // targetIndex 처리:
        // - 음수(-1): 가장 최근 결과 사용
        // - 양수: 현재 세션의 resultMessages 배열에서 해당 인덱스 찾기
        let targetMessage = resultMessages[resultMessages.length - 1] // 기본: 마지막 결과

        if (targetIndex >= 0 && targetIndex < resultMessages.length) {
          targetMessage = resultMessages[targetIndex]
        }

        if (targetMessage?.queryResult?.data?.rows) {
          const originalData = targetMessage.queryResult.data.rows
          const aggregationResult = aggregateData(originalData, aggregations)
          const aggDesc = formatAggregationDescription(aggregations)
          const resultMarkdown = formatAggregationResultMarkdown(aggregationResult, aggregations)

          console.log('[useChat] Aggregation result:', {
            originalCount: originalData.length,
            aggregationResult,
          })

          // 집계 결과를 새 메시지로 추가
          const assistantMessage: ChatMessage = {
            id: `msg-${Date.now()}-assistant`,
            role: 'assistant',
            content: `${originalData.length}건의 데이터를 집계했습니다. (${aggDesc})`,
            renderSpec: {
              type: 'text',
              requestId: data.renderSpec.requestId || `req-${Date.now()}`,
              text: {
                content: resultMarkdown,
                format: 'markdown',
              },
            },
            queryPlan: data.queryPlan,
            timestamp: data.timestamp,
            status: 'success',
          }

          addMessage(currentSessionId, assistantMessage)
        } else {
          // 대상 결과를 찾지 못한 경우
          const errorMessage: ChatMessage = {
            id: `msg-${Date.now()}-assistant`,
            role: 'assistant',
            content: '집계할 이전 결과를 찾을 수 없습니다.',
            timestamp: data.timestamp,
            status: 'error',
          }
          addMessage(currentSessionId, errorMessage)
        }

        setLoading(false)
        return
      }

      // 일반 응답 처리: Add assistant message with renderSpec, queryResult, queryPlan
      const assistantMessage: ChatMessage = {
        id: `msg-${Date.now()}-assistant`,
        role: 'assistant',
        content: data.aiMessage || '',
        renderSpec: data.renderSpec,
        queryResult: data.queryResult,
        queryPlan: data.queryPlan,  // 후속 질문에서 이전 쿼리 조건 참조용
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
