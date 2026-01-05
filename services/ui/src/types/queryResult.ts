export type QueryStatus = 'success' | 'error' | 'partial'

export interface QueryResult {
  requestId: string
  status: QueryStatus
  data: {
    rows?: Array<Record<string, any>>
    aggregations?: Record<string, any>
    logs?: Array<{
      timestamp: string
      level: 'info' | 'warn' | 'error' | 'debug'
      message: string
      metadata?: Record<string, any>
    }>
  }
  metadata: {
    executionTimeMs: number
    rowsReturned: number
    queryToken?: string
    hasMore?: boolean
  }
  error?: {
    code: string
    message: string
    details?: any
  }
}

export interface PaginationResponse {
  queryToken: string
  hasMore: boolean
  data: Array<Record<string, any>>
}
