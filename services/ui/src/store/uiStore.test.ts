import { describe, it, expect, beforeEach } from 'vitest'
import { useUIStore } from './uiStore'

describe('uiStore', () => {
  beforeEach(() => {
    useUIStore.setState({
      sidebarCollapsed: false,
      modal: { isOpen: false, type: null },
    })
  })

  describe('sidebar', () => {
    it('toggles sidebar state', () => {
      const { toggleSidebar } = useUIStore.getState()

      expect(useUIStore.getState().sidebarCollapsed).toBe(false)

      toggleSidebar()
      expect(useUIStore.getState().sidebarCollapsed).toBe(true)

      toggleSidebar()
      expect(useUIStore.getState().sidebarCollapsed).toBe(false)
    })

    it('sets sidebar collapsed state directly', () => {
      const { setSidebarCollapsed } = useUIStore.getState()

      setSidebarCollapsed(true)
      expect(useUIStore.getState().sidebarCollapsed).toBe(true)

      setSidebarCollapsed(false)
      expect(useUIStore.getState().sidebarCollapsed).toBe(false)
    })
  })

  describe('modal', () => {
    it('opens modal with type and data', () => {
      const { openModal } = useUIStore.getState()

      openModal('tableDetail', { id: 'test' })

      const { modal } = useUIStore.getState()
      expect(modal.isOpen).toBe(true)
      expect(modal.type).toBe('tableDetail')
      expect(modal.data).toEqual({ id: 'test' })
    })

    it('opens modal without data', () => {
      const { openModal } = useUIStore.getState()

      openModal('newAnalysis')

      const { modal } = useUIStore.getState()
      expect(modal.isOpen).toBe(true)
      expect(modal.type).toBe('newAnalysis')
      expect(modal.data).toBeUndefined()
    })

    it('closes modal and clears data', () => {
      const { openModal, closeModal } = useUIStore.getState()

      openModal('chartDetail', { chart: 'data' })
      closeModal()

      const { modal } = useUIStore.getState()
      expect(modal.isOpen).toBe(false)
      expect(modal.type).toBeNull()
      expect(modal.data).toBeUndefined()
    })

    it('opens different modal types', () => {
      const { openModal } = useUIStore.getState()

      openModal('newAnalysis')
      expect(useUIStore.getState().modal.type).toBe('newAnalysis')

      openModal('logDetail')
      expect(useUIStore.getState().modal.type).toBe('logDetail')

      openModal('chartDetail')
      expect(useUIStore.getState().modal.type).toBe('chartDetail')

      openModal('tableDetail')
      expect(useUIStore.getState().modal.type).toBe('tableDetail')
    })

    it('replaces previous modal when opening new one', () => {
      const { openModal } = useUIStore.getState()

      openModal('tableDetail', { data: 'first' })
      openModal('chartDetail', { data: 'second' })

      const { modal } = useUIStore.getState()
      expect(modal.type).toBe('chartDetail')
      expect(modal.data).toEqual({ data: 'second' })
    })
  })
})
