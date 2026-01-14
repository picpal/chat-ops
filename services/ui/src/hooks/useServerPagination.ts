import { useState, useCallback, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { coreApi } from '@/api'

interface UseServerPaginationOptions {
  queryToken?: string
  totalRows?: number
  pageSize?: number
  initialRows?: Array<Record<string, any>>
}

interface ServerPaginationResult {
  rows: Array<Record<string, any>>
  currentPage: number
  totalPages: number
  totalRows: number
  pageSize: number
  isLoading: boolean
  error: Error | null
  goToPage: (page: number) => void
  hasNextPage: boolean
  hasPrevPage: boolean
}

export const useServerPagination = ({
  queryToken,
  totalRows = 0,
  pageSize = 10,
  initialRows = [],
}: UseServerPaginationOptions): ServerPaginationResult => {
  const [currentPage, setCurrentPage] = useState(1)
  const [rows, setRows] = useState<Array<Record<string, any>>>(initialRows)
  const [isNavigating, setIsNavigating] = useState(false)

  const totalPages = totalRows > 0 ? Math.ceil(totalRows / pageSize) : 1

  // Query for fetching page data
  const {
    data,
    isLoading: isQueryLoading,
    error,
  } = useQuery({
    queryKey: ['serverPagination', queryToken, currentPage],
    queryFn: () => coreApi.goToPage(queryToken!, currentPage),
    enabled: !!queryToken && isNavigating && currentPage > 1,
    staleTime: 0,
  })

  // Update rows when data is fetched
  useEffect(() => {
    if (data?.data?.rows) {
      setRows(data.data.rows)
      setIsNavigating(false)
    }
  }, [data])

  // Reset to initial rows when going back to page 1
  useEffect(() => {
    if (currentPage === 1 && !isNavigating) {
      setRows(initialRows)
    }
  }, [currentPage, initialRows, isNavigating])

  const goToPage = useCallback(
    (page: number) => {
      if (page < 1 || page > totalPages) return
      if (page === currentPage) return

      setCurrentPage(page)

      if (page === 1) {
        // Use initial data for first page
        setRows(initialRows)
        setIsNavigating(false)
      } else {
        // Fetch from server for other pages
        setIsNavigating(true)
      }
    },
    [totalPages, currentPage, initialRows]
  )

  return {
    rows,
    currentPage,
    totalPages,
    totalRows,
    pageSize,
    isLoading: isQueryLoading && isNavigating,
    error: error as Error | null,
    goToPage,
    hasNextPage: currentPage < totalPages,
    hasPrevPage: currentPage > 1,
  }
}
