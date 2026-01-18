import { useCallback } from 'react'
import { useUIStore, ModalType } from '@/store'

export const useModal = () => {
  // Zustand selector pattern - select individual primitives for stable references
  const isOpen = useUIStore((state) => state.modal.isOpen)
  const type = useUIStore((state) => state.modal.type)
  const data = useUIStore((state) => state.modal.data)
  const openModal = useUIStore((state) => state.openModal)
  const closeModal = useUIStore((state) => state.closeModal)

  const open = useCallback((type: NonNullable<ModalType>, data?: any) => {
    openModal(type, data)
  }, [openModal])

  const close = useCallback(() => {
    closeModal()
  }, [closeModal])

  return {
    isOpen,
    type,
    data,
    open,
    close,
  }
}
