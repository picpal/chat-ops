import { create } from 'zustand'

export type ModalType =
  | 'newAnalysis'
  | 'tableDetail'
  | 'chartDetail'
  | 'logDetail'
  | null

interface ModalState {
  isOpen: boolean
  type: ModalType
  data?: any
}

interface UIState {
  sidebarCollapsed: boolean
  modal: ModalState

  // Actions
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  openModal: (type: NonNullable<ModalType>, data?: any) => void
  closeModal: () => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  modal: {
    isOpen: false,
    type: null,
  },

  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  setSidebarCollapsed: (collapsed: boolean) =>
    set({ sidebarCollapsed: collapsed }),

  openModal: (type, data) =>
    set({
      modal: { isOpen: true, type, data },
    }),

  closeModal: () =>
    set({
      modal: { isOpen: false, type: null, data: undefined },
    }),
}))
