import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  formatDate,
  formatTimeAgo,
  formatCurrency,
  formatNumber,
  formatPercentage,
  truncateText,
  formatExecutionTime,
  getStatusColor,
} from './formatters'

describe('formatters', () => {
  describe('formatDate', () => {
    it('formats ISO date string correctly', () => {
      const result = formatDate('2024-10-24T10:42:00Z')
      expect(result).toContain('Oct')
      expect(result).toContain('24')
      expect(result).toContain('2024')
    })

    it('returns original string for invalid date', () => {
      const result = formatDate('invalid-date')
      expect(result).toBe('invalid-date')
    })

    it('applies custom options', () => {
      const result = formatDate('2024-10-24T10:42:00Z', {
        month: 'long',
        day: '2-digit',
      })
      expect(result).toContain('October')
    })
  })

  describe('formatTimeAgo', () => {
    beforeEach(() => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date('2024-10-24T12:00:00Z'))
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('returns "Just now" for recent timestamps', () => {
      const result = formatTimeAgo('2024-10-24T11:59:30Z')
      expect(result).toBe('Just now')
    })

    it('returns minutes ago for timestamps within hour', () => {
      const result = formatTimeAgo('2024-10-24T11:30:00Z')
      expect(result).toBe('30m ago')
    })

    it('returns hours ago for timestamps within day', () => {
      const result = formatTimeAgo('2024-10-24T09:00:00Z')
      expect(result).toBe('3h ago')
    })

    it('returns days ago for timestamps within week', () => {
      const result = formatTimeAgo('2024-10-22T12:00:00Z')
      expect(result).toBe('2d ago')
    })

    it('returns formatted date for older timestamps', () => {
      const result = formatTimeAgo('2024-10-01T12:00:00Z')
      expect(result).toContain('Oct')
    })
  })

  describe('formatCurrency', () => {
    it('formats USD correctly', () => {
      const result = formatCurrency(1234.56)
      expect(result).toBe('$1,234.56')
    })

    it('formats with different currency', () => {
      const result = formatCurrency(1000, 'EUR')
      expect(result).toContain('1,000.00')
    })

    it('handles zero', () => {
      const result = formatCurrency(0)
      expect(result).toBe('$0.00')
    })

    it('handles negative numbers', () => {
      const result = formatCurrency(-500)
      expect(result).toContain('500.00')
    })
  })

  describe('formatNumber', () => {
    it('formats with thousand separators', () => {
      expect(formatNumber(1234567)).toBe('1,234,567')
    })

    it('formats with specified decimals', () => {
      expect(formatNumber(1234.5678, 2)).toBe('1,234.57')
    })

    it('handles zero', () => {
      expect(formatNumber(0)).toBe('0')
    })
  })

  describe('formatPercentage', () => {
    it('formats with default decimals', () => {
      expect(formatPercentage(85.456)).toBe('85.5%')
    })

    it('formats with specified decimals', () => {
      expect(formatPercentage(85.456, 2)).toBe('85.46%')
    })

    it('handles zero', () => {
      expect(formatPercentage(0)).toBe('0.0%')
    })
  })

  describe('truncateText', () => {
    it('returns original text if within limit', () => {
      expect(truncateText('short', 10)).toBe('short')
    })

    it('truncates and adds ellipsis', () => {
      expect(truncateText('this is a long text', 10)).toBe('this is a ...')
    })

    it('handles exact length', () => {
      expect(truncateText('exact', 5)).toBe('exact')
    })
  })

  describe('formatExecutionTime', () => {
    it('formats milliseconds', () => {
      expect(formatExecutionTime(500)).toBe('500ms')
    })

    it('formats seconds', () => {
      expect(formatExecutionTime(5000)).toBe('5.00s')
    })

    it('formats minutes', () => {
      expect(formatExecutionTime(120000)).toBe('2.00min')
    })

    it('formats edge case at 1 second', () => {
      expect(formatExecutionTime(1000)).toBe('1.00s')
    })
  })

  describe('getStatusColor', () => {
    it('returns emerald for success statuses', () => {
      expect(getStatusColor('success')).toBe('emerald')
      expect(getStatusColor('Success')).toBe('emerald')
      expect(getStatusColor('Paid')).toBe('emerald')
    })

    it('returns red for error statuses', () => {
      expect(getStatusColor('failed')).toBe('red')
      expect(getStatusColor('Failed')).toBe('red')
      expect(getStatusColor('Error')).toBe('red')
    })

    it('returns amber for pending statuses', () => {
      expect(getStatusColor('pending')).toBe('amber')
      expect(getStatusColor('Pending')).toBe('amber')
      expect(getStatusColor('Warning')).toBe('amber')
    })

    it('returns slate for refund statuses', () => {
      expect(getStatusColor('refunded')).toBe('slate')
      expect(getStatusColor('Refund')).toBe('slate')
    })

    it('returns blue for unknown statuses', () => {
      expect(getStatusColor('unknown')).toBe('blue')
      expect(getStatusColor('processing')).toBe('blue')
    })
  })
})
