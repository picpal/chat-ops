import React from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import ChatPanel from './ChatPanel'
import { PageView } from '@/types/navigation'

interface AppLayoutProps {
  children: React.ReactNode
  variant?: 'chat' | 'page'
  navigateTo: (view: PageView) => void
  currentView: PageView
}

const AppLayout: React.FC<AppLayoutProps> = ({ children, variant = 'chat', navigateTo, currentView }) => {
  return (
    <div className="flex h-screen w-full bg-white text-slate-900 font-display overflow-hidden">
      <Sidebar navigateTo={navigateTo} currentView={currentView} />

      {variant === 'chat' ? (
        <main className="flex-1 flex flex-col h-full relative min-w-0 bg-slate-50/50">
          <Header />

          <div data-chat-container className="flex-1 overflow-y-auto pt-4 md:pt-8 px-6 md:px-10 space-y-6 scroll-smooth pb-64">
            {children}
          </div>

          <ChatPanel />
        </main>
      ) : (
        <main className="flex-1 flex flex-col h-full relative min-w-0 overflow-y-auto">
          {children}
        </main>
      )}
    </div>
  )
}

export default AppLayout
