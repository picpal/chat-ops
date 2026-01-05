export type RenderSpecType = 'table' | 'text' | 'chart' | 'log' | 'composite'

export interface BaseRenderSpec {
  type: RenderSpecType
  requestId: string
  title?: string
  description?: string
}

// Table Renderer Types
export interface TableColumn {
  key: string
  label: string
  type: 'string' | 'number' | 'date' | 'status' | 'currency'
  format?: string
  sortable?: boolean
  width?: string
}

export interface TableRenderSpec extends BaseRenderSpec {
  type: 'table'
  columns: TableColumn[]
  dataRef: string // JSONPath reference to data in QueryResult
  pagination?: {
    enabled: boolean
    queryToken?: string
    hasMore?: boolean
  }
  actions?: Array<'export' | 'filter' | 'fullscreen'>
}

// Text Renderer Types
export interface TextSection {
  type: 'info' | 'warning' | 'error' | 'success'
  title?: string
  content: string
}

export interface TextRenderSpec extends BaseRenderSpec {
  type: 'text'
  content: string
  sections?: TextSection[]
  markdown?: boolean
}

// Chart Renderer Types
export type ChartType = 'bar' | 'line' | 'pie' | 'area'

export interface ChartRenderSpec extends BaseRenderSpec {
  type: 'chart'
  chartType: ChartType
  dataRef: string // JSONPath reference to data in QueryResult
  xAxisKey: string
  yAxisKey: string
  config?: {
    showGrid?: boolean
    showLegend?: boolean
    colors?: string[]
    title?: string
  }
}

// Log Renderer Types
export interface LogEntry {
  timestamp: string
  level: 'info' | 'warn' | 'error' | 'debug'
  message: string
  metadata?: Record<string, any>
}

export interface LogRenderSpec extends BaseRenderSpec {
  type: 'log'
  dataRef: string // JSONPath reference to log data in QueryResult
  searchable?: boolean
  filterByLevel?: boolean
}

// Composite Renderer Types
export interface CompositeRenderSpec extends BaseRenderSpec {
  type: 'composite'
  components: RenderSpec[]
}

// Union type for all RenderSpec types
export type RenderSpec =
  | TableRenderSpec
  | TextRenderSpec
  | ChartRenderSpec
  | LogRenderSpec
  | CompositeRenderSpec
