import React, { useState, useMemo } from 'react'
import { useModal } from '@/hooks'
import { Icon } from '@/components/common'
import { LogRenderSpec } from '@/types/renderSpec'
import { formatDate, cn, copyToClipboard } from '@/utils'

type LogLevel = 'info' | 'warn' | 'error' | 'debug' | 'all'

interface LogEntry {
  timestamp: string
  level: string
  message: string
  metadata?: Record<string, any>
}

interface LogModalData {
  spec: LogRenderSpec
  logs: LogEntry[]
}

const LogDetailModal: React.FC = () => {
  const { isOpen, type, data, close } = useModal()

  // State
  const [searchTerm, setSearchTerm] = useState('')
  const [levelFilter, setLevelFilter] = useState<LogLevel>('all')
  const [showLineNumbers, setShowLineNumbers] = useState(true)
  const [wrapLines, setWrapLines] = useState(true)
  const [showTimestamp, setShowTimestamp] = useState(false)

  // Extract modal data
  const modalData = data as LogModalData | undefined
  const spec = modalData?.spec
  const logs = modalData?.logs || []

  // ESC key handler
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
      if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault()
        document.getElementById('log-search-input')?.focus()
      }
    }
    if (isOpen && type === 'logDetail') {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [isOpen, type, close])

  // Filter logs
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      // Level filter
      if (levelFilter !== 'all' && log.level?.toLowerCase() !== levelFilter) {
        return false
      }
      // Search filter
      if (searchTerm) {
        const term = searchTerm.toLowerCase()
        return (
          log.message?.toLowerCase().includes(term) ||
          log.level?.toLowerCase().includes(term)
        )
      }
      return true
    })
  }, [logs, levelFilter, searchTerm])

  // Get level styles
  const getLevelStyle = (level: string) => {
    switch (level?.toLowerCase()) {
      case 'error':
        return 'text-red-400 font-bold'
      case 'warn':
      case 'warning':
        return 'text-amber-400 font-bold'
      case 'info':
        return 'text-emerald-400 font-bold'
      case 'debug':
        return 'text-blue-400 font-bold'
      default:
        return 'text-slate-400'
    }
  }

  const getRowStyle = (level: string) => {
    if (level?.toLowerCase() === 'error') {
      return 'hover:bg-red-500/10 bg-red-500/5 border-l-2 border-red-500'
    }
    return 'hover:bg-white/5'
  }

  // Copy all logs
  const handleCopyAll = async () => {
    const text = filteredLogs
      .map((log) => `[${log.timestamp}] [${log.level?.toUpperCase()}] ${log.message}`)
      .join('\n')
    await copyToClipboard(text)
  }

  // Copy single line
  const handleCopyLine = async (log: LogEntry) => {
    const text = `[${log.timestamp}] [${log.level?.toUpperCase()}] ${log.message}`
    await copyToClipboard(text)
  }

  // Highlight search term
  const highlightText = (text: string): React.ReactNode => {
    if (!searchTerm || !text) return text

    try {
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
    } catch {
      return text
    }
  }

  if (!isOpen || type !== 'logDetail' || !spec) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 md:p-6">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
        onClick={close}
      />

      {/* Modal */}
      <div className="relative w-full h-full max-w-[95%] xl:max-w-7xl bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden animate-fade-in-up ring-1 ring-black/5">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-white shrink-0">
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-100">
              <Icon name="terminal" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-800 tracking-tight">
                Maximized Log View
              </h2>
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600 border border-slate-200">
                  {spec.title || 'log.txt'}
                </span>
                <span>•</span>
                <span>Last updated: {formatDate(new Date().toISOString())}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Search Bar */}
            <div className="hidden lg:flex items-center px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary">
              <Icon name="search" size="sm" className="text-slate-400" />
              <input
                id="log-search-input"
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-transparent border-none p-0 text-sm focus:ring-0 w-64 placeholder-slate-400 ml-2 text-slate-700"
                placeholder="Search logs (Regex supported)"
              />
              <kbd className="hidden xl:inline-block ml-4 px-1.5 py-0.5 text-[10px] font-bold text-slate-400 bg-white border border-slate-200 rounded shadow-sm">
                CTRL+F
              </kbd>
            </div>

            <div className="h-6 w-px bg-slate-200 mx-1" />

            {/* Copy All Button */}
            <button
              onClick={handleCopyAll}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 bg-white hover:bg-slate-50 hover:text-slate-900 rounded-lg border border-slate-200 transition-all shadow-sm"
            >
              <Icon name="content_copy" size="sm" />
              <span>Copy All</span>
            </button>

            {/* Close Button */}
            <button
              onClick={close}
              className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <Icon name="close" />
            </button>
          </div>
        </div>

        {/* Controls */}
        <div className="px-6 py-2 bg-slate-50/80 backdrop-blur border-b border-slate-200 flex flex-wrap items-center justify-between gap-4 shrink-0 z-10">
          {/* Toggles */}
          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2 text-xs font-semibold text-slate-600 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={showLineNumbers}
                onChange={(e) => setShowLineNumbers(e.target.checked)}
                className="w-4 h-4 rounded border-slate-300 text-primary focus:ring-primary/20"
              />
              <span>Line Numbers</span>
            </label>
            <label className="flex items-center gap-2 text-xs font-semibold text-slate-600 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={wrapLines}
                onChange={(e) => setWrapLines(e.target.checked)}
                className="w-4 h-4 rounded border-slate-300 text-primary focus:ring-primary/20"
              />
              <span>Wrap Lines</span>
            </label>
            <label className="flex items-center gap-2 text-xs font-semibold text-slate-600 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={showTimestamp}
                onChange={(e) => setShowTimestamp(e.target.checked)}
                className="w-4 h-4 rounded border-slate-300 text-primary focus:ring-primary/20"
              />
              <span>Show Timestamp</span>
            </label>
          </div>

          {/* Level Filters */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-medium mr-1">Filter Level:</span>
            {(['all', 'error', 'warn', 'info', 'debug'] as LogLevel[]).map((level) => (
              <button
                key={level}
                onClick={() => setLevelFilter(level)}
                className={cn(
                  'px-2.5 py-1 rounded text-[10px] font-bold border transition-colors',
                  levelFilter === level
                    ? 'bg-white border-slate-200 text-slate-600 shadow-sm'
                    : level === 'error'
                      ? 'bg-white border-slate-200 text-slate-400 hover:text-red-600 hover:border-red-200 hover:bg-red-50'
                      : level === 'warn'
                        ? 'bg-white border-slate-200 text-slate-400 hover:text-amber-600 hover:border-amber-200 hover:bg-amber-50'
                        : level === 'info'
                          ? 'bg-white border-slate-200 text-slate-400 hover:text-emerald-600 hover:border-emerald-200 hover:bg-emerald-50'
                          : level === 'debug'
                            ? 'bg-white border-slate-200 text-slate-400 hover:text-blue-600 hover:border-blue-200 hover:bg-blue-50'
                            : 'bg-white border-slate-200 text-slate-400 hover:text-slate-600 hover:border-slate-300'
                )}
              >
                {level.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Log Content */}
        <div className="flex-1 overflow-auto bg-[#1e293b] text-slate-300 font-mono text-[13px] leading-6 relative custom-scrollbar">
          <div className="min-w-full inline-block align-top">
            {filteredLogs.length === 0 ? (
              <div className="flex items-center justify-center h-64 text-slate-500">
                No log entries found
              </div>
            ) : (
              filteredLogs.map((log, idx) => (
                <div
                  key={idx}
                  className={cn(
                    'flex group transition-colors duration-75',
                    getRowStyle(log.level)
                  )}
                >
                  {/* Line Number */}
                  {showLineNumbers && (
                    <div className="sticky left-0 w-12 shrink-0 bg-[#1e293b] border-r border-slate-700/50 text-slate-500 text-right pr-3 select-none group-hover:text-slate-300">
                      {idx + 1}
                    </div>
                  )}

                  {/* Log Content */}
                  <div
                    className={cn(
                      'pl-4 pr-12 flex-1',
                      wrapLines ? 'whitespace-pre-wrap break-all' : 'whitespace-nowrap'
                    )}
                  >
                    {/* Timestamp */}
                    {showTimestamp && log.timestamp && (
                      <span className="text-slate-500 mr-2">
                        {formatDate(log.timestamp, {
                          year: 'numeric',
                          month: '2-digit',
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                        })}
                      </span>
                    )}

                    {/* Level */}
                    <span className={cn('mr-2', getLevelStyle(log.level))}>
                      [{log.level?.toUpperCase()}]
                    </span>

                    {/* Message */}
                    <span className={log.level?.toLowerCase() === 'error' ? 'text-red-200' : ''}>
                      {highlightText(log.message)}
                    </span>
                  </div>

                  {/* Copy Button */}
                  <button
                    onClick={() => handleCopyLine(log)}
                    className="opacity-0 group-hover:opacity-100 absolute right-4 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-white transition-opacity bg-[#1e293b]/50 rounded"
                  >
                    <Icon name="content_copy" size="sm" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-white border-t border-slate-200 flex items-center justify-between shrink-0 text-xs">
          <div className="flex items-center gap-4 text-slate-500">
            <span>
              Lines 1-{filteredLogs.length} of {filteredLogs.length} displayed
            </span>
            <span className="w-px h-3 bg-slate-300" />
            <span>Size: ~{Math.round(JSON.stringify(filteredLogs).length / 1024)}KB</span>
            <span className="w-px h-3 bg-slate-300" />
            <span>Encoding: UTF-8</span>
          </div>
          <div className="flex gap-2">
            <button className="text-primary hover:text-blue-700 font-medium">
              Download Full Log
            </button>
          </div>
        </div>
      </div>

      {/* Custom scrollbar styles */}
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #0f172a;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #334155;
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #475569;
        }
      `}</style>
    </div>
  )
}

export default LogDetailModal
