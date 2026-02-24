import React, { useState, useMemo, useEffect } from 'react'
import { useModal, useServerPagination } from '@/hooks'
import { Icon, Badge } from '@/components/common'
import { formatCurrency, formatDate, formatNumber, cn } from '@/utils'
import { TableRenderSpec, TableColumn } from '@/types/renderSpec'

const ROWS_PER_PAGE = 10
// Stable empty array reference to prevent infinite loops
const EMPTY_ROWS: any[] = []

interface ServerPaginationInfo {
  queryToken?: string
  totalRows?: number
  totalPages?: number
  pageSize?: number
  hasMore?: boolean
}

const TableDetailModal: React.FC = () => {
  const { isOpen, type, data, close } = useModal()
  const [clientPage, setClientPage] = useState(1)
  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  // Extract modal data
  const modalData = data as {
    spec: TableRenderSpec
    rows: any[]
    serverPagination?: ServerPaginationInfo
  } | undefined

  const spec = modalData?.spec
  // Use stable empty array reference to prevent infinite loops in useServerPagination
  const initialRows = modalData?.rows || EMPTY_ROWS
  const serverPagination = modalData?.serverPagination

  // Extract table config with fallback
  const tableConfig = spec?.table || { columns: [], dataRef: 'data.rows' }
  const columns = tableConfig.columns || []

  // Determine if we should use server-side pagination
  // CHANGED: Disable server-side pagination in detail modal
  // The detail modal should show only the requested data (e.g., "30건 보여줘" → only 30 rows)
  // NOT the entire database. Server pagination would show all 1000 rows.
  const useServerSide = false

  // Server pagination hook
  const serverPaginationHook = useServerPagination({
    queryToken: serverPagination?.queryToken,
    totalRows: serverPagination?.totalRows || 0,
    pageSize: serverPagination?.pageSize || ROWS_PER_PAGE,
    initialRows: initialRows,
  })

  // Client-side pagination (fallback)
  const clientTotalPages = Math.ceil(initialRows.length / ROWS_PER_PAGE)
  const clientPaginatedRows = useMemo(() => {
    const start = (clientPage - 1) * ROWS_PER_PAGE
    return initialRows.slice(start, start + ROWS_PER_PAGE)
  }, [initialRows, clientPage])

  // Choose which pagination to use
  const currentPage = useServerSide ? serverPaginationHook.currentPage : clientPage
  const totalPages = useServerSide ? serverPaginationHook.totalPages : clientTotalPages
  const totalRows = useServerSide ? serverPaginationHook.totalRows : initialRows.length
  const displayRows = useServerSide ? serverPaginationHook.rows : clientPaginatedRows
  const isLoading = useServerSide ? serverPaginationHook.isLoading : false

  const goToPage = (page: number) => {
    if (useServerSide) {
      serverPaginationHook.goToPage(page)
    } else {
      setClientPage(page)
    }
  }

  // Download handler
  const handleDownload = async (format: 'csv' | 'excel') => {
    console.log('[TableDetailModal] handleDownload called', {
      hasSpec: !!spec,
      hasMetadata: !!spec?.metadata,
      metadata: spec?.metadata,
      sql: spec?.metadata?.sql
    })
    const sql = spec?.metadata?.sql
    if (!sql) {
      setDownloadError('SQL 정보가 없어 다운로드할 수 없습니다.')
      return
    }

    setIsDownloading(true)
    setDownloadError(null)

    try {
      const response = await fetch('/api/v1/chat/download', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ sql, format }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `다운로드 실패: ${response.status}`)
      }

      // Blob으로 변환
      const blob = await response.blob()

      // 파일명 추출 (Content-Disposition 헤더에서)
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `query_result.${format === 'csv' ? 'csv' : 'xlsx'}`
      if (contentDisposition) {
        const match = contentDisposition.match(/filename[^;=\n]*=(['"]?)([^'"\n;]*)\1/)
        if (match && match[2]) {
          filename = match[2]
        }
      }

      // 다운로드 트리거
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

    } catch (error) {
      console.error('Download failed:', error)
      setDownloadError(error instanceof Error ? error.message : '다운로드 실패')
    } finally {
      setIsDownloading(false)
    }
  }

  // Reset page when modal opens
  useEffect(() => {
    if (isOpen && type === 'tableDetail') {
      setClientPage(1)
      // Note: useServerSide is always false, so this branch never executes
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }
  }, [isOpen, type])

  // ESC key handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    if (isOpen && type === 'tableDetail') {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [isOpen, type, close])

  if (!isOpen || type !== 'tableDetail' || !spec) return null

  // Format cell value
  const formatCellValue = (value: any, column: TableColumn): React.ReactNode => {
    if (value == null) return '-'

    switch (column.type) {
      case 'currency':
        return formatCurrency(value)
      case 'date':
        return formatDate(value)
      case 'status':
        return <Badge status={String(value)}>{String(value)}</Badge>
      case 'number': {
        const numValue = typeof value === 'string' ? parseFloat(value) : value
        if (typeof numValue === 'number' && Number.isFinite(numValue)) {
          return Number.isInteger(numValue) ? formatNumber(numValue, 0) : formatNumber(numValue, 2)
        }
        return value
      }
      default:
        return String(value)
    }
  }

  // Generate page numbers
  const getPageNumbers = () => {
    const pages: (number | string)[] = []
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pages.push(i)
    } else {
      if (currentPage <= 3) {
        pages.push(1, 2, 3, '...', totalPages)
      } else if (currentPage >= totalPages - 2) {
        pages.push(1, '...', totalPages - 2, totalPages - 1, totalPages)
      } else {
        pages.push(1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages)
      }
    }
    return pages
  }

  // Calculate display range
  const startRow = (currentPage - 1) * ROWS_PER_PAGE + 1
  const endRow = Math.min(currentPage * ROWS_PER_PAGE, totalRows)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
        onClick={close}
      />

      {/* Modal */}
      <div className="relative w-full h-full bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-fade-in-up border border-slate-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-white shrink-0 z-20">
          <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <Icon name="aspect_ratio" className="text-primary" />
            {spec.title || 'Maximized Data View'}
          </h2>
          <div className="flex items-center gap-3">
            {/* Download Button */}
            <div className="relative group">
              <button
                className={cn(
                  "p-2 text-slate-500 hover:text-primary hover:bg-slate-50 rounded-lg transition-colors border border-slate-200 shadow-sm flex items-center gap-2 bg-slate-50/50",
                  (!spec?.metadata?.sql || isDownloading) && "opacity-50 cursor-not-allowed"
                )}
                disabled={!spec?.metadata?.sql || isDownloading}
              >
                <Icon name="download" size="sm" />
                <span className="text-sm font-medium hidden sm:block">
                  {isDownloading ? '다운로드 중...' : 'Download'}
                </span>
              </button>
              {/* Dropdown (shown on hover) */}
              <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-xl shadow-xl border border-slate-100 py-2 z-50 ring-1 ring-black/5 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
                <div className="px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Export Options
                </div>
                {!spec?.metadata?.sql ? (
                  <div className="px-4 py-2 text-sm text-slate-400">
                    SQL 정보가 없어 다운로드할 수 없습니다
                  </div>
                ) : (
                  <>
                    <button
                      onClick={() => handleDownload('excel')}
                      disabled={isDownloading}
                      className="w-full flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 hover:text-primary transition-colors disabled:opacity-50"
                    >
                      <Icon name="table_view" className="text-emerald-600" />
                      Download as Excel
                    </button>
                    <button
                      onClick={() => handleDownload('csv')}
                      disabled={isDownloading}
                      className="w-full flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 hover:text-primary transition-colors disabled:opacity-50"
                    >
                      <Icon name="description" className="text-blue-500" />
                      Download as CSV
                    </button>
                  </>
                )}
              </div>
            </div>

            <div className="h-6 w-px bg-slate-200" />

            {/* Close Button */}
            <button
              onClick={close}
              className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
            >
              <Icon name="close" size="sm" />
            </button>
          </div>
        </div>

        {/* Download Error Message */}
        {downloadError && (
          <div className="px-6 py-3 bg-red-50 border-b border-red-200 flex items-center gap-2 shrink-0">
            <Icon name="error" className="text-red-500" size="sm" />
            <span className="text-red-700 text-sm">{downloadError}</span>
            <button
              onClick={() => setDownloadError(null)}
              className="ml-auto p-1 text-red-400 hover:text-red-600"
            >
              <Icon name="close" size="sm" />
            </button>
          </div>
        )}

        {/* Table Content */}
        <div className="flex-1 overflow-auto bg-slate-50/30 p-0 relative">
          {/* Loading Overlay */}
          {isLoading && (
            <div className="absolute inset-0 bg-white/70 flex items-center justify-center z-20">
              <div className="flex items-center gap-2 text-slate-600">
                <Icon name="hourglass_empty" className="animate-spin" />
                <span>Loading page {currentPage}...</span>
              </div>
            </div>
          )}

          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50 text-xs uppercase font-bold text-slate-500 border-b border-slate-200 sticky top-0 z-10 shadow-sm">
              <tr>
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className={cn(
                      'px-8 py-4 whitespace-nowrap bg-slate-50',
                      col.type === 'currency' || col.type === 'number' ? 'text-right' : '',
                      col.align === 'center' && 'text-center',
                      col.align === 'right' && 'text-right',
                      col.type === 'status' ? 'text-center' : ''
                    )}
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {displayRows.length === 0 ? (
                <tr>
                  <td
                    colSpan={columns.length || 1}
                    className="px-8 py-12 text-center text-slate-500"
                  >
                    No data available
                  </td>
                </tr>
              ) : (
                displayRows.map((row, idx) => (
                  <tr
                    key={idx}
                    className="hover:bg-blue-50/30 transition-colors group"
                  >
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className={cn(
                          'px-8 py-4',
                          col.type === 'currency' || col.type === 'number'
                            ? 'text-slate-900 font-bold text-right'
                            : '',
                          col.align === 'center' && 'text-center',
                          col.align === 'right' && 'text-right',
                          col.type === 'status' ? 'text-center' : '',
                          col.key.toLowerCase().includes('id') &&
                            'font-mono text-slate-700 text-xs'
                        )}
                      >
                        {formatCellValue(row[col.key], col)}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Footer with Pagination */}
        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
          <p className="text-sm text-slate-500">
            Showing{' '}
            <span className="font-medium text-slate-900">
              {startRow}
            </span>{' '}
            to{' '}
            <span className="font-medium text-slate-900">
              {endRow}
            </span>{' '}
            of{' '}
            <span className="font-medium text-slate-900">{totalRows.toLocaleString()}</span>{' '}
            results
            {useServerSide && (
              <span className="ml-2 text-xs text-blue-500">(Server-side)</span>
            )}
          </p>

          {totalPages > 1 && (
            <nav className="flex items-center gap-1">
              {/* Previous Button */}
              <button
                onClick={() => goToPage(currentPage - 1)}
                disabled={currentPage === 1 || isLoading}
                className="p-2 rounded-lg border border-slate-200 bg-white text-slate-400 hover:text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Icon name="chevron_left" size="sm" />
              </button>

              {/* Page Numbers */}
              {getPageNumbers().map((page, idx) =>
                page === '...' ? (
                  <span key={`ellipsis-${idx}`} className="px-2 text-slate-400">
                    ...
                  </span>
                ) : (
                  <button
                    key={page}
                    onClick={() => goToPage(page as number)}
                    disabled={isLoading}
                    className={cn(
                      'px-3.5 py-2 rounded-lg text-sm font-medium transition-colors',
                      currentPage === page
                        ? 'bg-primary text-white'
                        : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50',
                      isLoading && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    {page}
                  </button>
                )
              )}

              {/* Next Button */}
              <button
                onClick={() => goToPage(currentPage + 1)}
                disabled={currentPage === totalPages || isLoading}
                className="p-2 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Icon name="chevron_right" size="sm" />
              </button>
            </nav>
          )}
        </div>
      </div>
    </div>
  )
}

export default TableDetailModal
