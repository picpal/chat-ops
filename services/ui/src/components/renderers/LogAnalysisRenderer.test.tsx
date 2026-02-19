import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import LogAnalysisRenderer from './LogAnalysisRenderer'
import { LogAnalysisRenderSpec } from '@/types/renderSpec'

// Mock LogAnalysisRenderSpec
const mockLogAnalysisSpec: LogAnalysisRenderSpec = {
  type: 'log_analysis',
  requestId: 'req-log-analysis-001',
  title: '서버 로그 분석 결과',
  description: 'API 서버 로그 분석',
  log_analysis: {
    summary: `## 분석 요약

서버 로그 분석 결과, 다음과 같은 패턴이 발견되었습니다:

### 주요 발견 사항
- **에러 집중 시간대**: 오전 10시 ~ 11시
- **주요 에러 유형**: Connection timeout (60%)

### 권장 조치
1. 게이트웨이 연결 상태 점검
2. 재시도 큐 설정 검토`,
    statistics: {
      totalEntries: 150,
      errorCount: 12,
      warnCount: 25,
      timeRange: '2024-10-24 08:00 ~ 12:00',
    },
    entries: [
      { timestamp: '2024-10-24T10:42:01.112Z', level: 'ERROR', message: '[PaymentGateway] Connection timeout.' },
      { timestamp: '2024-10-24T10:42:01.115Z', level: 'WARN', message: '[RetryQueue] Scheduled retry in 500ms.' },
      { timestamp: '2024-10-24T10:42:01.620Z', level: 'INFO', message: '[PaymentGateway] Retry 1 initiated.' },
      { timestamp: '2024-10-24T10:42:02.850Z', level: 'INFO', message: '[PaymentGateway] Response: 200 OK.' },
      { timestamp: '2024-10-24T10:42:02.855Z', level: 'DEBUG', message: '[AuditTrail] Transaction captured.' },
    ],
  },
}

