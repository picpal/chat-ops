import { describe, it, expect } from 'vitest'
import { extractRenderSpecText } from './extractRenderSpecText'
import {
  TextRenderSpec,
  TableRenderSpec,
  ChartRenderSpec,
  LogAnalysisRenderSpec,
  ClarificationRenderSpec,
  LogRenderSpec,
  CompositeRenderSpec,
  FilterLocalRenderSpec,
  AggregateLocalRenderSpec,
  DownloadRenderSpec,
  RenderSpec,
} from '@/types/renderSpec'
import { QueryResult } from '@/types/queryResult'

const BASE = { requestId: 'req-1' }

describe('extractRenderSpecText', () => {
  // ─── text ────────────────────────────────────────────────────────────────

  describe('text 타입', () => {
    it('text.content를 반환한다', () => {
      // Arrange
      const renderSpec: TextRenderSpec = {
        ...BASE,
        type: 'text',
        text: { content: '안녕하세요' },
      }

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toContain('안녕하세요')
    })

    it('레거시 직접 content 프로퍼티를 사용한다', () => {
      // Arrange
      const renderSpec: TextRenderSpec = {
        ...BASE,
        type: 'text',
        content: '레거시 콘텐츠',
      }

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toContain('레거시 콘텐츠')
    })

    it('sections가 있을 때 title 포함 형태로 추가된다', () => {
      // Arrange
      const renderSpec: TextRenderSpec = {
        ...BASE,
        type: 'text',
        text: {
          content: '메인 내용',
          sections: [
            { type: 'info', title: '제목', content: '섹션 내용' },
          ],
        },
      }

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toContain('메인 내용')
      expect(result).toContain('[INFO] 제목: 섹션 내용')
    })

    it('sections에 title이 없으면 [TYPE] content 형태로 추가된다', () => {
      // Arrange
      const renderSpec: TextRenderSpec = {
        ...BASE,
        type: 'text',
        text: {
          content: '메인',
          sections: [
            { type: 'warning', content: '경고 메시지' },
          ],
        },
      }

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toContain('[WARNING] 경고 메시지')
    })
  })

  // ─── table ───────────────────────────────────────────────────────────────

  describe('table 타입', () => {
    const baseTableSpec: TableRenderSpec = {
      ...BASE,
      type: 'table',
      title: '결제 목록',
      table: {
        columns: [
          { key: 'id', label: 'ID', type: 'string' },
          { key: 'amount', label: '금액', type: 'currency' },
        ],
        dataRef: 'data.rows',
        data: [
          { id: 'p-1', amount: 10000 },
          { id: 'p-2', amount: 20000 },
        ],
      },
    }

    it('인라인 data가 있을 때 헤더와 행을 반환한다', () => {
      // Arrange & Act
      const result = extractRenderSpecText(baseTableSpec)

      // Assert
      expect(result).toContain('[표] 결제 목록')
      expect(result).toContain('ID\t금액')
      expect(result).toContain('p-1\t10000')
      expect(result).toContain('p-2\t20000')
    })

    it('queryResult.data.rows에서 데이터를 참조한다 (인라인 data 없을 때)', () => {
      // Arrange
      const renderSpec: TableRenderSpec = {
        ...BASE,
        type: 'table',
        title: '매출 현황',
        table: {
          columns: [
            { key: 'merchant', label: '가맹점', type: 'string' },
            { key: 'total', label: '합계', type: 'currency' },
          ],
          dataRef: 'data.rows',
        },
      }
      const queryResult: QueryResult = {
        requestId: 'req-1',
        status: 'success',
        data: {
          rows: [
            { merchant: '가맹점A', total: 500000 },
            { merchant: '가맹점B', total: 300000 },
          ],
        },
        metadata: { executionTimeMs: 10, rowsReturned: 2 },
      }

      // Act
      const result = extractRenderSpecText(renderSpec, queryResult)

      // Assert
      expect(result).toContain('가맹점\t합계')
      expect(result).toContain('가맹점A\t500000')
    })

    it('행 수가 20건을 초과하면 "(외 N건)" 표시를 추가한다', () => {
      // Arrange
      const rows = Array.from({ length: 25 }, (_, i) => ({ id: `p-${i}`, amount: i * 1000 }))
      const renderSpec: TableRenderSpec = {
        ...BASE,
        type: 'table',
        title: '대량 데이터',
        table: {
          columns: [
            { key: 'id', label: 'ID', type: 'string' },
            { key: 'amount', label: '금액', type: 'currency' },
          ],
          dataRef: 'data.rows',
          data: rows,
        },
      }

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toContain('(외 5건)')
      const lines = result.split('\n')
      // 헤더 1줄 + 타이틀 1줄 + 20줄 데이터 + 1줄 초과표시 = 23줄
      const dataLines = lines.filter(l => l.startsWith('p-'))
      expect(dataLines).toHaveLength(20)
    })
  })

  // ─── chart ───────────────────────────────────────────────────────────────

  describe('chart 타입', () => {
    it('제목, 인사이트, 요약통계를 포함해 반환한다', () => {
      // Arrange
      const renderSpec: ChartRenderSpec = {
        ...BASE,
        type: 'chart',
        title: '월별 매출',
        chart: {
          chartType: 'bar',
          insight: { content: '3월 매출이 가장 높습니다', source: 'llm' },
          summaryStats: {
            source: 'llm',
            items: [
              { key: 'total', label: '총 매출', value: '1,000,000원', type: 'currency' },
              { key: 'avg', label: '월 평균', value: '333,333원', type: 'currency' },
            ],
          },
        },
      }

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toContain('[차트] 월별 매출')
      expect(result).toContain('인사이트: 3월 매출이 가장 높습니다')
      expect(result).toContain('- 총 매출: 1,000,000원')
      expect(result).toContain('- 월 평균: 333,333원')
    })

    it('인사이트와 요약통계가 없을 때 제목만 반환한다', () => {
      // Arrange
      const renderSpec: ChartRenderSpec = {
        ...BASE,
        type: 'chart',
        title: '간단 차트',
        chart: { chartType: 'pie' },
      }

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toBe('[차트] 간단 차트')
    })
  })

  // ─── log_analysis ─────────────────────────────────────────────────────────

  describe('log_analysis 타입', () => {
    it('요약과 통계를 포함해 반환한다', () => {
      // Arrange
      const renderSpec: LogAnalysisRenderSpec = {
        ...BASE,
        type: 'log_analysis',
        title: '오늘의 로그 분석',
        log_analysis: {
          summary: '에러가 3건 발생했습니다.',
          statistics: { totalEntries: 100, errorCount: 3, warnCount: 10 },
          entries: [],
        },
      }

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toContain('[로그 분석] 오늘의 로그 분석')
      expect(result).toContain('에러가 3건 발생했습니다.')
      expect(result).toContain('통계: 전체 100건 | 오류 3건 | 경고 10건')
    })
  })

  // ─── clarification ───────────────────────────────────────────────────────

  describe('clarification 타입', () => {
    it('질문과 번호 목록 선택지를 반환한다', () => {
      // Arrange
      const renderSpec: ClarificationRenderSpec = {
        type: 'clarification',
        clarification: {
          question: '조회 기간을 선택해주세요.',
          options: ['오늘', '이번 주', '이번 달'],
        },
      }

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toContain('[확인 질문] 조회 기간을 선택해주세요.')
      expect(result).toContain('1. 오늘')
      expect(result).toContain('2. 이번 주')
      expect(result).toContain('3. 이번 달')
    })
  })

  // ─── log ─────────────────────────────────────────────────────────────────

  describe('log 타입', () => {
    it('제목과 설명을 반환한다', () => {
      // Arrange
      const renderSpec: LogRenderSpec = {
        ...BASE,
        type: 'log',
        title: '서버 로그',
        description: '최근 1시간 로그',
        log: { dataRef: 'data.rows' },
      }

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toContain('[로그] 서버 로그')
      expect(result).toContain('최근 1시간 로그')
    })

    it('제목 없이 [로그] 접두사만 반환한다', () => {
      // Arrange
      const renderSpec: LogRenderSpec = {
        ...BASE,
        type: 'log',
        log: { dataRef: 'data.rows' },
      }

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toBe('[로그]')
    })
  })

  // ─── composite ───────────────────────────────────────────────────────────

  describe('composite 타입', () => {
    it('하위 컴포넌트들을 재귀적으로 처리하여 결합한다', () => {
      // Arrange
      const renderSpec: CompositeRenderSpec = {
        ...BASE,
        type: 'composite',
        components: [
          {
            ...BASE,
            type: 'text',
            text: { content: '첫 번째 내용' },
          } as TextRenderSpec,
          {
            ...BASE,
            type: 'text',
            text: { content: '두 번째 내용' },
          } as TextRenderSpec,
        ],
      }

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toContain('첫 번째 내용')
      expect(result).toContain('두 번째 내용')
    })

    it('depth >= 3이면 "[복합 컴포넌트]" 문자열을 반환한다', () => {
      // Arrange
      const innerSpec: TextRenderSpec = {
        ...BASE,
        type: 'text',
        text: { content: '깊은 내용' },
      }
      const renderSpec: CompositeRenderSpec = {
        ...BASE,
        type: 'composite',
        components: [innerSpec],
      }

      // Act - depth=3으로 직접 호출
      const result = extractRenderSpecText(renderSpec, undefined, 3)

      // Assert
      expect(result).toBe('[복합 컴포넌트]')
    })

    it('depth 3 중첩 도달 시 재귀를 멈추고 "[복합 컴포넌트]"를 반환한다', () => {
      // Arrange - 4단계 중첩 composite
      const level3: CompositeRenderSpec = {
        ...BASE,
        type: 'composite',
        components: [
          { ...BASE, type: 'text', text: { content: '깊은 텍스트' } } as TextRenderSpec,
        ],
      }
      const level2: CompositeRenderSpec = {
        ...BASE,
        type: 'composite',
        components: [level3],
      }
      const level1: CompositeRenderSpec = {
        ...BASE,
        type: 'composite',
        components: [level2],
      }
      const root: CompositeRenderSpec = {
        ...BASE,
        type: 'composite',
        components: [level1],
      }

      // Act
      const result = extractRenderSpecText(root)

      // Assert
      // depth=0 → root 처리, depth=1 → level1, depth=2 → level2, depth=3 → level3 → "[복합 컴포넌트]"
      expect(result).toContain('[복합 컴포넌트]')
      expect(result).not.toContain('깊은 텍스트')
    })
  })

  // ─── filter_local ─────────────────────────────────────────────────────────

  describe('filter_local 타입', () => {
    it('title이 있으면 [필터 적용] + title을 반환한다', () => {
      // Arrange
      const renderSpec: FilterLocalRenderSpec = {
        type: 'filter_local',
        title: '상태 필터',
        filter: [{ field: 'status', operator: 'eq', value: 'DONE' }],
        targetResultIndex: 0,
      }

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toBe('[필터 적용] 상태 필터')
    })

    it('title이 없고 description이 있으면 description을 사용한다', () => {
      // Arrange
      const renderSpec: FilterLocalRenderSpec = {
        type: 'filter_local',
        description: '필터 설명',
        filter: [{ field: 'status', operator: 'eq', value: 'DONE' }],
        targetResultIndex: 0,
      }

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toBe('[필터 적용] 필터 설명')
    })
  })

  // ─── aggregate_local ──────────────────────────────────────────────────────

  describe('aggregate_local 타입', () => {
    it('[집계 결과] + title을 반환한다', () => {
      // Arrange
      const renderSpec: AggregateLocalRenderSpec = {
        type: 'aggregate_local',
        title: '합계 집계',
        aggregations: [{ function: 'sum', field: 'amount' }],
        targetResultIndex: 0,
      }

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toBe('[집계 결과] 합계 집계')
    })
  })

  // ─── download ─────────────────────────────────────────────────────────────

  describe('download 타입', () => {
    it('download.message를 우선적으로 반환한다', () => {
      // Arrange
      const renderSpec: DownloadRenderSpec = {
        type: 'download',
        title: '다운로드 타이틀',
        download: {
          totalRows: 10000,
          maxDisplayRows: 1000,
          message: '데이터가 너무 많아 파일로 다운로드하세요.',
          sql: 'SELECT *',
          formats: ['csv', 'excel'],
        },
      }

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toBe('[다운로드] 데이터가 너무 많아 파일로 다운로드하세요.')
    })

    it('download.message 없으면 title을 사용한다', () => {
      // Arrange - message를 빈 문자열로 처리하기 위해 타입 어설션 사용
      const renderSpec = {
        type: 'download' as const,
        title: '파일 다운로드',
        download: {
          totalRows: 10000,
          maxDisplayRows: 1000,
          message: '',
          sql: 'SELECT *',
          formats: ['csv'] as ('csv' | 'excel')[],
        },
      } as DownloadRenderSpec

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toBe('[다운로드] 파일 다운로드')
    })
  })

  // ─── fallback / unknown ───────────────────────────────────────────────────

  describe('알 수 없는 타입 fallback', () => {
    it('title이 있으면 title을 반환한다', () => {
      // Arrange
      const renderSpec = {
        type: 'unknown_type',
        requestId: 'req-1',
        title: '알 수 없는 컴포넌트',
      } as unknown as RenderSpec

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toBe('알 수 없는 컴포넌트')
    })

    it('title이 없으면 description을 반환한다', () => {
      // Arrange
      const renderSpec = {
        type: 'unknown_type',
        requestId: 'req-1',
        description: '설명만 있음',
      } as unknown as RenderSpec

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toBe('설명만 있음')
    })

    it('title과 description 모두 없으면 빈 문자열을 반환한다', () => {
      // Arrange
      const renderSpec = {
        type: 'unknown_type',
        requestId: 'req-1',
      } as unknown as RenderSpec

      // Act
      const result = extractRenderSpecText(renderSpec)

      // Assert
      expect(result).toBe('')
    })
  })
})
