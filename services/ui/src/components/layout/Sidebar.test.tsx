import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import Sidebar from './Sidebar'
import { useChatStore, useUIStore } from '@/store'

// Mock Icon component
vi.mock('@/components/common', () => ({
  Icon: ({ name }: { name: string }) => <span data-testid={`icon-${name}`}>{name}</span>,
}))

// Mock SESSION_CATEGORIES and ICONS
vi.mock('@/utils', () => ({
  SESSION_CATEGORIES: {
    TODAY: '오늘',
    YESTERDAY: '어제',
    PREVIOUS_7_DAYS: '지난 7일',
    OLDER: '이전',
  },
  ICONS: {
    DESCRIPTION: 'description',
    ANALYTICS: 'analytics',
    TERMINAL: 'terminal',
    HOME: 'home',
    MENU_OPEN: 'menu_open',
    ADD_CIRCLE: 'add_circle',
    SEARCH: 'search',
    CLOSE: 'close',
    SETTINGS: 'settings',
    LOGOUT: 'logout',
    SIDEBAR_OPEN: 'sidebar_open',
  },
}))

const setupStore = () => {
  const sessionId = 'session-test-001'
  useChatStore.setState({
    currentSessionId: sessionId,
    sessions: [
      {
        id: sessionId,
        title: 'Test Session',
        timestamp: new Date().toISOString(),
        category: 'today',
        messages: [],
      },
      {
        id: 'session-test-002',
        title: 'Another Session',
        timestamp: new Date().toISOString(),
        category: 'today',
        messages: [],
      },
    ],
    isLoading: false,
    error: null,
    currentUserId: null,
    isSyncing: false,
  })
  useUIStore.setState({
    sidebarCollapsed: false,
    modal: { isOpen: false, type: null },
  })
  return sessionId
}

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('handleSessionClick - 설정 페이지에서 세션 클릭 시 채팅 뷰로 전환', () => {
    it('should call navigateTo("chat") when currentView is "admin" and session is clicked', async () => {
      // Arrange
      setupStore()
      const navigateTo = vi.fn()

      render(<Sidebar navigateTo={navigateTo} currentView="admin" />)

      // Act
      const sessionButton = screen.getByText('Test Session')
      fireEvent.click(sessionButton)

      // Assert
      await waitFor(() => {
        expect(navigateTo).toHaveBeenCalledWith('chat')
      })
    })

    it('should call navigateTo("chat") when currentView is "scenarios" and session is clicked', async () => {
      // Arrange
      setupStore()
      const navigateTo = vi.fn()

      render(<Sidebar navigateTo={navigateTo} currentView="scenarios" />)

      // Act
      const sessionButton = screen.getByText('Test Session')
      fireEvent.click(sessionButton)

      // Assert
      await waitFor(() => {
        expect(navigateTo).toHaveBeenCalledWith('chat')
      })
    })

    it('should call navigateTo("chat") when currentView is "log-settings" and session is clicked', async () => {
      // Arrange
      setupStore()
      const navigateTo = vi.fn()

      render(<Sidebar navigateTo={navigateTo} currentView="log-settings" />)

      // Act
      const sessionButton = screen.getByText('Test Session')
      fireEvent.click(sessionButton)

      // Assert
      await waitFor(() => {
        expect(navigateTo).toHaveBeenCalledWith('chat')
      })
    })

    it('should NOT call navigateTo when currentView is "chat" and session is clicked', async () => {
      // Arrange
      setupStore()
      const navigateTo = vi.fn()

      render(<Sidebar navigateTo={navigateTo} currentView="chat" />)

      // Act
      const sessionButton = screen.getByText('Test Session')
      fireEvent.click(sessionButton)

      // Assert
      await waitFor(() => {
        expect(navigateTo).not.toHaveBeenCalledWith('chat')
      })
    })
  })
})
