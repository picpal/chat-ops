import React from 'react'
import { Icon } from '@/components/common'
import { useUIStore } from '@/store'
import { APP_CONFIG, ICONS } from '@/utils'

const Header: React.FC = () => {
  const { sidebarCollapsed, toggleSidebar } = useUIStore()

  if (!sidebarCollapsed) {
    return null
  }

  return (
    <header className="h-14 bg-slate-50 flex items-center px-3 shrink-0 z-10 sticky top-0">
      <button
        onClick={toggleSidebar}
        className="p-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
        title="Open sidebar (⌘⇧S)"
      >
        <Icon name={ICONS.MENU} />
      </button>
    </header>
  )
}

export default Header
