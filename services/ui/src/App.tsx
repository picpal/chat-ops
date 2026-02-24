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
import type { PageView } from '@/types/navigation'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

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
  useInitializeChat()

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
      {/* Page content */}
      {currentView === 'chat' ? (
        <AppLayout variant="chat" navigateTo={navigateTo} currentView={currentView}>
          <ChatInterface />
        </AppLayout>
      ) : currentView === 'admin' ? (
        <AppLayout variant="page" navigateTo={navigateTo} currentView={currentView}>
          <AdminPage />
        </AppLayout>
      ) : currentView === 'scenarios' ? (
        <AppLayout variant="page" navigateTo={navigateTo} currentView={currentView}>
          <ScenariosPage />
        </AppLayout>
      ) : (
        <AppLayout variant="page" navigateTo={navigateTo} currentView={currentView}>
          <LogSettingsPage />
        </AppLayout>
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
