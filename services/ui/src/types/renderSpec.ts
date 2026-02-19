export type RenderSpecType = 'table' | 'text' | 'chart' | 'log' | 'log_analysis' | 'composite' | 'clarification' | 'filter_local' | 'aggregate_local' | 'download'

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
  metadata?: {
    sql?: string
    executionTimeMs?: number
  }
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

// AI-generated insight for chart data
export interface InsightConfig {
  content: string | null
  source: 'llm' | 'template' | 'none'
}

// Summary Stats item for dynamic chart statistics
export interface SummaryStatItem {
  key: string                          // 항목 고유 키 (예: max_share, total, trend)
  label: string                        // 표시 라벨 (한국어, 예: 최대 비중)
  value: string | number | null        // 표시 값
  type: 'number' | 'currency' | 'percentage' | 'text' | 'trend'
  highlight?: boolean                  // 강조 표시 여부
  icon?: string                        // Material Icon 이름
}

// Summary Stats configuration
export interface SummaryStatsConfig {
  items: SummaryStatItem[]
  source: 'llm' | 'rule' | 'fallback'
}

// Data Source configuration for chart
export interface DataSourceConfig {
  table?: string | null  // 테이블명 (SQL에서 추출)
  rowCount?: number      // 조회 건수
}

export interface ChartConfig {
  chartType: ChartType
  dataRef?: string
  xAxis?: ChartAxis
  yAxis?: ChartAxis
  series?: ChartSeries[]
  legend?: boolean
  tooltip?: boolean
  insight?: InsightConfig  // AI가 생성한 인사이트
  summaryStats?: SummaryStatsConfig  // 차트 유형에 맞는 동적 Summary Stats
  dataSource?: DataSourceConfig  // 데이터 소스 정보 (테이블명, 건수)
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

// Log Analysis Renderer Types
export interface LogAnalysisStatistics {
  totalEntries: number
  errorCount: number
  warnCount: number
  timeRange?: string
}

export interface LogAnalysisEntry {
  timestamp: string | null
  level: string
  message: string
}

export interface LogAnalysisConfig {
  summary: string
  statistics: LogAnalysisStatistics
  entries: LogAnalysisEntry[]
}

export interface LogAnalysisRenderSpec extends BaseRenderSpec {
  type: 'log_analysis'
  log_analysis: LogAnalysisConfig
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
    // 기간 선택 clarification용 (서버에서 보내는 새 메시지 트리거)
    originalQuestion?: string
    clarificationType?: 'timerange_selection' | 'filter_local' | 'aggregate_local'
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

// Download Renderer Types (대용량 데이터 다운로드)
export interface DownloadConfig {
  totalRows: number
  maxDisplayRows: number
  message: string
  sql: string
  formats: ('csv' | 'excel')[]
}

export interface DownloadRenderSpec extends Omit<BaseRenderSpec, 'requestId'> {
  type: 'download'
  download: DownloadConfig
  requestId?: string
  metadata?: {
    sql?: string
    executionTimeMs?: number
    mode?: string
  }
}

// Union type for all RenderSpec types
export type RenderSpec =
  | TableRenderSpec
  | TextRenderSpec
  | ChartRenderSpec
  | LogRenderSpec
  | LogAnalysisRenderSpec
  | CompositeRenderSpec
  | ClarificationRenderSpec
  | FilterLocalRenderSpec
  | AggregateLocalRenderSpec
  | DownloadRenderSpec
