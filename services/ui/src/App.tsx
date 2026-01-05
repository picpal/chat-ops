import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppLayout } from '@/components/layout'
import { NewAnalysisModal } from '@/components/modals'
import { ErrorBoundary } from '@/components/common'
import { ChatInterface } from '@/components/chat'

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
          <ChatInterface />
        </AppLayout>

        {/* Modals */}
        <NewAnalysisModal />
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
