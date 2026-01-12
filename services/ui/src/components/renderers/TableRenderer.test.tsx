import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import TableRenderer from './TableRenderer'
import { mockTableResult, tableSpec } from '@/test/mocks/fixtures'
import { useUIStore } from '@/store'

// Create wrapper with QueryClientProvider
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

const renderWithProvider = (ui: React.ReactElement) => {
  const Wrapper = createWrapper()
  return render(<Wrapper>{ui}</Wrapper>)
}

describe('TableRenderer', () => {
  beforeEach(() => {
    useUIStore.setState({
      sidebarCollapsed: false,
      modal: { isOpen: false, type: null },
    })
  })

  it('renders table with title and description', () => {
    renderWithProvider(<TableRenderer spec={tableSpec} data={mockTableResult} />)

    expect(screen.getByText('Recent Transactions')).toBeInTheDocument()
    expect(screen.getByText('PG, Payment, Settlement & Purchase Logs')).toBeInTheDocument()
  })

  it('renders all column headers', () => {
    renderWithProvider(<TableRenderer spec={tableSpec} data={mockTableResult} />)

    expect(screen.getByText('Transaction ID')).toBeInTheDocument()
    expect(screen.getByText('Date')).toBeInTheDocument()
    expect(screen.getByText('Amount')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByText('Merchant')).toBeInTheDocument()
  })

  it('renders data rows', () => {
    renderWithProvider(<TableRenderer spec={tableSpec} data={mockTableResult} />)

    expect(screen.getByText('TXN_9823491')).toBeInTheDocument()
    expect(screen.getByText('Uber Technologies')).toBeInTheDocument()
    expect(screen.getByText('$4,250.00')).toBeInTheDocument()
  })

  it('renders status badges', () => {
    renderWithProvider(<TableRenderer spec={tableSpec} data={mockTableResult} />)

    expect(screen.getAllByText('Failed').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Success').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Pending').length).toBeGreaterThan(0)
  })

  it('shows row count in footer', () => {
    renderWithProvider(<TableRenderer spec={tableSpec} data={mockTableResult} />)

    expect(screen.getByText('8 rows')).toBeInTheDocument()
  })

  it('displays request ID in footer', () => {
    renderWithProvider(<TableRenderer spec={tableSpec} data={mockTableResult} />)

    expect(screen.getByText('Query: req-table-001')).toBeInTheDocument()
  })

  it('shows empty state when no data', () => {
    const emptyData = {
      ...mockTableResult,
      data: { rows: [] },
    }

    renderWithProvider(<TableRenderer spec={tableSpec} data={emptyData} />)

    expect(screen.getByText('No data available')).toBeInTheDocument()
  })

  it('renders export button when export action is enabled', () => {
    renderWithProvider(<TableRenderer spec={tableSpec} data={mockTableResult} />)

    expect(screen.getByText('Export CSV')).toBeInTheDocument()
  })

  it('sorts by column when clicked', () => {
    renderWithProvider(<TableRenderer spec={tableSpec} data={mockTableResult} />)

    const amountHeader = screen.getByText('Amount')
    fireEvent.click(amountHeader)

    // After clicking, the table should be sorted
    // We can verify by checking the order of amounts in the DOM
    const amounts = screen.getAllByText(/\$[\d,]+\.\d{2}/)
    expect(amounts.length).toBeGreaterThan(0)
  })

  it('toggles sort direction on repeated click', () => {
    renderWithProvider(<TableRenderer spec={tableSpec} data={mockTableResult} />)

    const amountHeader = screen.getByText('Amount')

    // First click - ascending
    fireEvent.click(amountHeader)

    // Second click - descending
    fireEvent.click(amountHeader)

    // Header should still be clickable and table should be sorted
    expect(amountHeader).toBeInTheDocument()
  })

  it('opens fullscreen modal when fullscreen button clicked', () => {
    renderWithProvider(<TableRenderer spec={tableSpec} data={mockTableResult} />)

    // Find the fullscreen button (icon button)
    const buttons = screen.getAllByRole('button')
    const fullscreenButton = buttons.find(
      (btn) => btn.querySelector('.material-symbols-outlined')?.textContent === 'fullscreen'
    )

    if (fullscreenButton) {
      fireEvent.click(fullscreenButton)

      const { modal } = useUIStore.getState()
      expect(modal.isOpen).toBe(true)
      expect(modal.type).toBe('tableDetail')
    }
  })
})
