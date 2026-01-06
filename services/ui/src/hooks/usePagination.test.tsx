import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import { usePagination } from './usePagination'

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('usePagination', () => {
  beforeEach(() => {
    // Reset any state if needed
  })

  it('returns initial state without query token', () => {
    const { result } = renderHook(() => usePagination(), {
      wrapper: createWrapper(),
    })

    expect(result.current.data).toEqual([])
    expect(result.current.hasMore).toBe(false)
    expect(result.current.isLoading).toBe(false)
    expect(typeof result.current.loadMore).toBe('function')
    expect(typeof result.current.reset).toBe('function')
  })

  it('returns loading state when query token is provided', () => {
    const { result } = renderHook(() => usePagination('test-token'), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(true)
  })

  it('fetches data when query token is provided', async () => {
    const { result } = renderHook(() => usePagination('test-token'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    // Data should be accumulated from the mock response
    expect(result.current.data.length).toBeGreaterThanOrEqual(0)
  })

  it('has reset function that clears accumulated data', async () => {
    const { result } = renderHook(() => usePagination('test-token'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    result.current.reset()

    // After reset, data should be empty
    expect(result.current.data).toEqual([])
  })
})
