import React from 'react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  Label,
} from 'recharts'
import { useModal } from '@/hooks'
import { Icon } from '@/components/common'
import { ChartRenderSpec, ChartSeries, SummaryStatItem } from '@/types/renderSpec'
import { formatNumber, formatCompactNumber } from '@/utils'

// Summary Stats 값 포맷팅 헬퍼 함수
const formatStatValue = (
  value: string | number | null,
  type: SummaryStatItem['type']
): string => {
  if (value === null || value === undefined) return '-'

  // 문자열인 경우 그대로 반환 (이미 포맷팅된 값)
  if (typeof value === 'string') {
    return value
  }

  // 숫자 타입별 포맷팅
  switch (type) {
    case 'currency':
      if (value >= 100000000) {
        return `₩${(value / 100000000).toFixed(1)}억`
      }
      if (value >= 10000) {
        return `₩${Math.round(value / 10000)}만`
      }
      return `₩${value.toLocaleString()}`
    case 'percentage':
      return `${value.toFixed(1)}%`
    case 'number':
      return value.toLocaleString()
    case 'trend':
    case 'text':
    default:
      return String(value)
  }
}

// Default color palette matching design system
const COLORS = [
  '#137fec', // primary
  '#10b981', // emerald
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // violet
  '#06b6d4', // cyan
  '#3b82f6', // blue
  '#22c55e', // green
  '#ec4899', // pink
  '#f97316', // orange
]

interface ChartModalData {
  spec: ChartRenderSpec
  chartData: any[]
  stats: {
    total: number
    max: number
    avg: number
    count: number
  } | null
}

