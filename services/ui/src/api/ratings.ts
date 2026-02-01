import { aiClient } from './client'

export interface RatingRequest {
  requestId: string
  rating: number
  feedback?: string
  sessionId?: string
}

export interface RatingResponse {
  requestId: string
  rating: number
  savedAt: string
}

export interface RatingDetailResponse {
  requestId: string
  rating: number
  feedback?: string
  createdAt: string
}

export const ratingsApi = {
  saveRating: async (request: RatingRequest): Promise<RatingResponse> => {
    const response = await aiClient.post('/api/v1/ratings', request)
    return response.data
  },

  getRating: async (requestId: string): Promise<RatingDetailResponse> => {
    const response = await aiClient.get(`/api/v1/ratings/${requestId}`)
    return response.data
  },

  getRatingsBySession: async (sessionId: string): Promise<RatingDetailResponse[]> => {
    const response = await aiClient.get(`/api/v1/ratings/session/${sessionId}`)
    return response.data.ratings
  },
}
