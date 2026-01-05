import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { coreApi } from '@/api'

export const usePagination = (initialQueryToken?: string) => {
  const [queryToken, setQueryToken] = useState<string | undefined>(
    initialQueryToken
  )
  const [accumulatedData, setAccumulatedData] = useState<
    Array<Record<string, any>>
  >([])

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['pagination', queryToken],
    queryFn: () => coreApi.getPage(queryToken!),
    enabled: !!queryToken,
  })

  // Accumulate data when new page is fetched
  if (data?.data.rows && data.data.rows.length > 0) {
    const newRows = data.data.rows
    const existingIds = new Set(accumulatedData.map((row) => row.id || row))

    // Only add rows that don't already exist
    const uniqueNewRows = newRows.filter(
      (row) => !existingIds.has(row.id || row)
    )

    if (uniqueNewRows.length > 0) {
      setAccumulatedData((prev) => [...prev, ...uniqueNewRows])
    }
  }

  const loadMore = () => {
    if (data?.metadata.queryToken && data.metadata.hasMore) {
      setQueryToken(data.metadata.queryToken)
    }
  }

  const reset = () => {
    setAccumulatedData([])
    setQueryToken(initialQueryToken)
  }

  return {
    data: accumulatedData,
    hasMore: data?.metadata.hasMore ?? false,
    isLoading,
    error,
    loadMore,
    reset,
    refetch,
  }
}
