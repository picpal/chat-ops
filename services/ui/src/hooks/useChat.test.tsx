import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import { useChat } from './useChat'
import { useChatStore } from '@/store'

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useChat', () => {
  beforeEach(() => {
    useChatStore.setState({
      currentSessionId: 'session-1',
      sessions: [
        {
          id: 'session-1',
          title: 'Test',
          timestamp: new Date().toISOString(),
          category: 'today',
          messages: [],
        },
      ],
      isLoading: false,
      error: null,
    })
  })

  it('returns initial state', () => {
    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() })

    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()
    expect(result.current.isSuccess).toBe(false)
    expect(typeof result.current.sendMessage).toBe('function')
  })

  it('has sendMessage function', () => {
    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() })

    expect(result.current.sendMessage).toBeDefined()
    expect(typeof result.current.sendMessage).toBe('function')
  })

  it('has isLoading property', () => {
    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() })

    expect(typeof result.current.isLoading).toBe('boolean')
  })

  it('has error property', () => {
    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() })

    expect(result.current.error).toBeNull()
  })

  it('has isSuccess property', () => {
    const { result } = renderHook(() => useChat(), { wrapper: createWrapper() })

    expect(typeof result.current.isSuccess).toBe('boolean')
    expect(result.current.isSuccess).toBe(false)
  })
})
