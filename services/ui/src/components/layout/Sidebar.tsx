import React from 'react'
import { useChatStore, useUIStore } from '@/store'
import { Icon, Button } from '@/components/common'
import { SESSION_CATEGORIES, ICONS } from '@/utils'
import { SessionCategory } from '@/types/chat'

const Sidebar: React.FC = () => {
  const { sessions, currentSessionId, setCurrentSession, clearSessions } =
    useChatStore()
  const { openModal } = useUIStore()

  const handleNewAnalysis = () => {
    openModal('newAnalysis')
  }

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
    <aside className="w-80 h-full flex flex-col border-r border-slate-200 bg-slate-50 shrink-0 transition-all duration-300">
      {/* Header */}
      <div className="p-6 pb-2">
        <div className="flex gap-4 items-center mb-6">
          <div
            className="bg-center bg-no-repeat bg-cover rounded-xl h-12 w-12 shadow-lg ring-2 ring-primary/20"
            style={{
              backgroundImage:
                'url("https://lh3.googleusercontent.com/aida-public/AB6AXuDzHpBgerWZV5aLKq2-8J3gD01-1jBeEakwX8nGeZK4IzvGTxILKUtVTI6XL0UnSKDLojSasscyZnAPRVu97HSU0KU3ZYwc59kyWnMZUM8yjRTC-XCTPwBy5k1oRTuYlrElLum6yGzI8XrRsDuFhgPo9Kq805jVYH70ch4IH3UJ3VmWiBEXnb5ilc6BTbbnjxZmeK57sO2nXRVNRM93m6IORW8VNLHSwMoum8ItHWr7hQxR9K7FaaF58BKxRjORwa59_siotgMqXBRH")',
            }}
          />
          <div className="flex flex-col">
            <h1 className="text-slate-900 text-lg font-bold leading-tight tracking-tight">
              FinBot Agent
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <p className="text-slate-500 text-xs font-medium">Systems Online</p>
            </div>
          </div>
        </div>

        <Button
          onClick={handleNewAnalysis}
          variant="primary"
          className="w-full group"
          icon={ICONS.ADD_CIRCLE}
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
    </aside>
  )
}

export default Sidebar
