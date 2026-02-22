import React, { useState, useRef, useEffect } from 'react'
import { Icon } from '@/components/common'
import { useUIStore, useChatStore } from '@/store'
import { ICONS, copyToClipboard, extractRenderSpecText } from '@/utils'
import toast from 'react-hot-toast'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'

const Header: React.FC = () => {
  const { sidebarCollapsed, toggleSidebar } = useUIStore()
  const { currentSessionId, sessions } = useChatStore()

  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const currentSession = sessions.find((s) => s.id === currentSessionId)
  const hasMessages = currentSession && currentSession.messages.length > 0

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Close dropdown on ESC key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isMenuOpen) {
        setIsMenuOpen(false)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isMenuOpen])

  const handleCopyConversation = async () => {
    if (!currentSession) return

    const validMessages = currentSession.messages.filter(
      (msg) => msg.status !== 'sending' && msg.status !== 'error'
    )

    if (validMessages.length === 0) {
      toast.error('복사할 대화 내용이 없습니다')
      setIsMenuOpen(false)
      return
    }

    const text = validMessages
      .map((msg) => {
        const role = msg.role === 'user' ? '사용자' : 'AI'
        if (msg.role === 'user') {
          return `[${role}]: ${msg.content}`
        }
        // AI 메시지: content + renderSpec 텍스트
        const renderSpecText = msg.renderSpec
          ? extractRenderSpecText(msg.renderSpec, msg.queryResult)
          : ''
        const contentParts = [msg.content, renderSpecText].filter(Boolean)
        return `[${role}]: ${contentParts.join('\n\n')}`
      })
      .join('\n\n')

    const success = await copyToClipboard(text)
    if (success) {
      toast.success('대화 내용이 복사되었습니다')
    } else {
      toast.error('복사에 실패했습니다')
    }
    setIsMenuOpen(false)
  }

  const handleExportPDF = async () => {
    const chatContainer = document.querySelector('[data-chat-container]') as HTMLElement | null
    if (!chatContainer) {
      toast.error('내보낼 대화 영역을 찾을 수 없습니다')
      setIsMenuOpen(false)
      return
    }

    setIsExporting(true)
    const originalStyle = chatContainer.style.cssText
    try {
      chatContainer.classList.add('pdf-exporting')
      // 스크롤 컨테이너를 전체 높이로 확장하여 모든 내용 캡처
      chatContainer.style.overflow = 'visible'
      chatContainer.style.height = 'auto'
      chatContainer.style.maxHeight = 'none'
      await new Promise(resolve => requestAnimationFrame(resolve))
      const canvas = await html2canvas(chatContainer, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff',
        windowHeight: chatContainer.scrollHeight,
      })

      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF('p', 'mm', 'a4')

      const pdfWidth = pdf.internal.pageSize.getWidth()
      const pdfHeight = pdf.internal.pageSize.getHeight()
      const imgWidth = canvas.width
      const imgHeight = canvas.height

      const ratio = (pdfWidth - 20) / imgWidth
      const scaledWidth = imgWidth * ratio
      const scaledHeight = imgHeight * ratio

      let heightLeft = scaledHeight
      let position = 10

      pdf.addImage(imgData, 'PNG', 10, position, scaledWidth, scaledHeight)
      heightLeft -= (pdfHeight - 20)

      while (heightLeft > 0) {
        position = position - pdfHeight + 10
        pdf.addPage()
        pdf.addImage(imgData, 'PNG', 10, position, scaledWidth, scaledHeight)
        heightLeft -= (pdfHeight - 20)
      }

      const fileName = currentSession?.title
        ? `${currentSession.title.replace(/[^a-zA-Z0-9가-힣]/g, '_')}.pdf`
        : 'conversation.pdf'
      pdf.save(fileName)

      toast.success('PDF가 다운로드되었습니다')
    } catch (error) {
      console.error('PDF export error:', error)
      toast.error('PDF 내보내기에 실패했습니다')
    } finally {
      chatContainer.classList.remove('pdf-exporting')
      chatContainer.style.cssText = originalStyle
      setIsExporting(false)
      setIsMenuOpen(false)
    }
  }

  // Hide header when sidebar is open AND no messages
  if (!sidebarCollapsed && !hasMessages) {
    return null
  }

  return (
    <header className="h-14 bg-slate-50/50 flex items-center justify-between px-4 shrink-0 z-10 sticky top-0">
      {/* Left side - Sidebar toggle */}
      <div>
        {sidebarCollapsed && (
          <button
            onClick={toggleSidebar}
            className="p-2 text-stone-400 hover:text-stone-600 hover:bg-stone-100 rounded-lg transition-colors"
            title="Open sidebar (⌘⇧S)"
          >
            <Icon name={ICONS.MENU} />
          </button>
        )}
      </div>

      {/* Right side - More options */}
      <div className="relative" ref={menuRef}>
        {hasMessages && (
          <button
            onClick={() => setIsMenuOpen((prev) => !prev)}
            className="p-2 text-stone-400 hover:text-stone-600 hover:bg-stone-100 rounded-lg transition-colors"
            title="More options"
          >
            <Icon name={ICONS.MORE_HORIZ} />
          </button>
        )}

        {isMenuOpen && (
          <div
            role="menu"
            className="absolute right-0 top-full mt-2 bg-white rounded-xl shadow-xl border border-slate-100 py-2 z-50 min-w-[200px]"
          >
            <button
              onClick={handleCopyConversation}
              className="w-full px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50 flex items-center gap-2"
            >
              <Icon name={ICONS.CONTENT_COPY} />
              대화 내용 복사
            </button>
            <button
              onClick={handleExportPDF}
              disabled={isExporting}
              className="w-full px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50 flex items-center gap-2 disabled:opacity-50"
            >
              <Icon name={ICONS.PICTURE_AS_PDF} />
              {isExporting ? '내보내는 중...' : '대화 내보내기 (PDF)'}
            </button>
          </div>
        )}
      </div>
    </header>
  )
}

export default Header
