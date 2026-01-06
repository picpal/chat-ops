import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  generateId,
  cn,
  copyToClipboard,
  debounce,
  isEmpty,
  sleep,
  getJSONPath,
} from './helpers'

describe('helpers', () => {
  describe('generateId', () => {
    it('generates unique IDs with default prefix', () => {
      const id1 = generateId()
      const id2 = generateId()
      expect(id1).toMatch(/^id-\d+-[a-z0-9]+$/)
      expect(id1).not.toBe(id2)
    })

    it('generates IDs with custom prefix', () => {
      const id = generateId('custom')
      expect(id).toMatch(/^custom-\d+-[a-z0-9]+$/)
    })
  })

  describe('cn', () => {
    it('joins class names', () => {
      expect(cn('class1', 'class2')).toBe('class1 class2')
    })

    it('filters falsy values', () => {
      expect(cn('class1', false, null, undefined, 'class2')).toBe('class1 class2')
    })

    it('handles conditional classes', () => {
      const isActive = true
      const isDisabled = false
      expect(cn('base', isActive && 'active', isDisabled && 'disabled')).toBe('base active')
    })

    it('handles empty input', () => {
      expect(cn()).toBe('')
    })
  })

  describe('copyToClipboard', () => {
    it('copies text to clipboard successfully', async () => {
      const result = await copyToClipboard('test text')
      expect(result).toBe(true)
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('test text')
    })

    it('returns false on error', async () => {
      vi.spyOn(navigator.clipboard, 'writeText').mockRejectedValueOnce(new Error('Failed'))
      const result = await copyToClipboard('test')
      expect(result).toBe(false)
    })
  })

  describe('debounce', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('delays function execution', () => {
      const fn = vi.fn()
      const debouncedFn = debounce(fn, 100)

      debouncedFn('arg1')
      expect(fn).not.toHaveBeenCalled()

      vi.advanceTimersByTime(100)
      expect(fn).toHaveBeenCalledWith('arg1')
    })

    it('only executes once for rapid calls', () => {
      const fn = vi.fn()
      const debouncedFn = debounce(fn, 100)

      debouncedFn('a')
      debouncedFn('b')
      debouncedFn('c')

      vi.advanceTimersByTime(100)
      expect(fn).toHaveBeenCalledTimes(1)
      expect(fn).toHaveBeenCalledWith('c')
    })

    it('resets timer on new call', () => {
      const fn = vi.fn()
      const debouncedFn = debounce(fn, 100)

      debouncedFn('first')
      vi.advanceTimersByTime(50)
      debouncedFn('second')
      vi.advanceTimersByTime(50)
      expect(fn).not.toHaveBeenCalled()
      vi.advanceTimersByTime(50)
      expect(fn).toHaveBeenCalledWith('second')
    })
  })

  describe('isEmpty', () => {
    it('returns true for null and undefined', () => {
      expect(isEmpty(null)).toBe(true)
      expect(isEmpty(undefined)).toBe(true)
    })

    it('returns true for empty string', () => {
      expect(isEmpty('')).toBe(true)
      expect(isEmpty('   ')).toBe(true)
    })

    it('returns true for empty array', () => {
      expect(isEmpty([])).toBe(true)
    })

    it('returns true for empty object', () => {
      expect(isEmpty({})).toBe(true)
    })

    it('returns false for non-empty values', () => {
      expect(isEmpty('text')).toBe(false)
      expect(isEmpty([1])).toBe(false)
      expect(isEmpty({ a: 1 })).toBe(false)
    })

    it('returns false for zero and false', () => {
      expect(isEmpty(0)).toBe(false)
      expect(isEmpty(false)).toBe(false)
    })
  })

  describe('sleep', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('resolves after specified time', async () => {
      const promise = sleep(100)
      vi.advanceTimersByTime(100)
      await expect(promise).resolves.toBeUndefined()
    })
  })

  describe('getJSONPath', () => {
    const testObj = {
      data: {
        rows: [{ id: 1 }, { id: 2 }],
        nested: {
          value: 'deep',
        },
      },
    }

    it('extracts value from simple path', () => {
      expect(getJSONPath(testObj, '$.data.rows')).toEqual([{ id: 1 }, { id: 2 }])
    })

    it('extracts nested value', () => {
      expect(getJSONPath(testObj, '$.data.nested.value')).toBe('deep')
    })

    it('handles path without $. prefix', () => {
      expect(getJSONPath(testObj, 'data.rows')).toEqual([{ id: 1 }, { id: 2 }])
    })

    it('returns undefined for missing path', () => {
      expect(getJSONPath(testObj, '$.missing.path')).toBeUndefined()
    })

    it('returns undefined for null object', () => {
      expect(getJSONPath(null, '$.data')).toBeUndefined()
    })

    it('returns undefined for empty path', () => {
      expect(getJSONPath(testObj, '')).toBeUndefined()
    })

    it('handles $ only path', () => {
      expect(getJSONPath(testObj, '$')).toEqual(testObj)
    })
  })
})
