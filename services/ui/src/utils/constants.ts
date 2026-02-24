// API Endpoints
export const API_ENDPOINTS = {
  CHAT: '/api/v1/chat',
  QUERY_PAGE: '/api/v1/query/page',
  QUERY_START: '/api/v1/query/start',
  HEALTH: '/health',
} as const

// Status Colors matching Tailwind theme
export const STATUS_COLORS = {
  success: 'emerald',
  failed: 'red',
  pending: 'amber',
  refunded: 'slate',
  error: 'red',
  warning: 'amber',
  info: 'blue',
} as const

// Query Keys for TanStack Query
export const QUERY_KEYS = {
  CHAT: 'chat',
  PAGINATION: 'pagination',
  SESSIONS: 'sessions',
  HEALTH: 'health',
} as const

// Session Categories
export const SESSION_CATEGORIES = {
  TODAY: 'Today',
  YESTERDAY: 'Yesterday',
  PREVIOUS_7_DAYS: 'Previous 7 Days',
  OLDER: 'Older',
} as const

// Material Symbols Icons
export const ICONS = {
  ADD_CIRCLE: 'add_circle',
  BAR_CHART: 'bar_chart',
  TABLE_CHART: 'table_chart',
  SHOW_CHART: 'show_chart',
  PIE_CHART: 'pie_chart',
  TABLE_ROWS: 'table_rows',
  FILTER_LIST: 'filter_list',
  MORE_VERT: 'more_vert',
  DOWNLOAD: 'download',
  FULLSCREEN: 'fullscreen',
  CLOSE: 'close',
  SEND: 'send',
  MIC: 'mic',
  NOTIFICATIONS: 'notifications',
  SETTINGS: 'settings',
  LOGOUT: 'logout',
  CHECK_CIRCLE: 'check_circle',
  CLEANING_SERVICES: 'cleaning_services',
  CHAT: 'chat',
  MENU: 'menu',
  MENU_OPEN: 'menu_open',
  EDIT_SQUARE: 'edit_square',
  SMART_TOY: 'smart_toy',
  SIDEBAR: 'left_panel_close',
  SIDEBAR_OPEN: 'left_panel_open',
  MORE_HORIZ: 'more_horiz',
  SEARCH: 'search',
  CONTENT_COPY: 'content_copy',
  PICTURE_AS_PDF: 'picture_as_pdf',
  HOME: 'home',
  DESCRIPTION: 'description',
  ANALYTICS: 'analytics',
  TERMINAL: 'terminal',
} as const

// App Configuration
export const APP_CONFIG = {
  NAME: import.meta.env.VITE_APP_NAME || 'ChatOps AI Backoffice',
  VERSION: import.meta.env.VITE_APP_VERSION || '2.4',
  MAX_MESSAGE_LENGTH: 1000,
  PAGINATION_PAGE_SIZE: 10,
  MAX_ROWS_PER_QUERY: 1000,
} as const

// Colors from design system
export const COLORS = {
  PRIMARY: '#137fec',
  SURFACE: '#ffffff',
  BACKGROUND: '#ffffff',
  BORDER: '#e2e8f0',
  TEXT_MAIN: '#0f172a',
  TEXT_MUTED: '#64748b',
} as const
