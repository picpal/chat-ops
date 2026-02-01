import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Cell,
} from 'recharts'
import type { RatingDistribution, RatingTrend } from '@/types/ratingsAnalytics'

interface RatingChartsProps {
  distribution?: RatingDistribution
  trend?: RatingTrend
  isLoading: boolean
}

export function RatingCharts({ distribution, trend, isLoading }: RatingChartsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {[0, 1].map((i) => (
          <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/3 mb-4" />
            <div className="h-48 bg-gray-100 rounded" />
          </div>
        ))}
      </div>
    )
  }

  const barData = (distribution?.distribution || []).map((d) => ({
    name: `${d.rating}점`,
    count: d.count,
    percentage: d.percentage,
  }))

  const BAR_COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6']

  const lineData = (trend?.trend || []).map((t) => ({
    date: t.date.slice(5), // MM-DD
    평균별점: t.averageRating,
    평가수: t.count,
  }))

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* 별점 분포 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-sm font-medium text-gray-500 mb-4">별점 분포</h3>
        {barData.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis allowDecimals={false} />
              <Tooltip
                formatter={(value: number, name: string) =>
                  name === 'count' ? [`${value}건`, '건수'] : [value, name]
                }
              />
              <Bar
                dataKey="count"
                radius={[4, 4, 0, 0]}
                label={{ position: 'top', fontSize: 12 }}
              >
                {barData.map((_, index) => (
                  <Cell key={index} fill={BAR_COLORS[index] || '#3b82f6'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-48 flex items-center justify-center text-gray-400">
            데이터가 없습니다
          </div>
        )}
      </div>

      {/* 일별 추이 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-sm font-medium text-gray-500 mb-4">일별 평균 추이</h3>
        {lineData.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={lineData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis domain={[0, 5]} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="평균별점"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-48 flex items-center justify-center text-gray-400">
            데이터가 없습니다
          </div>
        )}
      </div>
    </div>
  )
}
