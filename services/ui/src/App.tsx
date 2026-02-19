import { useState, useEffect, useCallback } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { AppLayout } from '@/components/layout'
import {
  NewAnalysisModal,
  TableDetailModal,
  ChartDetailModal,
  LogDetailModal,
} from '@/components/modals'
import { ErrorBoundary } from '@/components/common'
import { ChatInterface } from '@/components/chat'
import { AdminPage } from '@/components/admin'
import { ScenariosPage } from '@/components/scenarios'
import { LogSettingsPage } from '@/components/settings'
import { useInitializeChat } from '@/hooks'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

type PageView = 'chat' | 'admin' | 'scenarios' | 'log-settings'

const pathToView = (pathname: string): PageView => {
  if (pathname === '/admin') return 'admin'
  if (pathname === '/scenarios') return 'scenarios'
  if (pathname === '/settings/log-analysis') return 'log-settings'
  return 'chat'
}

// Internal component that uses the initialization hook
function AppContent() {
  const [currentView, setCurrentView] = useState<PageView>(
    () => pathToView(window.location.pathname)
  )
  const { isInitializing } = useInitializeChat()

  // Set initial history state
  useEffect(() => {
    window.history.replaceState({ view: currentView }, '')
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Handle browser back/forward
  useEffect(() => {
    const handlePopState = (e: PopStateEvent) => {
      const view = e.state?.view || pathToView(window.location.pathname)
      setCurrentView(view)
    }
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const navigateTo = useCallback((view: PageView) => {
    if (view !== currentView) {
      const path = view === 'chat' ? '' : view === 'log-settings' ? 'settings/log-analysis' : view
      window.history.pushState({ view }, '', `/${path}`)
      setCurrentView(view)
    }
  }, [currentView])

  return (
    <>
      {/* Navigation bar */}
      <nav className="bg-gray-800 text-white px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="font-bold text-lg">ChatOps</span>
          <div className="flex gap-2">
            <button
              onClick={() => navigateTo('chat')}
              className={`px-3 py-1 rounded text-sm ${
                currentView === 'chat'
                  ? 'bg-blue-600'
                  : 'bg-gray-700 hover:bg-gray-600'
              }`}
            >
              채팅
            </button>
            <button
              onClick={() => navigateTo('admin')}
              className={`px-3 py-1 rounded text-sm ${
                currentView === 'admin'
                  ? 'bg-blue-600'
                  : 'bg-gray-700 hover:bg-gray-600'
              }`}
            >
              문서 관리
            </button>
            <button
              onClick={() => navigateTo('scenarios')}
              className={`px-3 py-1 rounded text-sm ${
                currentView === 'scenarios'
                  ? 'bg-blue-600'
                  : 'bg-gray-700 hover:bg-gray-600'
              }`}
            >
              시나리오 관리
            </button>
            <button
              onClick={() => navigateTo('log-settings')}
              className={`px-3 py-1 rounded text-sm ${
                currentView === 'log-settings'
                  ? 'bg-blue-600'
                  : 'bg-gray-700 hover:bg-gray-600'
              }`}
            >
              로그 설정
            </button>
          </div>
        </div>
        {isInitializing && (
          <span className="text-xs text-gray-400">Loading...</span>
        )}
      </nav>

      {/* Page content */}
      {currentView === 'chat' ? (
        <AppLayout>
          <ChatInterface />
        </AppLayout>
      ) : currentView === 'admin' ? (
        <AdminPage />
      ) : currentView === 'scenarios' ? (
        <ScenariosPage />
      ) : (
        <LogSettingsPage />
      )}

      {/* Modals */}
      <NewAnalysisModal />
      <TableDetailModal />
      <ChartDetailModal />
      <LogDetailModal />
    </>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AppContent />
        <Toaster
          position="bottom-right"
          toastOptions={{
            duration: 3000,
            style: {
              background: '#363636',
              color: '#fff',
            },
            success: {
              iconTheme: {
                primary: '#10b981',
                secondary: '#fff',
              },
            },
            error: {
              iconTheme: {
                primary: '#ef4444',
                secondary: '#fff',
              },
            },
          }}
        />
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
