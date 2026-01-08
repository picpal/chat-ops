import React from 'react'
import { useChatStore, useUIStore } from '@/store'
import { Icon, Button } from '@/components/common'
import { SESSION_CATEGORIES, ICONS } from '@/utils'
import { SessionCategory } from '@/types/chat'

const Sidebar: React.FC = () => {
  const { sessions, currentSessionId, setCurrentSession, clearSessions } =
    useChatStore()
  const { openModal, sidebarCollapsed, toggleSidebar } = useUIStore()

  const handleNewAnalysis = () => {
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
    <aside className={`h-full shrink-0 overflow-hidden transition-[width] duration-300 ease-in-out ${sidebarCollapsed ? 'w-0' : 'w-80'}`}>
      <div className={`w-80 h-full flex flex-col border-r border-slate-200 bg-slate-50 transition-opacity duration-150 ${sidebarCollapsed ? 'opacity-0' : 'opacity-100 delay-100'}`}>
        {/* Header */}
        <div className="h-14 px-3 flex items-center justify-between bg-slate-50 shrink-0">
          <span className="text-slate-900 font-semibold text-sm">ChatOps</span>
          <button
            onClick={toggleSidebar}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-900 hover:bg-slate-100 transition-colors"
            title="Close sidebar (⌘⇧S)"
          >
            <Icon name={ICONS.MENU_OPEN} className="text-[20px]" />
          </button>
        </div>

        {/* New Analysis Button */}
        <div className="p-3">
          <Button
            onClick={handleNewAnalysis}
            variant="primary"
            className="w-full group"
            icon={ICONS.EDIT_SQUARE}
          >
            New Analysis
          </Button>
        </div>

        {/* Session History */}
        <div className="flex-1 overflow-y-auto px-4 py-2 space-y-6">
          {(['today', 'yesterday', 'previous7days', 'older'] as SessionCategory[]).map(
            (category) => {
              const categorySessions = groupedSessions[category]
              if (categorySessions.length === 0) return null

              return (
                <div key={category}>
                  <h3 className="px-2 text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                    {category === 'today'
                      ? SESSION_CATEGORIES.TODAY
                      : category === 'yesterday'
                      ? SESSION_CATEGORIES.YESTERDAY
                      : category === 'previous7days'
                      ? SESSION_CATEGORIES.PREVIOUS_7_DAYS
                      : SESSION_CATEGORIES.OLDER}
                  </h3>
                  <div className="space-y-1">
                    {categorySessions.map((session) => {
                      const isActive = session.id === currentSessionId
                      return (
                        <button
                          key={session.id}
                          onClick={() => setCurrentSession(session.id)}
                          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all group ${
                            isActive
                              ? 'bg-white border border-slate-200 shadow-sm'
                              : 'hover:bg-white hover:shadow-sm hover:border-slate-200 border border-transparent'
                          }`}
                        >
                          <Icon
                            name={session.icon || ICONS.CHAT}
                            className={`text-[20px] ${
                              isActive
                                ? 'text-primary'
                                : 'text-slate-400 group-hover:text-primary'
                            }`}
                          />
                          <div className="overflow-hidden flex-1">
                            <p
                              className={`text-sm font-medium truncate ${
                                isActive
                                  ? 'text-slate-800'
                                  : 'text-slate-600 group-hover:text-slate-900'
                              }`}
                            >
                              {session.title}
                            </p>
                            {session.subtitle && (
                              <p className="text-slate-500 text-xs truncate">
                                {session.subtitle}
                              </p>
                            )}
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            }
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-100/50 flex items-center justify-between gap-2">
          <button className="flex flex-1 items-center gap-3 px-2 py-2 text-slate-500 hover:text-slate-900 transition-colors">
            <Icon name={ICONS.LOGOUT} />
            <span className="text-sm font-medium">Logout</span>
          </button>
          <button
            onClick={clearSessions}
            className="flex items-center justify-center p-2 text-slate-400 hover:text-slate-700 hover:bg-white rounded-lg transition-all border border-transparent hover:border-slate-200 hover:shadow-sm"
            title="Clear Query History"
          >
            <Icon name={ICONS.CLEANING_SERVICES} size="sm" />
          </button>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
