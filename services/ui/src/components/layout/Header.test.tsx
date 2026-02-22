import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import Header from './Header'
import { useChatStore, useUIStore } from '@/store'

// Mock Icon component to avoid cn/utils dependency issues in tests
vi.mock('@/components/common', () => ({
  Icon: ({ name }: { name: string }) => <span data-testid={`icon-${name}`}>{name}</span>,
}))

// Mock html2canvas
const { mockCanvas, mockPdf } = vi.hoisted(() => {
  const mockCanvas = {
    toDataURL: () => 'data:image/png;base64,mockdata',
    width: 800,
    height: 600,
  }
  const mockPdf = {
    internal: {
      pageSize: {
        getWidth: () => 210,
        getHeight: () => 297,
      },
    },
    addImage: vi.fn(),
    addPage: vi.fn(),
    save: vi.fn(),
  }
  return { mockCanvas, mockPdf }
})

vi.mock('html2canvas', () => ({
  default: vi.fn().mockResolvedValue(mockCanvas),
}))

// Mock jspdf
vi.mock('jspdf', () => {
  return {
    default: vi.fn().mockImplementation(function () {
      return mockPdf
    }),
  }
})

// Mock @/utils/helpers
vi.mock('@/utils/helpers', () => ({
  copyToClipboard: vi.fn().mockResolvedValue(true),
}))

// Helpers for store state setup
const setupStoreWithMessages = () => {
  const sessionId = 'session-test-001'
  useChatStore.setState({
    currentSessionId: sessionId,
    sessions: [
      {
        id: sessionId,
        title: 'Test Session',
        timestamp: new Date().toISOString(),
        category: 'today',
        messages: [
          {
            id: 'msg-001',
            role: 'user',
            content: '테스트 질문입니다.',
            timestamp: new Date().toISOString(),
            status: 'success',
          },
          {
            id: 'msg-002',
            role: 'assistant',
            content: '테스트 답변입니다.',
            timestamp: new Date().toISOString(),
            status: 'success',
          },
        ],
      },
    ],
    isLoading: false,
    error: null,
    currentUserId: null,
    isSyncing: false,
  })
  useUIStore.setState({
    sidebarCollapsed: true,
    modal: { isOpen: false, type: null },
  })
  return sessionId
}

