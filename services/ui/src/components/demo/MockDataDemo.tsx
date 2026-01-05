/**
 * Mock Data Demo Component
 * 테스트용 컴포넌트 - 모든 Renderer와 Modal을 테스트할 수 있습니다.
 *
 * 사용법: ChatInterface 대신 이 컴포넌트를 AppLayout에 넣으면 됩니다.
 */
import React from 'react'
import { RenderSpecDispatcher } from '@/components/renderers'
import { TableRenderSpec, ChartRenderSpec, LogRenderSpec, TextRenderSpec } from '@/types/renderSpec'
import { QueryResult } from '@/types/queryResult'

// Mock Query Result for Table
const mockTableResult: QueryResult = {
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
const mockChartResult: QueryResult = {
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
const mockLogResult: QueryResult = {
  requestId: 'req-log-001',
  status: 'success',
  data: {
    logs: [
      { timestamp: '2024-10-24T10:41:55.021Z', level: 'info', message: '[System] Log viewer initialized. Session ID: sess_882190' },
      { timestamp: '2024-10-24T10:41:55.240Z', level: 'info', message: '[AuthService] Token validation successful for user_id: 4492.' },
      { timestamp: '2024-10-24T10:42:01.112Z', level: 'error', message: "[PaymentGateway] Connection timeout to provider 'Stripe'. Retry count: 1." },
      { timestamp: '2024-10-24T10:42:01.115Z', level: 'warn', message: '[RetryQueue] Scheduled retry for txn_9823491 in 500ms.' },
      { timestamp: '2024-10-24T10:42:01.620Z', level: 'info', message: '[PaymentGateway] Retry 1 initiated. Payload size: 2kb.' },
      { timestamp: '2024-10-24T10:42:02.850Z', level: 'info', message: '[PaymentGateway] Response received: 200 OK. Transaction authorized.' },
      { timestamp: '2024-10-24T10:42:02.855Z', level: 'debug', message: '[AuditTrail] Payload: {"txn_id":"9823491", "status":"captured", "merchant":"Uber", "amount":4250.00}' },
    ],
  },
  metadata: {
    executionTimeMs: 12,
    rowsReturned: 7,
  },
}

// Empty result for text (text doesn't need query data)
const emptyResult: QueryResult = {
  requestId: 'req-text-001',
  status: 'success',
  data: {},
  metadata: {
    executionTimeMs: 0,
    rowsReturned: 0,
  },
}

// Table RenderSpec
const tableSpec: TableRenderSpec = {
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
const chartSpec: ChartRenderSpec = {
  type: 'chart',
  requestId: 'req-chart-001',
  title: 'Transaction Volume Trends',
  description: 'Last 7 Days • Data updated 2m ago',
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
const logSpec: LogRenderSpec = {
  type: 'log',
  requestId: 'req-log-001',
  title: 'server-err.log',
  description: 'Last 7 entries',
  dataRef: '$.data.logs',
  searchable: true,
  filterByLevel: true,
}

// Text RenderSpec
const textSpec: TextRenderSpec = {
  type: 'text',
  requestId: 'req-text-001',
  title: 'Settlement Failure Analysis',
  content: `## Analysis Summary

Based on the transaction data from the last 24 hours, here are the key findings:

### Key Points

1. **Total Failures**: 142 transactions failed (12% decrease vs previous 24h)
2. **Primary Error**: Error 503 (Service Unavailable) accounts for 60% of failures
3. **Secondary Issues**: Authentication failures (Error 401) at 18%

### Recommendations

- Monitor the Stripe gateway connection - multiple timeouts detected
- Review the retry queue configuration for optimal performance
- Consider implementing circuit breaker pattern for external API calls

> **Note**: The success rate has improved by 3% compared to last week.
`,
  sections: [
    {
      type: 'info',
      content: 'This analysis is based on real-time transaction data.',
    },
  ],
}

const MockDataDemo: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Demo Header */}
      <div className="bg-gradient-to-r from-primary to-blue-400 text-white rounded-xl p-6 shadow-lg">
        <h1 className="text-2xl font-bold mb-2">Mock Data Demo</h1>
        <p className="text-blue-100">
          테스트용 페이지입니다. 각 카드의 <strong>Fullscreen 버튼</strong>을 클릭하여 Modal을 테스트하세요.
        </p>
      </div>

      {/* Table Renderer */}
      <RenderSpecDispatcher renderSpec={tableSpec} queryResult={mockTableResult} />

      {/* Chart Renderer */}
      <RenderSpecDispatcher renderSpec={chartSpec} queryResult={mockChartResult} />

      {/* Log Renderer */}
      <RenderSpecDispatcher renderSpec={logSpec} queryResult={mockLogResult} />

      {/* Text Renderer */}
      <RenderSpecDispatcher renderSpec={textSpec} queryResult={emptyResult} />
    </div>
  )
}

export default MockDataDemo
