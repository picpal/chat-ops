import React from 'react'
import { Icon } from '@/components/common'
import { useUIStore, useChatStore } from '@/store'
import { ICONS } from '@/utils'

const Header: React.FC = () => {
  const { sidebarCollapsed, toggleSidebar } = useUIStore()
  const { currentSessionId, sessions } = useChatStore()

  const currentSession = sessions.find((s) => s.id === currentSessionId)
  const hasMessages = currentSession && currentSession.messages.length > 0

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
      <div>
        {hasMessages && (
          <button
            className="p-2 text-stone-400 hover:text-stone-600 hover:bg-stone-100 rounded-lg transition-colors"
            title="More options"
          >
            <Icon name={ICONS.MORE_HORIZ} />
          </button>
        )}
      </div>
    </header>
  )
}

export default Header