const setupStoreWithNoMessages = () => {
  const sessionId = 'session-empty-001'
  useChatStore.setState({
    currentSessionId: sessionId,
    sessions: [
      {
        id: sessionId,
        title: 'Empty Session',
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
    sidebarCollapsed: true,
    modal: { isOpen: false, type: null },
  })
}

const setupStoreWithLoadingAndErrorMessages = () => {
  const sessionId = 'session-mixed-001'
  useChatStore.setState({
    currentSessionId: sessionId,
    sessions: [
      {
        id: sessionId,
        title: 'Mixed Session',
        timestamp: new Date().toISOString(),
        category: 'today',
        messages: [
          {
            id: 'msg-001',
            role: 'user',
            content: '질문입니다.',
            timestamp: new Date().toISOString(),
            status: 'success',
          },
          {
            id: 'msg-002',
            role: 'assistant',
            content: '로딩 중...',
            timestamp: new Date().toISOString(),
            status: 'sending',
          },
          {
            id: 'msg-003',
            role: 'assistant',
            content: '오류가 발생했습니다.',
            timestamp: new Date().toISOString(),
            status: 'error',
          },
        ],
      },
    ],
    isLoading: false,
    error: null,
    currentUserId: null,
    isSyncing: false,
  })
  useUIStore.setState({
    sidebarCollapsed: true,
    modal: { isOpen: false, type: null },
  })
}

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => { cb(0); return 0 })
  })

  describe('더보기 버튼 표시 조건', () => {
    it('should show "..." button when session has messages', () => {
      // Arrange
      setupStoreWithMessages()

      // Act
      render(<Header />)

      // Assert - "..." 버튼(More options)이 표시되어야 함
      const moreButton = screen.getByTitle('More options')
      expect(moreButton).toBeInTheDocument()
    })

    it('should not show "..." button when session has no messages', () => {
      // Arrange
      setupStoreWithNoMessages()

      // Act
      render(<Header />)

      // Assert - "..." 버튼이 없어야 함
      const moreButton = screen.queryByTitle('More options')
      expect(moreButton).not.toBeInTheDocument()
    })
  })

  describe('드롭다운 메뉴', () => {
    it('should show dropdown menu when "..." button is clicked', () => {
      // Arrange
      setupStoreWithMessages()
      render(<Header />)
      const moreButton = screen.getByTitle('More options')

      // Act
      fireEvent.click(moreButton)

      // Assert - 드롭다운 메뉴가 표시되어야 함
      expect(screen.getByRole('menu')).toBeInTheDocument()
    })

    it('should render "대화 내용 복사" menu item in dropdown', () => {
      // Arrange
      setupStoreWithMessages()
      render(<Header />)
      const moreButton = screen.getByTitle('More options')

      // Act
      fireEvent.click(moreButton)

      // Assert
      expect(screen.getByText('대화 내용 복사')).toBeInTheDocument()
    })

    it('should render "대화 내보내기 (PDF)" menu item in dropdown', () => {
      // Arrange
      setupStoreWithMessages()
      render(<Header />)
      const moreButton = screen.getByTitle('More options')

      // Act
      fireEvent.click(moreButton)

      // Assert
      expect(screen.getByText('대화 내보내기 (PDF)')).toBeInTheDocument()
    })

    it('should close dropdown when clicking outside', async () => {
      // Arrange
      setupStoreWithMessages()
      render(<Header />)
      const moreButton = screen.getByTitle('More options')

      // Act - 드롭다운 열기
      fireEvent.click(moreButton)
      expect(screen.getByRole('menu')).toBeInTheDocument()

      // Act - 외부 클릭
      fireEvent.mouseDown(document.body)

      // Assert - 드롭다운이 닫혀야 함
      await waitFor(() => {
        expect(screen.queryByRole('menu')).not.toBeInTheDocument()
      })
    })

    it('should close dropdown when ESC key is pressed', async () => {
      // Arrange
      setupStoreWithMessages()
      render(<Header />)
      const moreButton = screen.getByTitle('More options')

      // Act - 드롭다운 열기
      fireEvent.click(moreButton)
      expect(screen.getByRole('menu')).toBeInTheDocument()

      // Act - ESC 키 누르기
      fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' })

      // Assert - 드롭다운이 닫혀야 함
      await waitFor(() => {
        expect(screen.queryByRole('menu')).not.toBeInTheDocument()
      })
    })
  })

  describe('대화 내용 복사 기능', () => {
    it('should call clipboard mock when copy button is clicked', async () => {
      // Arrange
      const { copyToClipboard } = await import('@/utils/helpers')
      setupStoreWithMessages()
      render(<Header />)
      const moreButton = screen.getByTitle('More options')
      fireEvent.click(moreButton)

      // Act
      const copyButton = screen.getByText('대화 내용 복사')
      fireEvent.click(copyButton)

      // Assert
      await waitFor(() => {
        expect(copyToClipboard).toHaveBeenCalled()
      })
    })

    it('should exclude loading/error messages when copying', async () => {
      // Arrange
      const { copyToClipboard } = await import('@/utils/helpers')
      setupStoreWithLoadingAndErrorMessages()
      render(<Header />)
      const moreButton = screen.getByTitle('More options')
      fireEvent.click(moreButton)

      // Act
      const copyButton = screen.getByText('대화 내용 복사')
      fireEvent.click(copyButton)

      // Assert - copyToClipboard가 호출되어야 하며, loading/error 메시지는 제외
      await waitFor(() => {
        expect(copyToClipboard).toHaveBeenCalled()
        const calledText = (copyToClipboard as ReturnType<typeof vi.fn>).mock.calls[0][0] as string
        // 로딩 중 메시지는 포함되지 않아야 함
        expect(calledText).not.toContain('로딩 중...')
        // 오류 메시지는 포함되지 않아야 함
        expect(calledText).not.toContain('오류가 발생했습니다.')
        // 정상 메시지는 포함되어야 함
        expect(calledText).toContain('질문입니다.')
      })
    })

    it('should include renderSpec text content when copying AI messages', async () => {
      // Arrange
      const { copyToClipboard } = await import('@/utils/helpers')
      const sessionId = 'session-renderspec-001'
      useChatStore.setState({
        currentSessionId: sessionId,
        sessions: [
          {
            id: sessionId,
            title: 'RenderSpec Session',
            timestamp: new Date().toISOString(),
            category: 'today',
            messages: [
              {
                id: 'msg-001',
                role: 'user',
                content: '분석해줘',
                timestamp: new Date().toISOString(),
                status: 'success',
              },
              {
                id: 'msg-002',
                role: 'assistant',
                content: '',
                timestamp: new Date().toISOString(),
                status: 'success',
                renderSpec: {
                  type: 'text',
                  requestId: 'test-req-001',
                  text: { content: '분석 결과입니다.' },
                },
              },
            ],
          },
        ],
        isLoading: false,
        error: null,
        currentUserId: null,
        isSyncing: false,
      })
      useUIStore.setState({
        sidebarCollapsed: true,
        modal: { isOpen: false, type: null },
      })
      render(<Header />)
      const moreButton = screen.getByTitle('More options')
      fireEvent.click(moreButton)

      // Act
      const copyButton = screen.getByText('대화 내용 복사')
      fireEvent.click(copyButton)

      // Assert - renderSpec의 텍스트 내용이 복사된 텍스트에 포함되어야 함
      await waitFor(() => {
        expect(copyToClipboard).toHaveBeenCalled()
        const calledText = (copyToClipboard as ReturnType<typeof vi.fn>).mock.calls[0][0] as string
        expect(calledText).toContain('분석 결과입니다.')
      })
    })
  })

  describe('PDF 내보내기 기능', () => {
    it('should call html2canvas when PDF export button is clicked', async () => {
      // Arrange
      const html2canvas = (await import('html2canvas')).default
      setupStoreWithMessages()

      // data-chat-container 엘리먼트 추가
      const chatContainer = document.createElement('div')
      chatContainer.setAttribute('data-chat-container', '')
      document.body.appendChild(chatContainer)

      render(<Header />)
      const moreButton = screen.getByTitle('More options')
      fireEvent.click(moreButton)

      // Act
      const pdfButton = screen.getByText('대화 내보내기 (PDF)')
      fireEvent.click(pdfButton)

      // Assert
      await waitFor(() => {
        expect(html2canvas).toHaveBeenCalled()
      })

      // Cleanup
      document.body.removeChild(chatContainer)
    })

    it('should add pdf-exporting class before capture and remove after', async () => {
      // Arrange
      const html2canvas = (await import('html2canvas')).default
      setupStoreWithMessages()

      const chatContainer = document.createElement('div')
      chatContainer.setAttribute('data-chat-container', '')
      document.body.appendChild(chatContainer)

      let hadClassDuringCapture = false
      ;(html2canvas as ReturnType<typeof vi.fn>).mockImplementation(async (element: HTMLElement) => {
        hadClassDuringCapture = element.classList.contains('pdf-exporting')
        return mockCanvas
      })

      render(<Header />)
      const moreButton = screen.getByTitle('More options')
      fireEvent.click(moreButton)

      // Act
      const pdfButton = screen.getByText('대화 내보내기 (PDF)')
      fireEvent.click(pdfButton)

      // Assert
      await waitFor(() => {
        expect(hadClassDuringCapture).toBe(true)
        expect(chatContainer.classList.contains('pdf-exporting')).toBe(false)
      })

      // Cleanup
      document.body.removeChild(chatContainer)
    })

    it('should remove pdf-exporting class even when html2canvas fails', async () => {
      // Arrange
      const html2canvas = (await import('html2canvas')).default
      setupStoreWithMessages()

      const chatContainer = document.createElement('div')
      chatContainer.setAttribute('data-chat-container', '')
      document.body.appendChild(chatContainer)

      ;(html2canvas as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Canvas error'))

      render(<Header />)
      const moreButton = screen.getByTitle('More options')
      fireEvent.click(moreButton)

      // Act
      const pdfButton = screen.getByText('대화 내보내기 (PDF)')
      fireEvent.click(pdfButton)

      // Assert - 에러 발생 후에도 pdf-exporting 클래스가 제거되어야 함
      await waitFor(() => {
        expect(chatContainer.classList.contains('pdf-exporting')).toBe(false)
      })

      // Cleanup
      document.body.removeChild(chatContainer)
    })
  })
})
