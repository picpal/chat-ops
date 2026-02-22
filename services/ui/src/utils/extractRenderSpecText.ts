import { RenderSpec, TextRenderSpec, TableRenderSpec, ChartRenderSpec, LogAnalysisRenderSpec, ClarificationRenderSpec, LogRenderSpec, CompositeRenderSpec, FilterLocalRenderSpec, AggregateLocalRenderSpec, DownloadRenderSpec } from '@/types/renderSpec'
import { QueryResult } from '@/types/queryResult'

const MAX_TABLE_ROWS = 20
const MAX_COMPOSITE_DEPTH = 3

function extractTextSpec(renderSpec: TextRenderSpec): string {
  const parts: string[] = []

  // text.content 우선, 없으면 레거시 content
  const mainContent = renderSpec.text?.content ?? renderSpec.content
  if (mainContent) {
    parts.push(mainContent)
  }

  // sections 처리
  const sections = renderSpec.text?.sections ?? renderSpec.sections
  if (sections && sections.length > 0) {
    for (const section of sections) {
      if (section.title) {
        parts.push(`[${section.type.toUpperCase()}] ${section.title}: ${section.content}`)
      } else {
        parts.push(`[${section.type.toUpperCase()}] ${section.content}`)
      }
    }
  }

  return parts.join('\n')
}

function extractTableSpec(renderSpec: TableRenderSpec, queryResult?: QueryResult): string {
  const parts: string[] = []

  const prefix = '[표]'
  if (renderSpec.title) {
    parts.push(`${prefix} ${renderSpec.title}`)
  } else {
    parts.push(prefix)
  }

  const columns = renderSpec.table.columns
  const inlineData = renderSpec.table.data
  const rows = inlineData ?? queryResult?.data?.rows

  if (rows && rows.length > 0 && columns.length > 0) {
    const headers = columns.map(col => col.label).join('\t')
    parts.push(headers)

    const displayRows = rows.slice(0, MAX_TABLE_ROWS)
    for (const row of displayRows) {
      const rowText = columns.map(col => {
        const val = row[col.key]
        return val !== undefined && val !== null ? String(val) : ''
      }).join('\t')
      parts.push(rowText)
    }

    if (rows.length > MAX_TABLE_ROWS) {
      parts.push(`(외 ${rows.length - MAX_TABLE_ROWS}건)`)
    }
  }

  return parts.join('\n')
}

function extractChartSpec(renderSpec: ChartRenderSpec): string {
  const parts: string[] = []

  const prefix = '[차트]'
  if (renderSpec.title) {
    parts.push(`${prefix} ${renderSpec.title}`)
  } else {
    parts.push(prefix)
  }

  const insight = renderSpec.chart.insight
  if (insight?.content) {
    parts.push(`인사이트: ${insight.content}`)
  }

  const summaryStats = renderSpec.chart.summaryStats
  if (summaryStats?.items && summaryStats.items.length > 0) {
    for (const item of summaryStats.items) {
      parts.push(`- ${item.label}: ${item.value}`)
    }
  }

  return parts.join('\n')
}

function extractLogAnalysisSpec(renderSpec: LogAnalysisRenderSpec): string {
  const parts: string[] = []

  const prefix = '[로그 분석]'
  if (renderSpec.title) {
    parts.push(`${prefix} ${renderSpec.title}`)
  } else {
    parts.push(prefix)
  }

  const { summary, statistics } = renderSpec.log_analysis
  if (summary) {
    parts.push(summary)
  }

  if (statistics) {
    parts.push(`통계: 전체 ${statistics.totalEntries}건 | 오류 ${statistics.errorCount}건 | 경고 ${statistics.warnCount}건`)
  }

  return parts.join('\n')
}

function extractClarificationSpec(renderSpec: ClarificationRenderSpec): string {
  const parts: string[] = []

  parts.push(`[확인 질문] ${renderSpec.clarification.question}`)

  const options = renderSpec.clarification.options
  if (options && options.length > 0) {
    options.forEach((option, index) => {
      parts.push(`${index + 1}. ${option}`)
    })
  }

  return parts.join('\n')
}

function extractLogSpec(renderSpec: LogRenderSpec): string {
  const parts: string[] = []

  const prefix = '[로그]'
  if (renderSpec.title) {
    parts.push(`${prefix} ${renderSpec.title}`)
  } else {
    parts.push(prefix)
  }

  if (renderSpec.description) {
    parts.push(renderSpec.description)
  }

  return parts.join('\n')
}

function extractCompositeSpec(renderSpec: CompositeRenderSpec, queryResult?: QueryResult, depth = 0): string {
  if (depth >= MAX_COMPOSITE_DEPTH) {
    return '[복합 컴포넌트]'
  }

  const texts = renderSpec.components.map(component =>
    extractRenderSpecText(component, queryResult, depth + 1)
  )

  return texts.filter(text => text.length > 0).join('\n\n')
}

function extractFilterLocalSpec(renderSpec: FilterLocalRenderSpec): string {
  const prefix = '[필터 적용]'
  if (renderSpec.title) return `${prefix} ${renderSpec.title}`
  if (renderSpec.description) return `${prefix} ${renderSpec.description}`
  return prefix
}

function extractAggregateLocalSpec(renderSpec: AggregateLocalRenderSpec): string {
  const prefix = '[집계 결과]'
  if (renderSpec.title) return `${prefix} ${renderSpec.title}`
  if (renderSpec.description) return `${prefix} ${renderSpec.description}`
  return prefix
}

function extractDownloadSpec(renderSpec: DownloadRenderSpec): string {
  const prefix = '[다운로드]'
  if (renderSpec.download?.message) return `${prefix} ${renderSpec.download.message}`
  if (renderSpec.title) return `${prefix} ${renderSpec.title}`
  if (renderSpec.description) return `${prefix} ${renderSpec.description}`
  return prefix
}

export function extractRenderSpecText(
  renderSpec: RenderSpec,
  queryResult?: QueryResult,
  depth = 0
): string {
  switch (renderSpec.type) {
    case 'text':
      return extractTextSpec(renderSpec)

    case 'table':
      return extractTableSpec(renderSpec, queryResult)

    case 'chart':
      return extractChartSpec(renderSpec)

    case 'log_analysis':
      return extractLogAnalysisSpec(renderSpec)

    case 'clarification':
      return extractClarificationSpec(renderSpec)

    case 'log':
      return extractLogSpec(renderSpec)

    case 'composite':
      return extractCompositeSpec(renderSpec, queryResult, depth)

    case 'filter_local':
      return extractFilterLocalSpec(renderSpec)

    case 'aggregate_local':
      return extractAggregateLocalSpec(renderSpec)

    case 'download':
      return extractDownloadSpec(renderSpec)

    default: {
      // fallback: title 또는 description
      const spec = renderSpec as { title?: string; description?: string }
      return spec.title ?? spec.description ?? ''
    }
  }
}
