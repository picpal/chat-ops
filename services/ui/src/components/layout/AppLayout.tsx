import React from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import ChatPanel from './ChatPanel'

interface AppLayoutProps {
  children: React.ReactNode
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  return (
    <div className="flex h-screen w-full bg-white text-slate-900 font-display overflow-hidden">
      <Sidebar />

      <main className="flex-1 flex flex-col h-full relative min-w-0 bg-slate-50/50">
        <Header />

        <div className="flex-1 overflow-y-auto p-6 md:p-10 space-y-6 scroll-smooth pb-64">
          {children}
        </div>

        <ChatPanel />
      </main>
    </div>
  )
}

export default AppLayout
