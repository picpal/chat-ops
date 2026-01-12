import React, { useState, useMemo } from 'react'
import { TableRenderSpec } from '@/types/renderSpec'
import { QueryResult } from '@/types/queryResult'
import { Card, Badge, Button, Icon } from '@/components/common'
import { usePagination, useModal } from '@/hooks'
import { formatCurrency, formatDate, getJSONPath, downloadCSV, cn } from '@/utils'

interface TableRendererProps {
  spec: TableRenderSpec
  data: QueryResult
}

const TableRenderer: React.FC<TableRendererProps> = ({ spec, data }) => {
  const [sortColumn, setSortColumn] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  const { open: openModal } = useModal()

  // Extract table config with fallback for safety
  const tableConfig = spec.table || { columns: [], dataRef: 'data.rows' }
  const columns = tableConfig.columns || []
  const dataRef = tableConfig.dataRef || 'data.rows'

  // Get rows from data using dataRef (JSONPath)
  const rows = useMemo(() => {
    const extractedData = getJSONPath(data, dataRef) || []
    return Array.isArray(extractedData) ? extractedData : []
  }, [data, dataRef])

  // Pagination
  const {
    hasMore,
    isLoading: isPaginationLoading,
    loadMore,
  } = usePagination(tableConfig.pagination?.queryToken)

  // Sort rows
  const sortedRows = useMemo(() => {
    if (!sortColumn) return rows

    return [...rows].sort((a, b) => {
      const aVal = a[sortColumn]
      const bVal = b[sortColumn]

      if (aVal === bVal) return 0
      if (aVal == null) return 1
      if (bVal == null) return -1

      const comparison = aVal < bVal ? -1 : 1
      return sortDirection === 'asc' ? comparison : -comparison
    })
  }, [rows, sortColumn, sortDirection])

  // Handle column sort
  const handleSort = (key: string) => {
    if (sortColumn === key) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortColumn(key)
      setSortDirection('asc')
    }
  }

  // Format cell value based on column type
  const formatCellValue = (value: any, type: string, _format?: string): React.ReactNode => {
    if (value == null) return '-'

    switch (type) {
      case 'currency':
        return formatCurrency(value)
      case 'date':
        return formatDate(value)
      case 'status':
        return <Badge status={String(value)}>{String(value)}</Badge>
      case 'number':
        return typeof value === 'number' ? value.toLocaleString() : value
      default:
        return String(value)
    }
  }

  // Export CSV
  const handleExport = () => {
    const csvData = sortedRows.map((row) =>
      columns.reduce(
        (acc, col) => ({
          ...acc,
          [col.label]: row[col.key],
        }),
        {}
      )
    )
    downloadCSV(csvData, `${spec.title || 'export'}.csv`)
  }

  // Open fullscreen modal
  const handleFullscreen = () => {
    openModal('tableDetail', { spec, data, rows: sortedRows })
  }

  // Check if action is enabled
  const hasAction = (actionType: string) => {
    return tableConfig.actions?.some((a) => a.action === actionType)
  }

  // Card actions
  const actions = (
    <>
      {hasAction('export-csv') && (
        <Button variant="secondary" size="sm" icon="download" onClick={handleExport}>
          Export CSV
        </Button>
      )}
      {hasAction('refresh') && (
        <button className="p-1.5 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors">
          <Icon name="refresh" size="sm" />
        </button>
      )}
      {hasAction('fullscreen') && (
        <button
          className="p-1.5 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
          onClick={handleFullscreen}
        >
          <Icon name="fullscreen" size="sm" />
        </button>
      )}
    </>
  )

  return (
    <Card
      title={spec.title}
      subtitle={spec.description}
      icon="table_rows"
      actions={actions}
      className="animate-fade-in-up"
    >
      <div className="overflow-x-auto -mx-6 -mb-6">
        <table className="w-full text-left text-sm text-slate-600">
          <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-500 border-b border-slate-200">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    'px-6 py-3 whitespace-nowrap',
                    col.sortable && 'cursor-pointer hover:bg-slate-100',
                    col.align === 'center' && 'text-center',
                    col.align === 'right' && 'text-right'
                  )}
                  style={{ width: col.width }}
                  onClick={() => col.sortable && handleSort(col.key)}
                >
                  <div className={cn(
                    'flex items-center gap-1',
                    col.align === 'center' && 'justify-center',
                    col.align === 'right' && 'justify-end'
                  )}>
                    {col.label}
                    {col.sortable && sortColumn === col.key && (
                      <Icon
                        name={sortDirection === 'asc' ? 'arrow_upward' : 'arrow_downward'}
                        size="sm"
                        className="text-primary"
                      />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sortedRows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length || 1}
                  className="px-6 py-8 text-center text-slate-500"
                >
                  No data available
                </td>
              </tr>
            ) : (
              sortedRows.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-50 transition-colors">
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cn(
                        'px-6 py-3',
                        col.type === 'number' || col.type === 'currency'
                          ? 'text-slate-900 font-medium'
                          : '',
                        col.align === 'center' && 'text-center',
                        col.align === 'right' && 'text-right',
                        col.key.toLowerCase().includes('id') &&
                          'font-mono text-slate-700 text-xs'
                      )}
                    >
                      {formatCellValue(row[col.key], col.type, col.format)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {tableConfig.pagination?.enabled && (hasMore || isPaginationLoading) && (
          <div className="bg-slate-50 px-6 py-3 border-t border-slate-200 flex justify-center">
            <button
              onClick={loadMore}
              disabled={isPaginationLoading}
              className="text-primary text-xs font-semibold hover:underline disabled:opacity-50"
            >
              {isPaginationLoading ? 'Loading...' : 'Load More'}
            </button>
          </div>
        )}

        {/* Footer info */}
        <div className="bg-slate-50 px-6 py-2 border-t border-slate-200 text-xs text-slate-500 flex justify-between">
          <span>{sortedRows.length} rows</span>
          <span>Query: {data.requestId}</span>
        </div>
      </div>
    </Card>
  )
}

export default TableRenderer
