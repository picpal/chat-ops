import React from 'react'
import { Icon } from '@/components/common'
import { useUIStore } from '@/store'
import { APP_CONFIG, ICONS } from '@/utils'

const Header: React.FC = () => {
  const { sidebarCollapsed, toggleSidebar } = useUIStore()

  return (
    <header className="h-16 border-b border-slate-200 bg-white/95 backdrop-blur-sm flex items-center justify-between px-6 shrink-0 z-10 sticky top-0">
      <div className="flex items-center gap-3">
        {sidebarCollapsed && (
          <button
            onClick={toggleSidebar}
            className="p-2 -ml-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
            title="Open sidebar (⌘⇧S)"
          >
            <Icon name={ICONS.MENU} />
          </button>
        )}
        <h2 className="text-slate-800 text-lg font-bold tracking-tight">Agent Dashboard</h2>
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-500 border border-slate-200 uppercase tracking-wider">
          Beta v{APP_CONFIG.VERSION}
        </span>
      </div>

      <div className="flex items-center gap-4">
        {/* Gateway Status */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200">
          <Icon name={ICONS.CHECK_CIRCLE} className="text-emerald-500" size="sm" />
          <span className="text-xs text-slate-600 font-medium">Gateway: Stable</span>
        </div>

        <div className="h-6 w-px bg-slate-200 mx-2" />

        {/* Action Buttons */}
        <button className="p-2 text-slate-400 hover:text-primary hover:bg-slate-50 rounded-lg transition-colors">
          <Icon name={ICONS.NOTIFICATIONS} />
        </button>

        <button className="p-2 text-slate-400 hover:text-primary hover:bg-slate-50 rounded-lg transition-colors">
          <Icon name={ICONS.SETTINGS} />
        </button>

        {/* User Avatar */}
        <div
          className="bg-center bg-no-repeat bg-cover rounded-full h-8 w-8 ring-2 ring-slate-100 cursor-pointer"
          style={{
            backgroundImage:
              'url("https://lh3.googleusercontent.com/aida-public/AB6AXuCJCmyW6HZ3ewQxUpD0aIqUy-TDMAH_wUtMZiyYoTmZKfAziWKUph1KHZLJxG5lmWBYkJpDYPc30wMuSGID-vuh6KjogFUuPAwcWgSx9b7lVNxQebQVuym-ju9w1noBDhgSrSbcray7Q76OJ6RAMRTxcX84VX706vzAR0nqSIEptUpdFO0oAl44lDjO_s_SUt8kRAXeZNXPosyPkOq3D4zQl-IiHug0qMKUtHBrb29naqk00lPsQhXpIve1whlO1nGJVbDg-sZ1EIZz")',
          }}
          title="User Profile"
        />
      </div>
    </header>
  )
}

export default Header
