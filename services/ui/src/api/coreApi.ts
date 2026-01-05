import { coreApiClient } from './client'
import { QueryResult } from '@/types/queryResult'
import { HealthCheckResponse } from '@/types/api'

export const coreApi = {
  /**
   * Get paginated query results using a queryToken
   */
  getPage: async (queryToken: string): Promise<QueryResult> => {
    const response = await coreApiClient.get<QueryResult>(
      `/api/v1/query/page/${queryToken}`
    )
    return response.data
  },

  /**
   * Check Core API health status
   */
  healthCheck: async (): Promise<HealthCheckResponse> => {
    const response = await coreApiClient.get<HealthCheckResponse>(
      '/api/v1/query/health'
    )
    return response.data
  },
}
