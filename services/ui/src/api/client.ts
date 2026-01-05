import axios, { AxiosInstance, AxiosError } from 'axios'

const AI_ORCHESTRATOR_BASE_URL =
  import.meta.env.VITE_AI_API_URL || 'http://localhost:8000'
const CORE_API_BASE_URL =
  import.meta.env.VITE_CORE_API_URL || 'http://localhost:8080'

// AI Orchestrator client
export const aiClient: AxiosInstance = axios.create({
  baseURL: AI_ORCHESTRATOR_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Core API client
export const coreApiClient: AxiosInstance = axios.create({
  baseURL: CORE_API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for authentication
const authInterceptor = (config: any) => {
  const token = localStorage.getItem('authToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}

// Response interceptor for error handling
const errorInterceptor = (error: AxiosError) => {
  if (error.response?.status === 401) {
    // Handle unauthorized - redirect to login or refresh token
    console.error('Unauthorized access - token may be invalid or expired')
    localStorage.removeItem('authToken')
  }

  if (error.response?.status === 500) {
    console.error('Server error:', error.response.data)
  }

  return Promise.reject(error)
}

// Add interceptors to both clients
aiClient.interceptors.request.use(authInterceptor, (error) => Promise.reject(error))
aiClient.interceptors.response.use((response) => response, errorInterceptor)

coreApiClient.interceptors.request.use(authInterceptor, (error) => Promise.reject(error))
coreApiClient.interceptors.response.use((response) => response, errorInterceptor)
