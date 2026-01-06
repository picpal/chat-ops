import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useModal } from './useModal'
import { useUIStore } from '@/store'

describe('useModal', () => {
  beforeEach(() => {
    useUIStore.setState({
      sidebarCollapsed: false,
      modal: { isOpen: false, type: null },
    })
  })

  it('returns initial closed state', () => {
    const { result } = renderHook(() => useModal())

    expect(result.current.isOpen).toBe(false)
    expect(result.current.type).toBeNull()
    expect(result.current.data).toBeUndefined()
  })

  it('opens modal with type and data', () => {
    const { result } = renderHook(() => useModal())

    act(() => {
      result.current.open('tableDetail', { rows: [] })
    })

    expect(result.current.isOpen).toBe(true)
    expect(result.current.type).toBe('tableDetail')
    expect(result.current.data).toEqual({ rows: [] })
  })

  it('opens modal without data', () => {
    const { result } = renderHook(() => useModal())

    act(() => {
      result.current.open('newAnalysis')
    })

    expect(result.current.isOpen).toBe(true)
    expect(result.current.type).toBe('newAnalysis')
  })

  it('closes modal', () => {
    const { result } = renderHook(() => useModal())

    act(() => {
      result.current.open('chartDetail', { data: 'test' })
    })

    act(() => {
      result.current.close()
    })

    expect(result.current.isOpen).toBe(false)
    expect(result.current.type).toBeNull()
  })

  it('can open different modal types', () => {
    const { result } = renderHook(() => useModal())

    act(() => {
      result.current.open('logDetail')
    })
    expect(result.current.type).toBe('logDetail')

    act(() => {
      result.current.open('chartDetail')
    })
    expect(result.current.type).toBe('chartDetail')
  })
})
