import React, { useState, useRef, useEffect } from 'react'
import { useChatStore, useUIStore } from '@/store'
import { Icon } from '@/components/common'
import { SESSION_CATEGORIES, ICONS } from '@/utils'
import { SessionCategory } from '@/types/chat'

const Sidebar: React.FC = () => {
  const { sessions, currentSessionId, setCurrentSession } =
    useChatStore()
  const { openModal, sidebarCollapsed, toggleSidebar } = useUIStore()
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setIsUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleNewChat = () => {
    openModal('newAnalysis')
  }

  // Keyboard shortcut: Cmd/Ctrl + Shift + S
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 's') {
        e.preventDefault()
        toggleSidebar()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [toggleSidebar])

  const groupedSessions = React.useMemo(() => {
    const groups: Record<SessionCategory, typeof sessions> = {
      today: [],
      yesterday: [],
      previous7days: [],
      older: [],
    }

    sessions.forEach((session) => {
      groups[session.category].push(session)
    })

    return groups
  }, [sessions])

  return (
    <aside className={`h-full shrink-0 overflow-hidden transition-[width] duration-300 ease-in-out ${sidebarCollapsed ? 'w-0' : 'w-72'}`}>
      <div className={`w-72 h-full flex flex-col bg-stone-100 transition-opacity duration-150 ${sidebarCollapsed ? 'opacity-0' : 'opacity-100 delay-100'}`}>
        {/* Header */}
        <div className="h-14 px-4 flex items-center justify-between shrink-0">
          <h1 className="text-stone-800 text-xl font-semibold tracking-tight">ChatOps</h1>
          <button
            onClick={toggleSidebar}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-stone-400 hover:text-stone-600 hover:bg-stone-200/50 transition-colors"
            title="Close sidebar (⌘⇧S)"
          >
            <Icon name={ICONS.MENU_OPEN} className="text-[20px]" />
          </button>
        </div>

        {/* New Chat Button */}
        <div className="px-4 py-2">
          <button
            onClick={handleNewChat}
            className="flex items-center gap-3 group"
          >
            <span className="w-9 h-9 rounded-full bg-blue-500 flex items-center justify-center text-white shadow-sm group-hover:bg-blue-600 transition-colors">
              <Icon name={ICONS.ADD_CIRCLE} className="text-[20px]" />
            </span>
            <span className="text-stone-700 text-[15px] font-medium group-hover:text-stone-900 transition-colors">
              새 채팅
            </span>
          </button>
        </div>

        {/* Session History */}
        <div className="flex-1 overflow-y-auto px-2 py-4">
          {(['today', 'yesterday', 'previous7days', 'older'] as SessionCategory[]).map(
            (category) => {
              const categorySessions = groupedSessions[category]
              if (categorySessions.length === 0) return null

              return (
                <div key={category} className="mb-4">
                  <h3 className="px-3 py-2 text-xs font-medium text-stone-400 uppercase tracking-wide">
                    {category === 'today'
                      ? SESSION_CATEGORIES.TODAY
                      : category === 'yesterday'
                      ? SESSION_CATEGORIES.YESTERDAY
                      : category === 'previous7days'
                      ? SESSION_CATEGORIES.PREVIOUS_7_DAYS
                      : SESSION_CATEGORIES.OLDER}
                  </h3>
                  <div className="space-y-0.5">
                    {categorySessions.map((session) => {
                      const isActive = session.id === currentSessionId
                      return (
                        <button
                          key={session.id}
                          onClick={() => setCurrentSession(session.id)}
                          className={`w-full px-3 py-2 rounded-lg text-left transition-all ${
                            isActive
                              ? 'bg-stone-200/70'
                              : 'hover:bg-stone-200/50'
                          }`}
                        >
                          <p className={`text-sm truncate ${
                            isActive ? 'text-stone-900 font-medium' : 'text-stone-600'
                          }`}>
                            {session.title}
                          </p>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            }
          )}
        </div>

        {/* Footer - User Profile */}
        <div className="px-2 py-2 shrink-0 relative" ref={userMenuRef}>
          {/* Popup Menu */}
          {isUserMenuOpen && (
            <div className="absolute bottom-full left-2 right-2 mb-1 bg-white rounded-lg shadow-lg border border-stone-200 py-1 z-50">
              <button className="w-full px-3 py-2 text-left text-sm text-stone-700 hover:bg-stone-100 flex items-center gap-2">
                <Icon name={ICONS.SETTINGS} className="text-[18px] text-stone-500" />
                설정
              </button>
              <button className="w-full px-3 py-2 text-left text-sm text-stone-700 hover:bg-stone-100 flex items-center gap-2">
                <Icon name={ICONS.LOGOUT} className="text-[18px] text-stone-500" />
                로그아웃
              </button>
            </div>
          )}

          {/* User Profile Button */}
          <button
            onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
            className="w-full px-2 py-2 rounded-lg flex items-center gap-3 hover:bg-stone-200/50 transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-stone-300 flex items-center justify-center text-stone-600 text-sm font-medium">
              U
            </div>
            <span className="text-sm text-stone-700 truncate flex-1 text-left">user@example.com</span>
          </button>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
