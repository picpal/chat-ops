import { useState } from 'react'
import type { AnalyticsPeriod } from '@/types/ratingsAnalytics'
import { useRatingSummary, useRatingDistribution, useRatingTrend } from '@/hooks/useRatingsAnalytics'
import { SummaryCards } from './SummaryCards'
import { RatingCharts } from './RatingCharts'
import { RatingDetailsTable } from './RatingDetailsTable'
import { LowRatingPanel } from './LowRatingPanel'
import { QualityAnswerToggle } from './QualityAnswerToggle'

const PERIOD_OPTIONS: { value: AnalyticsPeriod; label: string }[] = [
  { value: 'today', label: '오늘' },
  { value: '7d', label: '7일' },
  { value: '30d', label: '30일' },
  { value: 'all', label: '전체' },
]

export function ScenariosPage() {
  const [period, setPeriod] = useState<AnalyticsPeriod>('all')

  const summary = useRatingSummary(period)
  const distribution = useRatingDistribution(period)
  const trend = useRatingTrend(period)

  return (
    <div className="h-full overflow-y-auto bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">시나리오 관리</h1>
              <p className="mt-1 text-sm text-gray-500">
                AI 응답 별점 데이터를 분석하여 엔지니어링 개선에 활용합니다
              </p>
            </div>
            <div className="flex items-center gap-6">
              {/* Quality Answer RAG 토글 */}
              <QualityAnswerToggle />

              {/* 기간 선택 */}
              <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
                {PERIOD_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setPeriod(opt.value)}
                    className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      period === opt.value
                        ? 'bg-white shadow text-gray-900'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* 요약 카드 */}
        <SummaryCards data={summary.data} isLoading={summary.isLoading} />

        {/* 차트 */}
        <RatingCharts
          distribution={distribution.data}
          trend={trend.data}
          isLoading={distribution.isLoading || trend.isLoading}
        />

        {/* 상세 테이블 */}
        <RatingDetailsTable />

        {/* 낮은 별점 패널 */}
        <LowRatingPanel />
      </main>
    </div>
  )
}
