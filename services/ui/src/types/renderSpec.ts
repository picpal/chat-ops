export type RenderSpecType = 'table' | 'text' | 'chart' | 'log' | 'composite' | 'clarification' | 'filter_local' | 'aggregate_local'

// Server-side pagination info (added by RenderComposer)
export interface ServerPaginationInfo {
  queryToken: string
  hasMore: boolean
  currentPage: number
  totalRows?: number
  totalPages?: number
  pageSize?: number
}

export interface BaseRenderSpec {
  type: RenderSpecType
  requestId: string
  title?: string
  description?: string
  pagination?: ServerPaginationInfo // Server-side pagination metadata
}

// Table Renderer Types
export interface TableColumn {
  key: string
  label: string
  type: 'string' | 'number' | 'date' | 'status' | 'currency' | 'boolean' | 'percentage'
  format?: string
  align?: 'left' | 'center' | 'right'
  sortable?: boolean
  width?: string
}

export interface TableAction {
  label: string
  action: 'export-csv' | 'fullscreen' | 'refresh' | 'custom'
  icon?: string
}

export interface TableConfig {
  columns: TableColumn[]
  dataRef: string // JSONPath reference to data in QueryResult (default: "data.rows")
  data?: any[] // Inline data (takes priority over dataRef, used for preview mode)
  actions?: TableAction[]
  pagination?: {
    enabled: boolean
    type?: 'load-more' | 'infinite-scroll' | 'page-numbers'
    pageSize?: number
    queryToken?: string
    hasMore?: boolean
    totalRows?: number
  }
}

// Preview mode config (for Text-to-SQL results)
export interface PreviewConfig {
  enabled: boolean
  previewRows: number
  totalRows: number
  message?: string
}

export interface TableRenderSpec extends BaseRenderSpec {
  type: 'table'
  table: TableConfig
  fullData?: any[]  // Full data for modal (when preview mode is enabled)
  preview?: PreviewConfig
}

// Text Renderer Types
export interface TextSection {
  type: 'info' | 'warning' | 'error' | 'success'
  title?: string
  content: string
}

export interface TextConfig {
  content: string
  format?: 'markdown' | 'plain' | 'html'
  sections?: TextSection[]
}

export interface TextRenderSpec extends BaseRenderSpec {
  type: 'text'
  text?: TextConfig
  // Legacy support - direct properties
  content?: string
  sections?: TextSection[]
  markdown?: boolean
}

// Chart Renderer Types
export type ChartType = 'bar' | 'line' | 'pie' | 'area' | 'scatter' | 'composed'
export type AxisType = 'category' | 'number' | 'time'
export type SeriesType = 'bar' | 'line' | 'area'

export interface ChartAxis {
  dataKey: string
  label?: string
  type?: AxisType
}

export interface ChartSeries {
  dataKey: string
  name?: string
  color?: string
  type?: SeriesType
}

export interface ChartConfig {
  chartType: ChartType
  dataRef?: string
  xAxis?: ChartAxis
  yAxis?: ChartAxis
  series?: ChartSeries[]
  legend?: boolean
  tooltip?: boolean
}

export interface ChartRenderSpec extends BaseRenderSpec {
  type: 'chart'
  chart: ChartConfig
  data?: any // inline data if not using dataRef
}

// Log Renderer Types
export interface LogEntry {
  timestamp: string
  level: 'info' | 'warn' | 'error' | 'debug'
  message: string
  metadata?: Record<string, any>
}

export interface LogConfig {
  dataRef: string // JSONPath reference to log data in QueryResult (default: "data.rows")
  timestampKey?: string // Timestamp field key (default: "timestamp")
  levelKey?: string // Log level field key (default: "level")
  messageKey?: string // Log message field key (default: "message")
  highlight?: string[] // Keywords to highlight
  filter?: {
    levels?: Array<'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'FATAL'>
    searchable?: boolean
  }
}

export interface LogRenderSpec extends BaseRenderSpec {
  type: 'log'
  log?: LogConfig
  // Legacy support - direct properties
  dataRef?: string
  searchable?: boolean
  filterByLevel?: boolean
}

// Composite Renderer Types
export interface CompositeRenderSpec extends BaseRenderSpec {
  type: 'composite'
  components: RenderSpec[]
}

// Clarification Renderer Types
export interface ClarificationConfig {
  question: string
  options: string[]
}

export interface ClarificationRenderSpec extends Omit<BaseRenderSpec, 'requestId'> {
  type: 'clarification'
  clarification: ClarificationConfig
  requestId?: string
  metadata?: {
    requestId?: string
    targetResultIndices?: number[]
    pendingFilters?: Array<{ field: string; operator: string; value: unknown }>
    pendingAggregations?: Array<{
      function: 'sum' | 'avg' | 'count' | 'min' | 'max'
      field: string
      alias?: string
    }>
    aggregationType?: 'aggregate_local'
    generatedAt?: string
  }
}

// Filter Local Renderer Types (클라이언트 사이드 필터링)
export interface FilterLocalRenderSpec extends Omit<BaseRenderSpec, 'requestId'> {
  type: 'filter_local'
  filter: Array<{ field: string; operator: string; value: unknown }>
  targetResultIndex: number
  requestId?: string
  metadata?: {
    requestId?: string
    generatedAt?: string
  }
}

// Aggregate Local Renderer Types (클라이언트 사이드 집계)
export interface AggregateLocalRenderSpec extends Omit<BaseRenderSpec, 'requestId'> {
  type: 'aggregate_local'
  aggregations: Array<{
    function: 'sum' | 'avg' | 'count' | 'min' | 'max'
    field: string
    alias?: string
  }>
  targetResultIndex: number
  requestId?: string
  metadata?: {
    requestId?: string
    generatedAt?: string
  }
}

// Union type for all RenderSpec types
export type RenderSpec =
  | TableRenderSpec
  | TextRenderSpec
  | ChartRenderSpec
  | LogRenderSpec
  | CompositeRenderSpec
  | ClarificationRenderSpec
  | FilterLocalRenderSpec
  | AggregateLocalRenderSpec
