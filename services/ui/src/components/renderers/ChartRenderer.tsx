import React, { useMemo } from 'react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  AreaChart,
  Area,
  ComposedChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  Label,
} from 'recharts'
import { ChartRenderSpec, ChartSeries, SummaryStatItem } from '@/types/renderSpec'
import { QueryResult } from '@/types/queryResult'
import { Card, Button, Icon } from '@/components/common'
import { useModal } from '@/hooks'
import { getJSONPath, formatNumber } from '@/utils'

interface ChartRendererProps {
  spec: ChartRenderSpec
  data: QueryResult
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
      // 억 단위
      if (value >= 100000000) {
        return `₩${(value / 100000000).toFixed(1)}억`
      }
      // 만 단위
      if (value >= 10000) {
        return `₩${Math.round(value / 10000)}만`
      }
      return `₩${value.toLocaleString()}`

    case 'percentage':
      return `${value.toFixed(1)}%`

    case 'number':
      return value.toLocaleString()

    case 'trend':
      return String(value)

    case 'text':
    default:
      return String(value)
  }
}

const ChartRenderer: React.FC<ChartRendererProps> = ({ spec, data }) => {
  const { open: openModal } = useModal()

  // Extract chart config from nested structure
  const chartConfig = spec.chart

  // Get chart data from QueryResult using dataRef or inline data
  const chartData = useMemo(() => {
    if (spec.data) {
      // If inline data is provided, use it directly
      const dataRef = chartConfig.dataRef || 'rows'
      const extracted = getJSONPath(spec.data, dataRef) || spec.data
      return Array.isArray(extracted) ? extracted : []
    }
    // Otherwise get from QueryResult using dataRef
    const dataRef = chartConfig.dataRef || 'data.rows'
    const extracted = getJSONPath(data, dataRef) || []
    return Array.isArray(extracted) ? extracted : []
  }, [data, spec.data, chartConfig.dataRef])

  // Get primary Y axis dataKey for stats calculation
  const primaryYAxisKey = useMemo(() => {
    if (chartConfig.series && chartConfig.series.length > 0) {
      return chartConfig.series[0].dataKey
    }
    return chartConfig.yAxis?.dataKey || 'value'
  }, [chartConfig])

  // Calculate summary stats
  const stats = useMemo(() => {
    if (chartData.length === 0) return null

    const values = chartData
      .map((d) => {
        const val = d[primaryYAxisKey]
        // Convert string to number if needed
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
  }, [chartData, primaryYAxisKey])

  const handleFullscreen = () => {
    openModal('chartDetail', { spec, data, chartData, stats })
  }

  const actions = (
    <>
      <Button variant="secondary" size="sm" icon="download">
        Export CSV
      </Button>
      <button
        className="p-1.5 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
        onClick={handleFullscreen}
      >
        <Icon name="fullscreen" size="sm" />
      </button>
    </>
  )

  // Get series color with fallback
  const getSeriesColor = (series: ChartSeries, index: number): string => {
    return series.color || COLORS[index % COLORS.length]
  }

  // Render series element based on type
  const renderSeriesElement = (series: ChartSeries, index: number, defaultType: 'bar' | 'line' | 'area') => {
    const color = getSeriesColor(series, index)
    const seriesType = series.type || defaultType

    switch (seriesType) {
      case 'bar':
        return (
          <Bar
            key={series.dataKey}
            dataKey={series.dataKey}
            name={series.name || series.dataKey}
            fill={color}
            radius={[4, 4, 0, 0]}
          />
        )
      case 'line':
        return (
          <Line
            key={series.dataKey}
            type="monotone"
            dataKey={series.dataKey}
            name={series.name || series.dataKey}
            stroke={color}
            strokeWidth={2}
            dot={{ fill: color, strokeWidth: 2 }}
            activeDot={{ r: 6 }}
          />
        )
      case 'area':
        return (
          <Area
            key={series.dataKey}
            type="monotone"
            dataKey={series.dataKey}
            name={series.name || series.dataKey}
            stroke={color}
            strokeWidth={2}
            fillOpacity={0.3}
            fill={color}
          />
        )
      default:
        return null
    }
  }

  // Render appropriate chart type
  const renderChart = () => {
    const { xAxis, yAxis, series, legend, tooltip, chartType } = chartConfig
    const showLegend = legend ?? (series && series.length > 1)
    const showTooltip = tooltip ?? true
    const xAxisDataKey = xAxis?.dataKey || 'name'

    const commonProps = {
      data: chartData,
      margin: { top: 20, right: 30, left: 20, bottom: xAxis?.label ? 40 : 20 },
    }

    const tooltipStyle = {
      contentStyle: {
        backgroundColor: '#fff',
        border: '1px solid #e2e8f0',
        borderRadius: '8px',
        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
      },
    }

    // Common X/Y Axis components with labels
    const renderXAxis = () => (
      <XAxis dataKey={xAxisDataKey} tick={{ fontSize: 12 }} stroke="#94a3b8">
        {xAxis?.label && (
          <Label value={xAxis.label} offset={-10} position="insideBottom" style={{ fontSize: 12, fill: '#64748b' }} />
        )}
      </XAxis>
    )

    const renderYAxis = () => (
      <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8">
        {yAxis?.label && (
          <Label value={yAxis.label} angle={-90} position="insideLeft" style={{ fontSize: 12, fill: '#64748b', textAnchor: 'middle' }} />
        )}
      </YAxis>
    )

    // If we have multiple series or composed type, use ComposedChart
    const hasMultipleSeries = series && series.length > 1
    const useComposedChart = chartType === 'composed' || (hasMultipleSeries && series.some(s => s.type && s.type !== chartType))

    if (useComposedChart && series) {
      return (
        <ComposedChart {...commonProps}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          {renderXAxis()}
          {renderYAxis()}
          {showTooltip && <Tooltip {...tooltipStyle} />}
          {showLegend && <Legend />}
          {series.map((s, index) => renderSeriesElement(s, index, 'bar'))}
        </ComposedChart>
      )
    }

    switch (chartType) {
      case 'bar':
        return (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            {renderXAxis()}
            {renderYAxis()}
            {showTooltip && <Tooltip {...tooltipStyle} />}
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
              <Bar
                dataKey={yAxis?.dataKey || 'value'}
                fill={COLORS[0]}
                radius={[4, 4, 0, 0]}
              >
                {chartData.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                    opacity={0.8 + (index % 3) * 0.1}
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
            {renderXAxis()}
            {renderYAxis()}
            {showTooltip && <Tooltip {...tooltipStyle} />}
            {showLegend && <Legend />}
            {series && series.length > 0 ? (
              series.map((s, index) => (
                <Line
                  key={s.dataKey}
                  type="monotone"
                  dataKey={s.dataKey}
                  name={s.name || s.dataKey}
                  stroke={getSeriesColor(s, index)}
                  strokeWidth={2}
                  dot={{ fill: getSeriesColor(s, index), strokeWidth: 2 }}
                  activeDot={{ r: 6 }}
                />
              ))
            ) : (
              <Line
                type="monotone"
                dataKey={yAxis?.dataKey || 'value'}
                stroke={COLORS[0]}
                strokeWidth={2}
                dot={{ fill: COLORS[0], strokeWidth: 2 }}
                activeDot={{ r: 6 }}
              />
            )}
          </LineChart>
        )

      case 'area':
        return (
          <AreaChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            {renderXAxis()}
            {renderYAxis()}
            {showTooltip && <Tooltip {...tooltipStyle} />}
            {showLegend && <Legend />}
            {series && series.length > 0 ? (
              series.map((s, index) => {
                const color = getSeriesColor(s, index)
                const gradientId = `colorGradient-${s.dataKey}`
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
                      strokeWidth={2}
                      fillOpacity={1}
                      fill={`url(#${gradientId})`}
                    />
                  </React.Fragment>
                )
              })
            ) : (
              <>
                <defs>
                  <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS[0]} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={COLORS[0]} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey={yAxis?.dataKey || 'value'}
                  stroke={COLORS[0]}
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorGradient)"
                />
              </>
            )}
          </AreaChart>
        )

      case 'pie':
        const pieDataKey = series?.[0]?.dataKey || yAxis?.dataKey || 'value'
        const pieNameKey = xAxisDataKey

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

          if (percent < 0.05) return null // Hide label for slices less than 5%

          return (
            <text
              x={x}
              y={y}
              fill="white"
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={12}
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
              nameKey={pieNameKey}
              cx="50%"
              cy="50%"
              outerRadius={100}
              innerRadius={50}
              label={renderCustomizedLabel}
              labelLine={false}
              paddingAngle={2}
            >
              {pieChartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            {showTooltip && <Tooltip {...tooltipStyle} />}
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
            Unsupported chart type: {chartType}
          </div>
        )
    }
  }

  // Get chart icon based on chart type
  const getChartIcon = () => {
    switch (chartConfig.chartType) {
      case 'pie':
        return 'pie_chart'
      case 'bar':
        return 'bar_chart'
      case 'area':
        return 'area_chart'
      default:
        return 'show_chart'
    }
  }

  return (
    <Card
      title={spec.title}
      subtitle={spec.description}
      icon={getChartIcon()}
      actions={actions}
      className="animate-fade-in-up"
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Chart */}
        <div className="lg:col-span-2">
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              {renderChart()}
            </ResponsiveContainer>
          </div>
        </div>

        {/* Stats Sidebar - Dynamic rendering with backend summaryStats priority */}
        {(chartConfig.summaryStats?.items?.length || stats) && (
          <div className="lg:border-l lg:border-slate-200 lg:pl-8 flex flex-col justify-center space-y-4">
            {/* Backend summaryStats가 있으면 사용 */}
            {chartConfig.summaryStats?.items?.length ? (
              <>
                {chartConfig.summaryStats.source === 'llm' && (
                  <div className="flex items-center gap-1 mb-2">
                    <span className="text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded font-medium">
                      AI 분석
                    </span>
                  </div>
                )}
                {chartConfig.summaryStats.items.slice(0, 4).map((item: SummaryStatItem) => (
                  <div key={item.key} className={item.highlight ? 'bg-blue-50/50 -mx-2 px-2 py-1 rounded-lg' : ''}>
                    <div className="flex items-center gap-1.5 mb-1">
                      {item.icon && (
                        <Icon name={item.icon} size="xs" className="text-slate-400" />
                      )}
                      <p className="text-slate-500 text-sm font-medium">{item.label}</p>
                    </div>
                    <p className={`text-slate-900 ${item.highlight ? 'text-xl font-bold' : 'text-lg font-semibold'}`}>
                      {formatStatValue(item.value, item.type)}
                    </p>
                  </div>
                ))}
              </>
            ) : stats && (
              /* 폴백: 기존 프론트엔드 계산 stats */
              <>
                <div>
                  <p className="text-slate-500 text-sm font-medium mb-1">Total</p>
                  <p className="text-slate-900 text-3xl font-bold tracking-tight">
                    {formatNumber(stats.total)}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500 text-sm font-medium mb-1">Average</p>
                  <p className="text-slate-900 text-xl font-semibold">
                    {formatNumber(stats.avg, 1)}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500 text-sm font-medium mb-1">Peak</p>
                  <p className="text-slate-900 text-xl font-semibold">
                    {formatNumber(stats.max)}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500 text-sm font-medium mb-1">Data Points</p>
                  <p className="text-slate-700 text-lg">{stats.count}</p>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}

export default ChartRenderer
