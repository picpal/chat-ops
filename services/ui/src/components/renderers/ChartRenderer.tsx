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
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { ChartRenderSpec } from '@/types/renderSpec'
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
]

const ChartRenderer: React.FC<ChartRendererProps> = ({ spec, data }) => {
  const { open: openModal } = useModal()

  // Get chart data from QueryResult using dataRef
  const chartData = useMemo(() => {
    const extracted = getJSONPath(data, spec.dataRef) || []
    return Array.isArray(extracted) ? extracted : []
  }, [data, spec.dataRef])

  // Calculate summary stats
  const stats = useMemo(() => {
    if (chartData.length === 0) return null

    const values = chartData.map((d) => d[spec.yAxisKey]).filter((v) => typeof v === 'number')
    const total = values.reduce((sum, v) => sum + v, 0)
    const max = Math.max(...values)
    const avg = total / values.length

    return { total, max, avg, count: chartData.length }
  }, [chartData, spec.yAxisKey])

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

  // Render appropriate chart type
  const renderChart = () => {
    const colors = spec.config?.colors || COLORS
    const showGrid = spec.config?.showGrid ?? true
    const showLegend = spec.config?.showLegend ?? false

    const commonProps = {
      data: chartData,
      margin: { top: 10, right: 30, left: 0, bottom: 0 },
    }

    switch (spec.chartType) {
      case 'bar':
        return (
          <BarChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />}
            <XAxis dataKey={spec.xAxisKey} tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
              }}
            />
            {showLegend && <Legend />}
            <Bar dataKey={spec.yAxisKey} fill={colors[0]} radius={[4, 4, 0, 0]}>
              {chartData.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={colors[index % colors.length]}
                  opacity={0.8 + (index % 3) * 0.1}
                />
              ))}
            </Bar>
          </BarChart>
        )

      case 'line':
        return (
          <LineChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />}
            <XAxis dataKey={spec.xAxisKey} tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
              }}
            />
            {showLegend && <Legend />}
            <Line
              type="monotone"
              dataKey={spec.yAxisKey}
              stroke={colors[0]}
              strokeWidth={2}
              dot={{ fill: colors[0], strokeWidth: 2 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        )

      case 'area':
        return (
          <AreaChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />}
            <XAxis dataKey={spec.xAxisKey} tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
              }}
            />
            {showLegend && <Legend />}
            <defs>
              <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={colors[0]} stopOpacity={0.3} />
                <stop offset="95%" stopColor={colors[0]} stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey={spec.yAxisKey}
              stroke={colors[0]}
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorGradient)"
            />
          </AreaChart>
        )

      case 'pie':
        return (
          <PieChart>
            <Pie
              data={chartData}
              dataKey={spec.yAxisKey}
              nameKey={spec.xAxisKey}
              cx="50%"
              cy="50%"
              outerRadius={100}
              label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
              labelLine={false}
            >
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
              }}
            />
            {showLegend && <Legend />}
          </PieChart>
        )

      default:
        return (
          <div className="flex items-center justify-center h-full text-slate-500">
            Unsupported chart type: {spec.chartType}
          </div>
        )
    }
  }

  return (
    <Card
      title={spec.title || spec.config?.title}
      subtitle={spec.description}
      icon={spec.chartType === 'pie' ? 'pie_chart' : spec.chartType === 'bar' ? 'bar_chart' : 'show_chart'}
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

        {/* Stats Sidebar */}
        {stats && (
          <div className="lg:border-l lg:border-slate-200 lg:pl-8 flex flex-col justify-center space-y-4">
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
          </div>
        )}
      </div>
    </Card>
  )
}

export default ChartRenderer
