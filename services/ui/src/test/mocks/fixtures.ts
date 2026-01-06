import { QueryResult } from '@/types/queryResult'
import { TableRenderSpec, ChartRenderSpec, LogRenderSpec, TextRenderSpec } from '@/types/renderSpec'
import { ChatResponse, ConversationSession } from '@/types/chat'

// Mock Query Result for Table
export const mockTableResult: QueryResult = {
  requestId: 'req-table-001',
  status: 'success',
  data: {
    rows: [
      { id: 'TXN_9823491', date: '2024-10-24T10:42:00Z', amount: 4250.00, status: 'Failed', merchant: 'Uber Technologies' },
      { id: 'TXN_9823442', date: '2024-10-24T10:38:00Z', amount: 1299.00, status: 'Success', merchant: 'Shopify Inc.' },
      { id: 'TXN_9823122', date: '2024-10-24T10:15:00Z', amount: 342.50, status: 'Pending', merchant: 'Netflix Services' },
      { id: 'TXN_9822901', date: '2024-10-24T09:55:00Z', amount: 89.00, status: 'Success', merchant: 'Spotify AB' },
      { id: 'TXN_9822844', date: '2024-10-24T09:23:00Z', amount: 2100.00, status: 'Success', merchant: 'Adobe Creative' },
      { id: 'TXN_9822510', date: '2024-10-24T08:45:00Z', amount: 125.50, status: 'Refunded', merchant: 'Amazon Marketplace' },
      { id: 'TXN_9822419', date: '2024-10-24T08:12:00Z', amount: 560.00, status: 'Failed', merchant: 'Google Cloud' },
      { id: 'TXN_9822301', date: '2024-10-24T07:55:00Z', amount: 750.00, status: 'Success', merchant: 'Microsoft Azure' },
    ],
  },
  metadata: {
    executionTimeMs: 125,
    rowsReturned: 8,
  },
}

// Mock Query Result for Chart
export const mockChartResult: QueryResult = {
  requestId: 'req-chart-001',
  status: 'success',
  data: {
    rows: [
      { name: 'Oct 18', value: 25000 },
      { name: 'Oct 19', value: 32000 },
      { name: 'Oct 20', value: 28000 },
      { name: 'Oct 21', value: 38420 },
      { name: 'Oct 22', value: 42000 },
      { name: 'Oct 23', value: 45000 },
      { name: 'Oct 24', value: 48200 },
    ],
  },
  metadata: {
    executionTimeMs: 45,
    rowsReturned: 7,
  },
}

// Mock Query Result for Logs
export const mockLogResult: QueryResult = {
  requestId: 'req-log-001',
  status: 'success',
  data: {
    logs: [
      { timestamp: '2024-10-24T10:41:55.021Z', level: 'info', message: '[System] Log viewer initialized.' },
      { timestamp: '2024-10-24T10:41:55.240Z', level: 'info', message: '[AuthService] Token validation successful.' },
      { timestamp: '2024-10-24T10:42:01.112Z', level: 'error', message: '[PaymentGateway] Connection timeout.' },
      { timestamp: '2024-10-24T10:42:01.115Z', level: 'warn', message: '[RetryQueue] Scheduled retry in 500ms.' },
      { timestamp: '2024-10-24T10:42:01.620Z', level: 'info', message: '[PaymentGateway] Retry 1 initiated.' },
      { timestamp: '2024-10-24T10:42:02.850Z', level: 'info', message: '[PaymentGateway] Response: 200 OK.' },
      { timestamp: '2024-10-24T10:42:02.855Z', level: 'debug', message: '[AuditTrail] Transaction captured.' },
    ],
  },
  metadata: {
    executionTimeMs: 12,
    rowsReturned: 7,
  },
}

// Empty result for text
export const emptyResult: QueryResult = {
  requestId: 'req-text-001',
  status: 'success',
  data: {},
  metadata: {
    executionTimeMs: 0,
    rowsReturned: 0,
  },
}

// Table RenderSpec
export const tableSpec: TableRenderSpec = {
  type: 'table',
  requestId: 'req-table-001',
  title: 'Recent Transactions',
  description: 'PG, Payment, Settlement & Purchase Logs',
  dataRef: '$.data.rows',
  columns: [
    { key: 'id', label: 'Transaction ID', type: 'string', sortable: true },
    { key: 'date', label: 'Date', type: 'date', sortable: true },
    { key: 'amount', label: 'Amount', type: 'currency', sortable: true },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'merchant', label: 'Merchant', type: 'string' },
  ],
  actions: ['export', 'filter', 'fullscreen'],
  pagination: { enabled: true },
}

// Chart RenderSpec
export const chartSpec: ChartRenderSpec = {
  type: 'chart',
  requestId: 'req-chart-001',
  title: 'Transaction Volume Trends',
  description: 'Last 7 Days',
  chartType: 'area',
  dataRef: '$.data.rows',
  xAxisKey: 'name',
  yAxisKey: 'value',
  config: {
    showGrid: true,
    showLegend: true,
  },
}

// Log RenderSpec
export const logSpec: LogRenderSpec = {
  type: 'log',
  requestId: 'req-log-001',
  title: 'server-err.log',
  description: 'Last 7 entries',
  dataRef: '$.data.logs',
  searchable: true,
  filterByLevel: true,
}

// Text RenderSpec
export const textSpec: TextRenderSpec = {
  type: 'text',
  requestId: 'req-text-001',
  title: 'Settlement Failure Analysis',
  content: `## Analysis Summary

Based on the transaction data, here are the key findings:

### Key Points

1. **Total Failures**: 142 transactions failed
2. **Primary Error**: Error 503 accounts for 60%

### Recommendations

- Monitor the gateway connection
- Review the retry queue configuration
`,
  sections: [
    {
      type: 'info',
      content: 'This analysis is based on real-time data.',
    },
  ],
}

// Chat Response
export const mockChatResponse: ChatResponse = {
  requestId: 'req-001',
  renderSpec: tableSpec,
  queryResult: mockTableResult,
  aiMessage: 'Here are the recent transactions you requested.',
  timestamp: new Date().toISOString(),
}

// Session
export const mockSession: ConversationSession = {
  id: 'session-test-001',
  title: 'Test Session',
  subtitle: 'Testing conversation',
  icon: 'chat',
  timestamp: new Date().toISOString(),
  category: 'today',
  messages: [],
}
