import React, { useState } from 'react'
import { DownloadRenderSpec } from '@/types/renderSpec'
import { Card, Button, Icon } from '@/components/common'

interface DownloadRendererProps {
  spec: DownloadRenderSpec
}

const DownloadRenderer: React.FC<DownloadRendererProps> = ({ spec }) => {
  const { download } = spec
  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  const handleDownload = async (format: 'csv' | 'excel') => {
    setIsDownloading(true)
    setDownloadError(null)

    try {
      const response = await fetch('/api/v1/chat/download', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sql: download.sql,
          format,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Download failed: ${response.status}`)
      }

      // Blob으로 변환
      const blob = await response.blob()

      // 파일명 추출 (Content-Disposition 헤더에서)
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `query_result.${format === 'csv' ? 'csv' : 'xlsx'}`
      if (contentDisposition) {
        const match = contentDisposition.match(/filename[^;=\n]*=(['"]?)([^'"\n;]*)\1/)
        if (match && match[2]) {
          filename = match[2]
        }
      }

      // 다운로드 트리거
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

    } catch (error) {
      console.error('Download failed:', error)
      setDownloadError(error instanceof Error ? error.message : 'Download failed')
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <Card
      title={spec.title || '대용량 데이터 조회'}
      icon="cloud_download"
      className="animate-fade-in-up"
    >
      <div className="text-center py-8">
        {/* 아이콘 */}
        <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
          <Icon name="database" size="lg" className="text-blue-600" />
        </div>

        {/* 조회 결과 건수 */}
        <p className="text-2xl font-bold text-slate-800 mb-2">
          {download.totalRows.toLocaleString()}건
        </p>

        {/* 안내 메시지 */}
        <p className="text-slate-500 mb-6 max-w-md mx-auto">
          {download.message}
        </p>

        {/* 에러 메시지 */}
        {downloadError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            <Icon name="error" size="sm" className="inline mr-2" />
            {downloadError}
          </div>
        )}

        {/* 다운로드 버튼 */}
        <div className="flex gap-3 justify-center">
          {download.formats.includes('csv') && (
            <Button
              variant="primary"
              size="lg"
              icon="download"
              onClick={() => handleDownload('csv')}
              disabled={isDownloading}
            >
              {isDownloading ? '다운로드 중...' : 'CSV 다운로드'}
            </Button>
          )}
          {download.formats.includes('excel') && (
            <Button
              variant="secondary"
              size="lg"
              icon="table_view"
              onClick={() => handleDownload('excel')}
              disabled={isDownloading}
            >
              Excel 다운로드
            </Button>
          )}
        </div>

        {/* 추가 안내 */}
        <p className="mt-6 text-xs text-slate-400">
          다운로드 시 전체 {download.totalRows.toLocaleString()}건의 데이터가 포함됩니다
        </p>
      </div>
    </Card>
  )
}

export default DownloadRenderer
