import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { LogAnalysisRenderSpec } from '@/types/renderSpec'
import { Card, Icon } from '@/components/common'
import { cn, formatDate } from '@/utils'

interface LogAnalysisRendererProps {
  spec: LogAnalysisRenderSpec
}

type TabType = 'summary' | 'logs'

const LogAnalysisRenderer: React.FC<LogAnalysisRendererProps> = ({ spec }) => {
  const [activeTab, setActiveTab] = useState<TabType>('summary')

  const { summary, statistics, entries } = spec.log_analysis

  // Get level styles (same as LogRenderer)
  const getLevelStyle = (level: string | null) => {
    if (!level) return 'text-slate-400'
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

  // Statistics cards data
  const statsCards = [
    {
      label: '전체 로그',
      value: statistics.totalEntries,
      icon: 'description',
      color: 'text-blue-500',
    },
    {
      label: '에러',
      value: statistics.errorCount,
      icon: 'error',
      color: 'text-red-500',
    },
    {
      label: '경고',
      value: statistics.warnCount,
      icon: 'warning',
      color: 'text-amber-500',
    },
    {
      label: '시간 범위',
      value: statistics.timeRange || '-',
      icon: 'schedule',
      color: 'text-slate-500',
      isText: true,
    },
  ]

  return (
    <Card
      title={spec.title || '서버 로그 분석 결과'}
      subtitle={spec.description}
      icon="analytics"
      className="animate-fade-in-up"
    >
      {/* Statistics Cards */}
      <div className="flex flex-wrap gap-4 mb-6">
        {statsCards.map((stat, idx) => (
          <div
            key={idx}
            className="flex items-center gap-3 px-4 py-3 bg-slate-50 rounded-lg border border-slate-100 min-w-[140px]"
          >
            <Icon name={stat.icon} className={stat.color} size="md" />
            <div>
              <div className="text-xs text-slate-500">{stat.label}</div>
              <div className={cn(
                'font-semibold',
                stat.isText ? 'text-sm text-slate-700' : 'text-lg text-slate-900'
              )}>
                {stat.value}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Tab Buttons */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setActiveTab('summary')}
          className={cn(
            'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
            activeTab === 'summary'
              ? 'bg-blue-600 text-white'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          )}
        >
          분석 요약
        </button>
        <button
          onClick={() => setActiveTab('logs')}
          className={cn(
            'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
            activeTab === 'logs'
              ? 'bg-blue-600 text-white'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          )}
        >
          원본 로그
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'summary' ? (
        <div className="prose prose-slate prose-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary}</ReactMarkdown>
        </div>
      ) : (
        <div className="bg-slate-900 rounded-lg overflow-hidden -mx-6 -mb-6">
          <div className="max-h-[400px] overflow-y-auto p-4 font-mono text-sm">
            {entries.length === 0 ? (
              <div className="text-slate-500 text-center py-8">No log entries found</div>
            ) : (
              entries.map((entry, idx) => (
                <div
                  key={idx}
                  className={cn(
                    'flex items-start gap-3 py-1.5 px-2 hover:bg-slate-800/50 rounded group',
                    entry.level?.toLowerCase() === 'error' && 'border-l-2 border-red-500 pl-3'
                  )}
                >
                  {/* Line Number */}
                  <span className="text-slate-600 select-none w-8 text-right shrink-0">
                    {idx + 1}
                  </span>

                  {/* Timestamp */}
                  <span className="text-slate-500 shrink-0">
                    {entry.timestamp
                      ? formatDate(entry.timestamp, {
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                        })
                      : '--:--:--'}
                  </span>

                  {/* Level */}
                  <span className={cn('w-12 shrink-0 font-bold', getLevelStyle(entry.level))}>
                    [{entry.level ? entry.level.toUpperCase().slice(0, 4) : '-'}]
                  </span>

                  {/* Message */}
                  <span className="text-slate-300 flex-1 break-all">{entry.message}</span>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="bg-slate-800 px-4 py-2 flex justify-between items-center text-xs text-slate-500 border-t border-slate-700">
            <span>{entries.length} lines</span>
            <span>UTF-8</span>
          </div>
        </div>
      )}
    </Card>
  )
}

export default LogAnalysisRenderer
