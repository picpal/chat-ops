/**
 * 클라이언트 사이드 필터링 유틸리티
 * filter_local 응답 처리를 위한 함수들
 */

import type { QueryFilter, FilterOperator } from '../types/queryPlan'

// Debug: 필터 로깅을 한 번만 하기 위한 플래그
let filterLoggedOnce = false

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
 * 단일 필터 조건을 평가
 */
function evaluateFilter(item: Record<string, unknown>, filter: QueryFilter): boolean {
  const fieldValue = getFieldValue(item, filter.field)
  const filterValue = filter.value

  // Debug: 필터 평가 과정 로깅 (한 번만)
  if (import.meta.env.DEV && !filterLoggedOnce) {
    filterLoggedOnce = true
    const snakeCaseField = toSnakeCase(filter.field)
    console.log('[filterUtils] Evaluating filter (first item):', {
      field: filter.field,
      snakeCaseField,
      operator: filter.operator,
      filterValue,
      fieldValue,
      matchFound: fieldValue !== undefined,
    })
  }

  switch (filter.operator as FilterOperator) {
    case 'eq':
      return fieldValue === filterValue

    case 'ne':
      return fieldValue !== filterValue

    case 'gt':
      return typeof fieldValue === 'number' && typeof filterValue === 'number'
        ? fieldValue > filterValue
        : String(fieldValue) > String(filterValue)

    case 'gte':
      return typeof fieldValue === 'number' && typeof filterValue === 'number'
        ? fieldValue >= filterValue
        : String(fieldValue) >= String(filterValue)

    case 'lt':
      return typeof fieldValue === 'number' && typeof filterValue === 'number'
        ? fieldValue < filterValue
        : String(fieldValue) < String(filterValue)

    case 'lte':
      return typeof fieldValue === 'number' && typeof filterValue === 'number'
        ? fieldValue <= filterValue
        : String(fieldValue) <= String(filterValue)

    case 'in':
      if (Array.isArray(filterValue)) {
        return filterValue.includes(fieldValue)
      }
      return false

    case 'like':
      // 대소문자 무시 부분 문자열 매칭
      return String(fieldValue)
        .toLowerCase()
        .includes(String(filterValue).toLowerCase())

    case 'between':
      if (Array.isArray(filterValue) && filterValue.length === 2) {
        const [min, max] = filterValue
        if (typeof fieldValue === 'number') {
          return fieldValue >= Number(min) && fieldValue <= Number(max)
        }
        return String(fieldValue) >= String(min) && String(fieldValue) <= String(max)
      }
      return false

    default:
      console.warn(`Unknown filter operator: ${filter.operator}`)
      return true
  }
}

/**
 * 데이터 배열에 필터 조건들을 적용
 * 모든 필터가 AND 조건으로 적용됨
 */
export function applyFilters<T extends Record<string, unknown>>(
  data: T[],
  filters: QueryFilter[]
): T[] {
  if (!filters || filters.length === 0) {
    return data
  }

  return data.filter((item) => {
    return filters.every((filter) => evaluateFilter(item, filter))
  })
}

/**
 * 필터 조건을 사람이 읽기 쉬운 문자열로 변환
 */
export function formatFilterDescription(filters: QueryFilter[]): string {
  if (!filters || filters.length === 0) {
    return '필터 없음'
  }

  const operatorLabels: Record<FilterOperator, string> = {
    eq: '=',
    ne: '≠',
    gt: '>',
    gte: '≥',
    lt: '<',
    lte: '≤',
    in: 'IN',
    like: 'LIKE',
    between: 'BETWEEN',
  }

  return filters
    .map((filter) => {
      const op = operatorLabels[filter.operator as FilterOperator] || filter.operator
      if (filter.operator === 'between' && Array.isArray(filter.value)) {
        return `${filter.field} ${filter.value[0]}~${filter.value[1]}`
      }
      if (filter.operator === 'in' && Array.isArray(filter.value)) {
        return `${filter.field} IN [${filter.value.join(', ')}]`
      }
      return `${filter.field} ${op} ${filter.value}`
    })
    .join(', ')
}
