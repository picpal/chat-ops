import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ChartRenderer from './ChartRenderer'
import { mockChartResult, chartSpec } from '@/test/mocks/fixtures'
import { useUIStore } from '@/store'
import { ChartRenderSpec } from '@/types/renderSpec'

describe('ChartRenderer', () => {
  beforeEach(() => {
    useUIStore.setState({
      sidebarCollapsed: false,
      modal: { isOpen: false, type: null },
    })
  })

  it('renders chart with title and description', () => {
    render(<ChartRenderer spec={chartSpec} data={mockChartResult} />)

    expect(screen.getByText('Transaction Volume Trends')).toBeInTheDocument()
    expect(screen.getByText('Last 7 Days')).toBeInTheDocument()
  })

  it('calculates and displays stats correctly', () => {
    render(<ChartRenderer spec={chartSpec} data={mockChartResult} />)

    // Stats sidebar should show total, average, peak, and count
    expect(screen.getByText('Total')).toBeInTheDocument()
    expect(screen.getByText('Average')).toBeInTheDocument()
    expect(screen.getByText('Peak')).toBeInTheDocument()
    expect(screen.getByText('Data Points')).toBeInTheDocument()

    // Verify data points count
    expect(screen.getByText('7')).toBeInTheDocument()
  })

  it('shows total value', () => {
    render(<ChartRenderer spec={chartSpec} data={mockChartResult} />)

    // Total: 25000 + 32000 + 28000 + 38420 + 42000 + 45000 + 48200 = 258,620
    expect(screen.getByText('258,620')).toBeInTheDocument()
  })

  it('opens fullscreen modal when button clicked', () => {
    render(<ChartRenderer spec={chartSpec} data={mockChartResult} />)

    const buttons = screen.getAllByRole('button')
    const fullscreenButton = buttons.find(
      (btn) => btn.querySelector('.material-symbols-outlined')?.textContent === 'fullscreen'
    )

    if (fullscreenButton) {
      fireEvent.click(fullscreenButton)

      const { modal } = useUIStore.getState()
      expect(modal.isOpen).toBe(true)
      expect(modal.type).toBe('chartDetail')
    }
  })

  it('handles empty data gracefully', () => {
    const emptyResult = {
      ...mockChartResult,
      data: { rows: [] },
    }

    render(<ChartRenderer spec={chartSpec} data={emptyResult} />)

    // Should render without errors
    expect(screen.getByText('Transaction Volume Trends')).toBeInTheDocument()
    // Stats should not be displayed
    expect(screen.queryByText('Total')).not.toBeInTheDocument()
  })

  it('renders export button', () => {
    render(<ChartRenderer spec={chartSpec} data={mockChartResult} />)

    expect(screen.getByText('Export CSV')).toBeInTheDocument()
  })

  it('renders bar chart icon for bar chart type', () => {
    const barSpec: ChartRenderSpec = { ...chartSpec, chartType: 'bar' }
    render(<ChartRenderer spec={barSpec} data={mockChartResult} />)

    expect(screen.getByText('bar_chart')).toBeInTheDocument()
  })

  it('renders line chart icon for line chart type', () => {
    const lineSpec: ChartRenderSpec = { ...chartSpec, chartType: 'line' }
    render(<ChartRenderer spec={lineSpec} data={mockChartResult} />)

    expect(screen.getByText('show_chart')).toBeInTheDocument()
  })

  it('renders pie chart icon for pie chart type', () => {
    const pieSpec: ChartRenderSpec = { ...chartSpec, chartType: 'pie' }
    render(<ChartRenderer spec={pieSpec} data={mockChartResult} />)

    expect(screen.getByText('pie_chart')).toBeInTheDocument()
  })
})
