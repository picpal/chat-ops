/**
 * Format a date string to a human-readable format
 */
export const formatDate = (dateString: string, options?: Intl.DateTimeFormatOptions): string => {
  try {
    const date = new Date(dateString)
    const defaultOptions: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      ...options,
    }
    return new Intl.DateTimeFormat('en-US', defaultOptions).format(date)
  } catch (error) {
    return dateString
  }
}

/**
 * Format a date to time ago format (e.g., "2 hours ago")
 */
export const formatTimeAgo = (dateString: string): string => {
  try {
    const date = new Date(dateString)
    const now = new Date()
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

    if (diffInSeconds < 60) return 'Just now'
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
    if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`

    return formatDate(dateString, { month: 'short', day: 'numeric' })
  } catch (error) {
    return dateString
  }
}

/**
 * Format currency (USD)
 */
export const formatCurrency = (amount: number, currency: string = 'USD'): string => {
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount)
  } catch (error) {
    return `$${amount.toFixed(2)}`
  }
}

/**
 * Format number with thousand separators
 */
export const formatNumber = (num: number, decimals: number = 0): string => {
  try {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(num)
  } catch (error) {
    return num.toString()
  }
}

/**
 * Format percentage
 */
export const formatPercentage = (value: number, decimals: number = 1): string => {
  return `${value.toFixed(decimals)}%`
}

/**
 * Truncate text with ellipsis
 */
export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

/**
 * Format execution time in milliseconds to human-readable format
 */
export const formatExecutionTime = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`
  return `${(ms / 60000).toFixed(2)}min`
}

/**
 * Get status badge color class
 */
export const getStatusColor = (
  status: string
): 'emerald' | 'red' | 'amber' | 'slate' | 'blue' => {
  const statusLower = status.toLowerCase()

  if (statusLower.includes('success') || statusLower.includes('paid')) {
    return 'emerald'
  }
  if (statusLower.includes('failed') || statusLower.includes('error')) {
    return 'red'
  }
  if (statusLower.includes('pending') || statusLower.includes('warning')) {
    return 'amber'
  }
  if (statusLower.includes('refund')) {
    return 'slate'
  }

  return 'blue'
}