describe('LogAnalysisRenderer', () => {
  describe('Statistics Rendering', () => {
    it('renders statistics cards with correct values', () => {
      render(<LogAnalysisRenderer spec={mockLogAnalysisSpec} />)

      // Total entries
      expect(screen.getByText('전체 로그')).toBeInTheDocument()
      expect(screen.getByText('150')).toBeInTheDocument()

      // Error count
      expect(screen.getByText('에러')).toBeInTheDocument()
      expect(screen.getByText('12')).toBeInTheDocument()

      // Warn count
      expect(screen.getByText('경고')).toBeInTheDocument()
      expect(screen.getByText('25')).toBeInTheDocument()

      // Time range
      expect(screen.getByText('시간 범위')).toBeInTheDocument()
      expect(screen.getByText('2024-10-24 08:00 ~ 12:00')).toBeInTheDocument()
    })
  })

  describe('Tab Functionality', () => {
    it('has summary tab active by default', () => {
      render(<LogAnalysisRenderer spec={mockLogAnalysisSpec} />)

      const summaryTab = screen.getByRole('button', { name: /분석 요약/i })
      const logsTab = screen.getByRole('button', { name: /원본 로그/i })

      // Summary tab should be active (has active class)
      expect(summaryTab).toHaveClass('bg-blue-600')
      expect(logsTab).not.toHaveClass('bg-blue-600')
    })

    it('switches to logs tab when clicked', () => {
      render(<LogAnalysisRenderer spec={mockLogAnalysisSpec} />)

      const logsTab = screen.getByRole('button', { name: /원본 로그/i })
      fireEvent.click(logsTab)

      // Logs tab should now be active
      expect(logsTab).toHaveClass('bg-blue-600')

      const summaryTab = screen.getByRole('button', { name: /분석 요약/i })
      expect(summaryTab).not.toHaveClass('bg-blue-600')
    })

    it('switches back to summary tab when clicked', () => {
      render(<LogAnalysisRenderer spec={mockLogAnalysisSpec} />)

      const logsTab = screen.getByRole('button', { name: /원본 로그/i })
      const summaryTab = screen.getByRole('button', { name: /분석 요약/i })

      // Switch to logs tab first
      fireEvent.click(logsTab)
      expect(logsTab).toHaveClass('bg-blue-600')

      // Switch back to summary tab
      fireEvent.click(summaryTab)
      expect(summaryTab).toHaveClass('bg-blue-600')
      expect(logsTab).not.toHaveClass('bg-blue-600')
    })
  })

  describe('Summary Tab Content', () => {
    it('renders markdown summary correctly', () => {
      render(<LogAnalysisRenderer spec={mockLogAnalysisSpec} />)

      // Check markdown headings are rendered (h2 and h3)
      // '분석 요약' appears both in tab button and h2, so use getAllByText
      const summaryElements = screen.getAllByText('분석 요약')
      expect(summaryElements.length).toBeGreaterThanOrEqual(2) // tab + h2

      expect(screen.getByText('주요 발견 사항')).toBeInTheDocument()
      expect(screen.getByText('권장 조치')).toBeInTheDocument()
    })

    it('renders markdown emphasis correctly', () => {
      render(<LogAnalysisRenderer spec={mockLogAnalysisSpec} />)

      // Bold text should be rendered (check for the content)
      expect(screen.getByText(/에러 집중 시간대/)).toBeInTheDocument()
      expect(screen.getByText(/주요 에러 유형/)).toBeInTheDocument()
    })
  })

  describe('Logs Tab Content', () => {
    it('renders log entries when logs tab is active', () => {
      render(<LogAnalysisRenderer spec={mockLogAnalysisSpec} />)

      // Switch to logs tab
      const logsTab = screen.getByRole('button', { name: /원본 로그/i })
      fireEvent.click(logsTab)

      // Check log entries are rendered
      expect(screen.getByText('[PaymentGateway] Connection timeout.')).toBeInTheDocument()
      expect(screen.getByText('[RetryQueue] Scheduled retry in 500ms.')).toBeInTheDocument()
      expect(screen.getByText('[PaymentGateway] Retry 1 initiated.')).toBeInTheDocument()
    })

    it('renders log levels with correct styling', () => {
      render(<LogAnalysisRenderer spec={mockLogAnalysisSpec} />)

      // Switch to logs tab
      const logsTab = screen.getByRole('button', { name: /원본 로그/i })
      fireEvent.click(logsTab)

      // Check for level indicators
      expect(screen.getByText('[ERRO]')).toBeInTheDocument()
      expect(screen.getByText('[WARN]')).toBeInTheDocument()
      expect(screen.getAllByText('[INFO]').length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('[DEBU]')).toBeInTheDocument()
    })

    it('displays correct number of log entries', () => {
      render(<LogAnalysisRenderer spec={mockLogAnalysisSpec} />)

      // Switch to logs tab
      const logsTab = screen.getByRole('button', { name: /원본 로그/i })
      fireEvent.click(logsTab)

      // Footer should show entry count
      expect(screen.getByText('5 lines')).toBeInTheDocument()
    })
  })

  describe('Title and Description', () => {
    it('renders title from spec', () => {
      render(<LogAnalysisRenderer spec={mockLogAnalysisSpec} />)

      expect(screen.getByText('서버 로그 분석 결과')).toBeInTheDocument()
    })

    it('renders description as subtitle', () => {
      render(<LogAnalysisRenderer spec={mockLogAnalysisSpec} />)

      expect(screen.getByText('API 서버 로그 분석')).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles missing timeRange gracefully', () => {
      const specWithoutTimeRange: LogAnalysisRenderSpec = {
        ...mockLogAnalysisSpec,
        log_analysis: {
          ...mockLogAnalysisSpec.log_analysis,
          statistics: {
            totalEntries: 100,
            errorCount: 5,
            warnCount: 10,
          },
        },
      }

      render(<LogAnalysisRenderer spec={specWithoutTimeRange} />)

      expect(screen.getByText('시간 범위')).toBeInTheDocument()
      expect(screen.getByText('-')).toBeInTheDocument()
    })

    it('handles empty entries array', () => {
      const specWithNoEntries: LogAnalysisRenderSpec = {
        ...mockLogAnalysisSpec,
        log_analysis: {
          ...mockLogAnalysisSpec.log_analysis,
          entries: [],
        },
      }

      render(<LogAnalysisRenderer spec={specWithNoEntries} />)

      // Switch to logs tab
      const logsTab = screen.getByRole('button', { name: /원본 로그/i })
      fireEvent.click(logsTab)

      expect(screen.getByText('No log entries found')).toBeInTheDocument()
    })

    it('handles null timestamp in entries', () => {
      const specWithNullTimestamp: LogAnalysisRenderSpec = {
        ...mockLogAnalysisSpec,
        log_analysis: {
          ...mockLogAnalysisSpec.log_analysis,
          entries: [
            { timestamp: null, level: 'ERROR', message: 'Error without timestamp' },
          ],
        },
      }

      render(<LogAnalysisRenderer spec={specWithNullTimestamp} />)

      // Switch to logs tab
      const logsTab = screen.getByRole('button', { name: /원본 로그/i })
      fireEvent.click(logsTab)

      expect(screen.getByText('Error without timestamp')).toBeInTheDocument()
    })
  })
})
