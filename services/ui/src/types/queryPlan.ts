/**
 * QueryPlan - AI Orchestrator가 생성하는 쿼리 계획
 * libs/contracts/query-plan.schema.json 기반
 */

export type EntityType =
  | 'Order'
  | 'Merchant'
  | 'PgCustomer'
  | 'PaymentMethod'
  | 'Payment'
  | 'PaymentHistory'
  | 'Refund'
  | 'BalanceTransaction'
  | 'Settlement'
  | 'SettlementDetail'

export type OperationType = 'list' | 'aggregate' | 'search'

export type QueryIntent = 'new_query' | 'refine_previous' | 'filter_local'

export type FilterOperator =
  | 'eq'
  | 'ne'
  | 'gt'
  | 'gte'
  | 'lt'
  | 'lte'
  | 'in'
  | 'like'
  | 'between'

export type AggregationFunction = 'count' | 'sum' | 'avg' | 'min' | 'max'

export type SortDirection = 'asc' | 'desc'

export interface QueryFilter {
  field: string
  operator: FilterOperator
  value: string | number | boolean | unknown[]
}

export interface QueryAggregation {
  function: AggregationFunction
  field: string
  alias?: string
}

export interface QueryOrderBy {
  field: string
  direction: SortDirection
}

export interface QueryTimeRange {
  start: string
  end: string
}

export interface QueryPlan {
  requestId?: string
  entity: EntityType | string
  operation: OperationType
  filters?: QueryFilter[]
  aggregations?: QueryAggregation[]
  groupBy?: string[]
  orderBy?: QueryOrderBy[]
  limit?: number
  queryToken?: string
  timeRange?: QueryTimeRange
  query_intent?: QueryIntent
  needs_clarification?: boolean
}
