import React, { useState, useMemo } from 'react'
import { LogRenderSpec } from '@/types/renderSpec'
import { QueryResult } from '@/types/queryResult'
import { Card, Icon } from '@/components/common'
import { useModal } from '@/hooks'
import { getJSONPath, formatDate, cn, copyToClipboard } from '@/utils'

interface LogRendererProps {
  spec: LogRenderSpec
  data: QueryResult
}

type LogLevel = 'info' | 'warn' | 'error' | 'debug'

const LogRenderer: React.FC<LogRendererProps> = ({ spec, data }) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [levelFilter, setLevelFilter] = useState<LogLevel | 'all'>('all')
  const [showLineNumbers, setShowLineNumbers] = useState(true)
  const { open: openModal } = useModal()

  // Get log entries from data using dataRef
  const logs = useMemo(() => {
    const extracted = getJSONPath(data, spec.dataRef) || []
    return Array.isArray(extracted) ? extracted : []
  }, [data, spec.dataRef])

  // Filter logs
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      // Level filter
      if (levelFilter !== 'all' && log.level !== levelFilter) {
        return false
      }
      // Search filter
      if (searchTerm) {
        const term = searchTerm.toLowerCase()
        return (
          log.message?.toLowerCase().includes(term) ||
          log.level?.toLowerCase().includes(term) ||
          JSON.stringify(log.metadata || {}).toLowerCase().includes(term)
        )
      }
      return true
    })
  }, [logs, levelFilter, searchTerm])

  // Get level styles
  const getLevelStyle = (level: string) => {
    switch (level.toLowerCase()) {
      case 'error':
        return 'text-red-400'
      case 'warn':
      case 'warning':
        return 'text-amber-400'
      case 'info':
        return 'text-emerald-400'
      case 'debug':
        return 'text-blue-400'
      default:
        return 'text-slate-400'
    }
  }

  // Highlight search term in text
  const highlightText = (text: string) => {
    if (!searchTerm) return text

    const regex = new RegExp(`(${searchTerm})`, 'gi')
    const parts = text.split(regex)

    return parts.map((part, i) =>
      regex.test(part) ? (
        <mark key={i} className="bg-yellow-300 text-slate-900 px-0.5 rounded">
          {part}
        </mark>
      ) : (
        part
      )
    )
  }

  const handleCopyLine = async (log: any) => {
    const text = `[${log.timestamp}] [${log.level.toUpperCase()}] ${log.message}`
    await copyToClipboard(text)
  }

  const handleFullscreen = () => {
    openModal('logDetail', { spec, data, logs: filteredLogs })
  }

  const actions = (
    <>
      <button
        className="p-1.5 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
        onClick={handleFullscreen}
      >
        <Icon name="fullscreen" size="sm" />
      </button>
    </>
  )

  return (
    <Card
      title={spec.title || 'Log Entries'}
      subtitle={spec.description || `${filteredLogs.length} entries`}
      icon="terminal"
      actions={actions}
      className="animate-fade-in-up"
    >
      {/* Controls */}
      <div className="flex flex-wrap gap-4 mb-4">
        {/* Search */}
        {spec.searchable && (
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Icon
                name="search"
                size="sm"
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search logs..."
                className="w-full pl-10 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>
        )}

        {/* Level Filter */}
        {spec.filterByLevel && (
          <div className="flex items-center gap-2">
            {(['all', 'error', 'warn', 'info', 'debug'] as const).map((level) => (
              <button
                key={level}
                onClick={() => setLevelFilter(level)}
                className={cn(
                  'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                  levelFilter === level
                    ? 'bg-primary text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                )}
              >
                {level.toUpperCase()}
              </button>
            ))}
          </div>
        )}

        {/* Line Numbers Toggle */}
        <button
          onClick={() => setShowLineNumbers(!showLineNumbers)}
          className={cn(
            'flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
            showLineNumbers
              ? 'bg-slate-200 text-slate-700'
              : 'bg-slate-100 text-slate-500'
          )}
        >
          <Icon name="format_list_numbered" size="sm" />
          Line #
        </button>
      </div>

      {/* Log Content */}
      <div className="bg-slate-900 rounded-lg overflow-hidden -mx-6 -mb-6">
        <div className="max-h-[400px] overflow-y-auto p-4 font-mono text-sm">
          {filteredLogs.length === 0 ? (
            <div className="text-slate-500 text-center py-8">No log entries found</div>
          ) : (
            filteredLogs.map((log, idx) => (
              <div
                key={idx}
                className={cn(
                  'flex items-start gap-3 py-1.5 px-2 hover:bg-slate-800/50 rounded group',
                  log.level === 'error' && 'border-l-2 border-red-500 pl-3'
                )}
              >
                {/* Line Number */}
                {showLineNumbers && (
                  <span className="text-slate-600 select-none w-8 text-right shrink-0">
                    {idx + 1}
                  </span>
                )}

                {/* Timestamp */}
                <span className="text-slate-500 shrink-0">
                  {formatDate(log.timestamp, {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                  })}
                </span>

                {/* Level */}
                <span className={cn('w-12 shrink-0 font-bold', getLevelStyle(log.level))}>
                  [{log.level.toUpperCase().slice(0, 4)}]
                </span>

                {/* Message */}
                <span className="text-slate-300 flex-1 break-all">
                  {highlightText(log.message)}
                </span>

                {/* Copy Button */}
                <button
                  onClick={() => handleCopyLine(log)}
                  className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-slate-300 transition-opacity"
                >
                  <Icon name="content_copy" size="sm" />
                </button>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="bg-slate-800 px-4 py-2 flex justify-between items-center text-xs text-slate-500 border-t border-slate-700">
          <span>{filteredLogs.length} lines</span>
          <span>UTF-8</span>
        </div>
      </div>
    </Card>
  )
}

export default LogRenderer
