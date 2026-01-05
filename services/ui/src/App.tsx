import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppLayout } from '@/components/layout'
import {
  NewAnalysisModal,
  TableDetailModal,
  ChartDetailModal,
  LogDetailModal,
} from '@/components/modals'
import { ErrorBoundary } from '@/components/common'
// import { ChatInterface } from '@/components/chat'
import { MockDataDemo } from '@/components/demo' // 테스트용

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AppLayout>
          {/* <ChatInterface /> */}
          <MockDataDemo /> {/* 테스트용 - 완료 후 ChatInterface로 교체 */}
        </AppLayout>

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
