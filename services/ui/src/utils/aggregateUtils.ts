/**
 * 클라이언트 사이드 집계 유틸리티
 * aggregate_local 응답 처리를 위한 함수들
 */

export type AggregationFunction = 'sum' | 'avg' | 'count' | 'min' | 'max'

export interface Aggregation {
  function: AggregationFunction
  field: string
  alias?: string
  displayLabel?: string  // LLM이 생성한 한글 레이블
  currency?: string | null  // 화폐 단위: 'USD', 'KRW', null
}

export interface AggregationResult {
  [alias: string]: number
}

// Debug: 집계 로깅을 한 번만 하기 위한 플래그
let aggregateLoggedOnce = false

/**
 * camelCase를 snake_case로 변환
 * 예: orderName → order_name
 */
function toSnakeCase(str: string): string {
  return str.replace(/([A-Z])/g, '_$1').toLowerCase()
}

/**
 * 필드명으로 값을 찾음 (camelCase와 snake_case 모두 시도)
 */
function getFieldValue(item: Record<string, unknown>, fieldName: string): unknown {
  // 1. 원본 필드명으로 시도
  if (fieldName in item) {
    return item[fieldName]
  }

  // 2. snake_case로 변환하여 시도
  const snakeCaseField = toSnakeCase(fieldName)
  if (snakeCaseField in item) {
    return item[snakeCaseField]
  }

  // 3. 찾지 못함
  return undefined
}

/**
 * 값을 숫자로 변환
 * 숫자가 아닌 경우 NaN 반환
 */
function toNumber(value: unknown): number {
  if (typeof value === 'number') {
    return value
  }
  if (typeof value === 'string') {
    const parsed = parseFloat(value)
    return isNaN(parsed) ? NaN : parsed
  }
  return NaN
}

/**
 * 단일 집계 함수를 적용
 */
function applyAggregation(
  data: Record<string, unknown>[],
  aggregation: Aggregation
): number {
  const { function: aggFunc, field } = aggregation

  // Debug: 집계 과정 로깅 (한 번만)
  if (import.meta.env.DEV && !aggregateLoggedOnce) {
    aggregateLoggedOnce = true
    console.log('[aggregateUtils] Applying aggregation (first):', {
      function: aggFunc,
      field,
      dataLength: data.length,
      sampleItem: data[0],
    })
  }

  // count는 필드 값과 무관하게 행 수를 센다
  if (aggFunc === 'count') {
    return data.length
  }

  // 나머지 집계 함수는 숫자 값만 대상으로 함
  const numericValues = data
    .map((item) => toNumber(getFieldValue(item, field)))
    .filter((val) => !isNaN(val))

  if (numericValues.length === 0) {
    console.warn(`[aggregateUtils] No numeric values found for field: ${field}`)
    return 0
  }

  switch (aggFunc) {
    case 'sum':
      return numericValues.reduce((acc, val) => acc + val, 0)

    case 'avg':
      return numericValues.reduce((acc, val) => acc + val, 0) / numericValues.length

    case 'min':
      return Math.min(...numericValues)

    case 'max':
      return Math.max(...numericValues)

    default:
      console.warn(`[aggregateUtils] Unknown aggregation function: ${aggFunc}`)
      return 0
  }
}

/**
 * 데이터 배열에 집계 함수들을 적용
 */
export function aggregateData(
  data: Record<string, unknown>[],
  aggregations: Aggregation[]
): AggregationResult {
  if (!data || data.length === 0) {
    console.warn('[aggregateUtils] Empty data array provided')
    return {}
  }

  if (!aggregations || aggregations.length === 0) {
    console.warn('[aggregateUtils] No aggregations provided')
    return {}
  }

  const result: AggregationResult = {}

  for (const aggregation of aggregations) {
    const alias = aggregation.alias || `${aggregation.function}_${aggregation.field}`
    result[alias] = applyAggregation(data, aggregation)
  }

  return result
}

/**
 * 집계 함수명을 한글로 변환
 */
function getAggregationLabel(func: AggregationFunction): string {
  const labels: Record<AggregationFunction, string> = {
    sum: '합계',
    avg: '평균',
    count: '건수',
    min: '최소값',
    max: '최대값',
  }
  return labels[func] || func
}

/**
 * 집계 결과를 사람이 읽기 쉬운 문자열로 변환
 */
export function formatAggregationDescription(aggregations: Aggregation[]): string {
  if (!aggregations || aggregations.length === 0) {
    return '집계 없음'
  }

  return aggregations
    .map((agg) => {
      const label = getAggregationLabel(agg.function)
      return `${agg.field} ${label}`
    })
    .join(', ')
}

/**
 * 화폐 단위에 맞게 금액 포맷팅
 */
function formatCurrency(value: number, currency?: string | null): string {
  const absValue = Math.abs(value)
  const sign = value < 0 ? '-' : ''

  if (currency === 'KRW') {
    // 원화: 억, 만 단위
    if (absValue >= 100000000) {
      const eok = Math.floor(absValue / 100000000)
      const remainder = absValue % 100000000
      if (remainder >= 10000) {
        const man = Math.floor(remainder / 10000)
        return `${sign}${eok.toLocaleString()}억 ${man.toLocaleString()}만원`
      }
      return `${sign}${eok.toLocaleString()}억원`
    } else if (absValue >= 10000) {
      const man = Math.floor(absValue / 10000)
      return `${sign}${man.toLocaleString()}만원`
    }
    return `${sign}₩${absValue.toLocaleString()}`
  } else if (currency === 'USD') {
    // 달러: K, M 단위
    if (absValue >= 1000000) {
      const millions = absValue / 1000000
      return `${sign}$${millions.toLocaleString(undefined, { maximumFractionDigits: 2 })}M`
    } else if (absValue >= 1000) {
      const thousands = absValue / 1000
      return `${sign}$${thousands.toLocaleString(undefined, { maximumFractionDigits: 1 })}K`
    }
    return `${sign}$${absValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  // 화폐 단위 없음: 일반 숫자
  return `${sign}${absValue.toLocaleString()}`
}

/**
 * 집계 결과를 마크다운 형식으로 포맷
 * LLM이 제공한 displayLabel과 currency를 우선 사용
 */
export function formatAggregationResultMarkdown(
  result: AggregationResult,
  aggregations: Aggregation[]
): string {
  const lines: string[] = []

  for (const agg of aggregations) {
    const alias = agg.alias || `${agg.function}_${agg.field}`
    const value = result[alias]

    if (value !== undefined) {
      // LLM이 제공한 레이블 사용, 없으면 기본 레이블
      const label = agg.displayLabel || `${agg.field} ${getAggregationLabel(agg.function)}`

      // 숫자 포맷팅
      let formattedValue: string

      if (agg.function === 'count') {
        formattedValue = `${value.toLocaleString()}건`
      } else if (agg.currency) {
        // LLM이 지정한 화폐 단위 사용
        formattedValue = formatCurrency(value, agg.currency)
        // 정확한 금액도 병기
        const symbol = agg.currency === 'KRW' ? '₩' : '$'
        formattedValue += ` (${symbol}${value.toLocaleString()})`
      } else if (agg.function === 'avg') {
        formattedValue = value.toLocaleString(undefined, {
          minimumFractionDigits: 0,
          maximumFractionDigits: 2,
        })
      } else {
        formattedValue = value.toLocaleString()
      }

      lines.push(`**${label}**: ${formattedValue}`)
    }
  }

  return lines.join('\n\n')
}
