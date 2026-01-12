import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
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

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

type PageView = 'chat' | 'admin'

function App() {
  const [currentView, setCurrentView] = useState<PageView>('chat')

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        {/* 네비게이션 바 */}
        <nav className="bg-gray-800 text-white px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="font-bold text-lg">ChatOps</span>
            <div className="flex gap-2">
              <button
                onClick={() => setCurrentView('chat')}
                className={`px-3 py-1 rounded text-sm ${
                  currentView === 'chat'
                    ? 'bg-blue-600'
                    : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                채팅
              </button>
              <button
                onClick={() => setCurrentView('admin')}
                className={`px-3 py-1 rounded text-sm ${
                  currentView === 'admin'
                    ? 'bg-blue-600'
                    : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                문서 관리
              </button>
            </div>
          </div>
        </nav>

        {/* 페이지 컨텐츠 */}
        {currentView === 'chat' ? (
          <AppLayout>
            <ChatInterface />
          </AppLayout>
        ) : (
          <AdminPage />
        )}

        {/* Modals */}
        <NewAnalysisModal />
        <TableDetailModal />
        <ChartDetailModal />
        <LogDetailModal />
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
