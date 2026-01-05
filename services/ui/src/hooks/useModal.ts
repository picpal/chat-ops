import { useUIStore, ModalType } from '@/store'

export const useModal = () => {
  const { modal, openModal, closeModal } = useUIStore()

  const open = (type: NonNullable<ModalType>, data?: any) => {
    openModal(type, data)
  }

  const close = () => {
    closeModal()
  }

  return {
    isOpen: modal.isOpen,
    type: modal.type,
    data: modal.data,
    open,
    close,
  }
}
