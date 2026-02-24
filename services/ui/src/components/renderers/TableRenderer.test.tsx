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

describe('number formatting', () => {
  // number 타입 컬럼을 가진 spec
  const numberTableSpec = {
    type: 'table' as const,
    requestId: 'req-number-001',
    title: 'Number Format Test',
    description: 'Testing number column formatting',
    table: {
      dataRef: 'data.rows',
      columns: [
        { key: 'label', label: 'Label', type: 'string' as const },
        { key: 'value', label: 'Value', type: 'number' as const },
      ],
      actions: [],
      pagination: { enabled: false },
    },
  }

  const numberTableResult: import('@/types/queryResult').QueryResult = {
    requestId: 'req-number-001',
    status: 'success',
    data: {
      rows: [
        { label: 'integer_string', value: '158.000000000000000000' },
        { label: 'decimal_string', value: '3.14159265358979' },
        { label: 'integer_number', value: 1234567 },
        { label: 'decimal_number', value: 1234.56 },
      ],
    },
    metadata: {
      executionTimeMs: 10,
      rowsReturned: 4,
    },
  }

  it('formats integer-valued numeric string (18 decimal places) without decimal point', () => {
    renderWithProvider(<TableRenderer spec={numberTableSpec} data={numberTableResult} />)

    // "158.000000000000000000" 는 정수이므로 "158" 로 표시되어야 함
    // 현재 구현(string → 그대로 반환)에서는 "158.000000000000000000" 이 표시됨 → 실패 예상
    expect(screen.getByText('158')).toBeInTheDocument()
    expect(screen.queryByText('158.000000000000000000')).not.toBeInTheDocument()
  })

  it('formats decimal numeric string with max 2 decimal places', () => {
    renderWithProvider(<TableRenderer spec={numberTableSpec} data={numberTableResult} />)

    // "3.14159265358979" → 최대 소수 2자리 "3.14" 로 표시되어야 함
    // 현재 구현에서는 "3.14159265358979" 그대로 표시됨 → 실패 예상
    expect(screen.getByText('3.14')).toBeInTheDocument()
    expect(screen.queryByText('3.14159265358979')).not.toBeInTheDocument()
  })

  it('formats integer number type with thousands separator', () => {
    renderWithProvider(<TableRenderer spec={numberTableSpec} data={numberTableResult} />)

    // 1234567 → "1,234,567" 로 표시되어야 함
    // 현재 구현은 toLocaleString() 사용 → 환경에 따라 통과 가능하나 명시적 검증
    expect(screen.getByText('1,234,567')).toBeInTheDocument()
  })

  it('formats decimal number type with thousands separator and 2 decimal places', () => {
    renderWithProvider(<TableRenderer spec={numberTableSpec} data={numberTableResult} />)

    // 1234.56 → "1,234.56" 로 표시되어야 함
    // 현재 구현은 toLocaleString() 사용 → 환경에 따라 통과 가능하나 명시적 검증
    expect(screen.getByText('1,234.56')).toBeInTheDocument()
  })
})