const ChartDetailModal: React.FC = () => {
  const { isOpen, type, data, close } = useModal()

  // Extract modal data
  const modalData = data as ChartModalData | undefined
  const spec = modalData?.spec
  const chartData = modalData?.chartData || []

  // Calculate stats from chartData directly (handle string values)
  const stats = React.useMemo(() => {
    if (chartData.length === 0 || !spec) return null

    const chartConfig = spec.chart
    const primaryYAxisKey = chartConfig.series?.[0]?.dataKey || chartConfig.yAxis?.dataKey || 'value'

    const values = chartData
      .map((d) => {
        const val = d[primaryYAxisKey]
        if (typeof val === 'string') return parseFloat(val)
        if (typeof val === 'number') return val
        return NaN
      })
      .filter((v) => !isNaN(v))

    if (values.length === 0) return null

    const total = values.reduce((sum, v) => sum + v, 0)
    const max = Math.max(...values)
    const avg = total / values.length

    return { total, max, avg, count: chartData.length }
  }, [chartData, spec])

  // ESC key handler
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    if (isOpen && type === 'chartDetail') {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [isOpen, type, close])

  if (!isOpen || type !== 'chartDetail' || !spec) return null

  // Extract chart config from nested structure
  const chartConfig = spec.chart
  const { xAxis, yAxis, series, chartType } = chartConfig
  const xAxisDataKey = xAxis?.dataKey || 'name'

  // Get series color with fallback
  const getSeriesColor = (s: ChartSeries, index: number): string => {
    return s.color || COLORS[index % COLORS.length]
  }

  // Get primary Y axis key for display
  const primaryYAxisKey = series?.[0]?.dataKey || yAxis?.dataKey || 'value'
  const primaryYAxisName = series?.[0]?.name || primaryYAxisKey

  // Render chart based on type
  const renderChart = () => {
    const showLegend = chartConfig.legend ?? (series && series.length > 1)

    const commonProps = {
      data: chartData,
      margin: { top: 20, right: 30, left: 20, bottom: xAxis?.label ? 40 : 20 },
    }

    const tooltipStyle = {
      contentStyle: {
        backgroundColor: '#0f172a',
        border: 'none',
        borderRadius: '8px',
        color: '#fff',
        fontSize: '12px',
      },
    }

    // Common X/Y Axis components with labels
    const renderXAxisComponent = () => (
      <XAxis dataKey={xAxisDataKey} tick={{ fontSize: 12 }} stroke="#94a3b8">
        {xAxis?.label && (
          <Label value={xAxis.label} offset={-10} position="insideBottom" style={{ fontSize: 12, fill: '#64748b' }} />
        )}
      </XAxis>
    )

    const renderYAxisComponent = () => (
      <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8">
        {yAxis?.label && (
          <Label value={yAxis.label} angle={-90} position="insideLeft" style={{ fontSize: 12, fill: '#64748b', textAnchor: 'middle' }} />
        )}
      </YAxis>
    )

    switch (chartType) {
      case 'bar':
        return (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            {renderXAxisComponent()}
            {renderYAxisComponent()}
            <Tooltip {...tooltipStyle} />
            {showLegend && <Legend />}
            {series && series.length > 0 ? (
              series.map((s, index) => (
                <Bar
                  key={s.dataKey}
                  dataKey={s.dataKey}
                  name={s.name || s.dataKey}
                  fill={getSeriesColor(s, index)}
                  radius={[4, 4, 0, 0]}
                />
              ))
            ) : (
              <Bar dataKey={primaryYAxisKey} fill={COLORS[0]} radius={[4, 4, 0, 0]}>
                {chartData.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                    opacity={0.9}
                  />
                ))}
              </Bar>
            )}
          </BarChart>
        )

      case 'line':
        return (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            {renderXAxisComponent()}
            {renderYAxisComponent()}
            <Tooltip {...tooltipStyle} />
            {showLegend && <Legend />}
            {series && series.length > 0 ? (
              series.map((s, index) => (
                <Line
                  key={s.dataKey}
                  type="monotone"
                  dataKey={s.dataKey}
                  name={s.name || s.dataKey}
                  stroke={getSeriesColor(s, index)}
                  strokeWidth={3}
                  dot={{ fill: '#fff', stroke: getSeriesColor(s, index), strokeWidth: 2, r: 4 }}
                  activeDot={{ r: 6, fill: getSeriesColor(s, index) }}
                />
              ))
            ) : (
              <Line
                type="monotone"
                dataKey={primaryYAxisKey}
                stroke={COLORS[0]}
                strokeWidth={3}
                dot={{ fill: '#fff', stroke: COLORS[0], strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6, fill: COLORS[0] }}
              />
            )}
          </LineChart>
        )

      case 'area':
        return (
          <AreaChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            {renderXAxisComponent()}
            {renderYAxisComponent()}
            <Tooltip {...tooltipStyle} />
            {showLegend && <Legend />}
            {series && series.length > 0 ? (
              series.map((s, index) => {
                const color = getSeriesColor(s, index)
                const gradientId = `colorGradientModal-${s.dataKey}`
                return (
                  <React.Fragment key={s.dataKey}>
                    <defs>
                      <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={color} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <Area
                      type="monotone"
                      dataKey={s.dataKey}
                      name={s.name || s.dataKey}
                      stroke={color}
                      strokeWidth={3}
                      fillOpacity={1}
                      fill={`url(#${gradientId})`}
                    />
                  </React.Fragment>
                )
              })
            ) : (
              <>
                <defs>
                  <linearGradient id="colorGradientModal" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS[0]} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={COLORS[0]} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey={primaryYAxisKey}
                  stroke={COLORS[0]}
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#colorGradientModal)"
                />
              </>
            )}
          </AreaChart>
        )

      case 'pie':
        const pieDataKey = series?.[0]?.dataKey || yAxis?.dataKey || 'value'

        // Convert string values to numbers for pie chart
        const pieChartData = chartData.map((item) => ({
          ...item,
          [pieDataKey]: typeof item[pieDataKey] === 'string'
            ? parseFloat(item[pieDataKey])
            : item[pieDataKey],
        }))

        const RADIAN = Math.PI / 180
        const renderCustomizedLabel = ({
          cx,
          cy,
          midAngle,
          innerRadius,
          outerRadius,
          percent,
        }: {
          cx: number
          cy: number
          midAngle: number
          innerRadius: number
          outerRadius: number
          percent: number
        }) => {
          const radius = innerRadius + (outerRadius - innerRadius) * 0.5
          const x = cx + radius * Math.cos(-midAngle * RADIAN)
          const y = cy + radius * Math.sin(-midAngle * RADIAN)

          if (percent < 0.05) return null

          return (
            <text
              x={x}
              y={y}
              fill="white"
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={14}
              fontWeight={600}
            >
              {`${(percent * 100).toFixed(0)}%`}
            </text>
          )
        }

        return (
          <PieChart>
            <Pie
              data={pieChartData}
              dataKey={pieDataKey}
              nameKey={xAxisDataKey}
              cx="50%"
              cy="50%"
              outerRadius={140}
              innerRadius={70}
              label={renderCustomizedLabel}
              labelLine={false}
              paddingAngle={2}
            >
              {pieChartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip {...tooltipStyle} />
            <Legend
              layout="horizontal"
              verticalAlign="bottom"
              align="center"
              wrapperStyle={{ paddingTop: 20 }}
            />
          </PieChart>
        )

      default:
        return (
          <div className="flex items-center justify-center h-full text-slate-500">
            Unsupported chart type
          </div>
        )
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
        onClick={close}
      />

      {/* Modal */}
      <div className="relative w-full max-w-6xl bg-white rounded-2xl shadow-2xl flex flex-col h-[85vh] overflow-hidden animate-fade-in-up ring-1 ring-slate-900/5">
        {/* Header */}
        <div className="flex items-center justify-between px-8 py-5 border-b border-slate-100 bg-white shrink-0">
          <div>
            <h2 className="text-xl font-bold text-slate-800">
              {spec.title || 'Maximized Chart View'}
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              {spec.description || `${chartType} chart visualization`}
            </p>
          </div>
          <div className="flex items-center gap-4">
            {/* Download Button */}
            <div className="relative group">
              <button className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 hover:text-primary rounded-lg text-sm font-medium transition-colors shadow-sm">
                <Icon name="download" size="sm" />
                <span>Download</span>
                <Icon name="expand_more" size="sm" />
              </button>
              {/* Dropdown */}
              <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-xl shadow-xl border border-slate-100 py-2 z-50 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
                <div className="px-4 py-2 border-b border-slate-50 mb-1">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Export Options
                  </span>
                </div>
                <button className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50 hover:text-primary transition-colors">
                  <Icon name="image" className="text-slate-400" />
                  Download as PNG
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50 hover:text-primary transition-colors">
                  <Icon name="picture_as_pdf" className="text-slate-400" />
                  Download as PDF
                </button>
              </div>
            </div>

            {/* Close Button */}
            <button
              onClick={close}
              className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <Icon name="close" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto bg-slate-50/50 p-8">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 h-full">
            {/* Chart Area */}
            <div className="lg:col-span-3 flex flex-col gap-6">
              {/* Chart Container */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex-1 min-h-[400px] flex flex-col">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-lg font-bold text-slate-800">
                      {spec.title || 'Chart Visualization'}
                    </h3>
                    <p className="text-sm text-slate-500">
                      {spec.description || 'Data visualization'}
                    </p>
                  </div>
                  {/* Legend Indicators */}
                  <div className="flex gap-4">
                    {series && series.length > 0 ? (
                      series.map((s, index) => (
                        <div key={s.dataKey} className="flex items-center gap-2">
                          <span
                            className="w-3 h-0.5"
                            style={{ backgroundColor: getSeriesColor(s, index) }}
                          />
                          <span className="text-xs font-medium text-slate-600">
                            {s.name || s.dataKey}
                          </span>
                        </div>
                      ))
                    ) : (
                      <div className="flex items-center gap-2">
                        <span
                          className="w-3 h-0.5"
                          style={{ backgroundColor: COLORS[0] }}
                        />
                        <span className="text-xs font-medium text-slate-600">
                          {primaryYAxisName}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Chart */}
                <div className="flex-1 min-h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    {renderChart()}
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Insight Box */}
              <div className="bg-blue-50/50 border border-blue-100 p-4 rounded-xl flex gap-4 items-start">
                <div className="p-2 bg-blue-100 text-blue-600 rounded-lg shrink-0">
                  <Icon name="trending_up" size="sm" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-slate-800">
                    인사이트: 데이터 분석
                    {chartConfig.insight?.source === 'llm' && (
                      <span className="ml-2 text-xs font-normal text-blue-600 bg-blue-100 px-1.5 py-0.5 rounded">
                        AI 생성
                      </span>
                    )}
                  </h4>
                  <p className="text-sm text-slate-600 mt-1 leading-relaxed">
                    {chartConfig.insight?.content ? (
                      // 백엔드에서 생성된 인사이트 사용
                      chartConfig.insight.content
                    ) : stats ? (
                      // 폴백: 프론트엔드 템플릿
                      <>
                        총 <strong>{stats.count}</strong>개 데이터 포인트의
                        합계는 <strong>{formatNumber(stats.total)}</strong>입니다.
                        평균 <strong>{formatNumber(stats.avg, 1)}</strong>,
                        최대값 <strong>{formatNumber(stats.max)}</strong>입니다.
                      </>
                    ) : (
                      '분석할 데이터가 없습니다.'
                    )}
                  </p>
                </div>
              </div>
            </div>

            {/* Stats Sidebar */}
            <div className="lg:col-span-1 space-y-6">
              {/* Summary Stats Card - Dynamic rendering with backend summaryStats priority */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    Summary Stats
                  </h4>
                  {chartConfig.summaryStats?.source === 'llm' && (
                    <span className="text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded font-medium">
                      AI 분석
                    </span>
                  )}
                </div>
                {/* Backend summaryStats가 있으면 사용 */}
                {chartConfig.summaryStats?.items?.length ? (
                  <div className="space-y-4">
                    {chartConfig.summaryStats.items.map((item: SummaryStatItem, index: number) => (
                      <React.Fragment key={item.key}>
                        <div className={item.highlight ? 'bg-blue-50/50 -mx-2 px-2 py-2 rounded-lg' : ''}>
                          <div className="flex items-center gap-1.5 mb-1">
                            {item.icon && (
                              <Icon name={item.icon} size="xs" className="text-slate-400" />
                            )}
                            <p className="text-xs text-slate-500">{item.label}</p>
                          </div>
                          <p className={`font-bold text-slate-800 break-all ${item.highlight ? 'text-xl' : 'text-lg'}`}>
                            {formatStatValue(item.value, item.type)}
                          </p>
                        </div>
                        {index < chartConfig.summaryStats!.items.length - 1 && (
                          <div className="h-px bg-slate-100 w-full" />
                        )}
                      </React.Fragment>
                    ))}
                  </div>
                ) : stats ? (
                  /* 폴백: 기존 프론트엔드 계산 stats */
                  <div className="space-y-4">
                    <div>
                      <p className="text-xs text-slate-500 mb-1">Total</p>
                      <p className="text-xl font-bold text-slate-800 break-all">
                        {formatCompactNumber(stats.total)}
                      </p>
                    </div>
                    <div className="h-px bg-slate-100 w-full" />
                    <div>
                      <p className="text-xs text-slate-500 mb-1">Average</p>
                      <p className="text-lg font-bold text-slate-800 break-all">
                        {formatCompactNumber(stats.avg)}
                      </p>
                    </div>
                    <div className="h-px bg-slate-100 w-full" />
                    <div>
                      <p className="text-xs text-slate-500 mb-1">Peak Value</p>
                      <p className="text-lg font-bold text-slate-800 break-all">
                        {formatCompactNumber(stats.max)}
                      </p>
                    </div>
                    <div className="h-px bg-slate-100 w-full" />
                    <div>
                      <p className="text-xs text-slate-500 mb-1">Data Points</p>
                      <p className="text-lg font-bold text-slate-800">
                        {stats.count}
                      </p>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No statistics available</p>
                )}
              </div>

              {/* Data Source Card */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">
                  Data Source
                </h4>
                <div className="flex items-center gap-3 mb-3">
                  <div className="h-8 w-8 rounded bg-slate-100 flex items-center justify-center text-slate-500">
                    <Icon name="database" size="sm" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-800">
                      Query Result
                    </p>
                    <p className="text-xs text-slate-500">
                      {chartConfig.dataRef || 'data.rows'}
                    </p>
                  </div>
                </div>
                <p className="text-xs text-slate-400 italic">
                  Last sync: Just now
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChartDetailModal
