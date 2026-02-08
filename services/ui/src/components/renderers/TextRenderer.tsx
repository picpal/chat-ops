import React, { useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import toast from 'react-hot-toast'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import { TextRenderSpec } from '@/types/renderSpec'
import { Card, Badge, Button, Icon } from '@/components/common'
import { copyToClipboard, cn } from '@/utils'

interface TextRendererProps {
  spec: TextRenderSpec
}

const TextRenderer: React.FC<TextRendererProps> = ({ spec }) => {
  const contentRef = useRef<HTMLDivElement>(null)
  const [isExporting, setIsExporting] = useState(false)

  // Extract text config with fallback for legacy support
  const content = spec.text?.content ?? spec.content ?? ''
  const sections = spec.text?.sections ?? spec.sections
  const isMarkdown = spec.text?.format === 'markdown' || spec.markdown

  const handleCopy = async () => {
    const success = await copyToClipboard(content)
    if (success) {
      toast.success('클립보드에 복사되었습니다')
    } else {
      toast.error('복사에 실패했습니다')
    }
  }

  const handleExportPDF = async () => {
    const element = contentRef.current
    if (!element) {
      toast.error('내보낼 컨텐츠를 찾을 수 없습니다')
      return
    }

    setIsExporting(true)
    try {
      const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff',
      })

      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF('p', 'mm', 'a4')

      const pdfWidth = pdf.internal.pageSize.getWidth()
      const pdfHeight = pdf.internal.pageSize.getHeight()
      const imgWidth = canvas.width
      const imgHeight = canvas.height

      const ratio = Math.min(
        (pdfWidth - 20) / imgWidth,
        (pdfHeight - 20) / imgHeight
      )

      const imgX = 10
      const imgY = 10
      const scaledWidth = imgWidth * ratio
      const scaledHeight = imgHeight * ratio

      pdf.addImage(imgData, 'PNG', imgX, imgY, scaledWidth, scaledHeight)

      const fileName = spec.title
        ? `${spec.title.replace(/[^a-zA-Z0-9가-힣]/g, '_')}.pdf`
        : 'document.pdf'
      pdf.save(fileName)

      toast.success('PDF가 다운로드되었습니다')
    } catch (error) {
      console.error('PDF export error:', error)
      toast.error('PDF 내보내기에 실패했습니다')
    } finally {
      setIsExporting(false)
    }
  }

  // Get section style based on type
  const getSectionStyle = (type: string) => {
    switch (type) {
      case 'success':
        return 'bg-emerald-50 border-emerald-200 text-emerald-800'
      case 'error':
        return 'bg-red-50 border-red-200 text-red-800'
      case 'warning':
        return 'bg-amber-50 border-amber-200 text-amber-800'
      case 'info':
      default:
        return 'bg-blue-50 border-blue-200 text-blue-800'
    }
  }

  const getSectionIcon = (type: string) => {
    switch (type) {
      case 'success':
        return 'check_circle'
      case 'error':
        return 'error'
      case 'warning':
        return 'warning'
      case 'info':
      default:
        return 'info'
    }
  }

  const actions = (
    <>
      <Button variant="secondary" size="sm" icon="content_copy" onClick={handleCopy}>
        Copy
      </Button>
      <Button
        variant="secondary"
        size="sm"
        icon="picture_as_pdf"
        onClick={handleExportPDF}
        disabled={isExporting}
      >
        {isExporting ? 'Exporting...' : 'Export PDF'}
      </Button>
    </>
  )

  return (
    <Card
      title={spec.title}
      subtitle={spec.description}
      icon="description"
      actions={actions}
      className="animate-fade-in-up"
    >
      {/* Main content */}
      <div ref={contentRef}>
        {isMarkdown ? (
          <div className="prose prose-slate prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        ) : (
          <div className="text-slate-700 text-sm whitespace-pre-wrap">{content}</div>
        )}

        {/* Sections */}
        {sections && sections.length > 0 && (
          <div className="mt-6 space-y-4">
            {sections.map((section, idx) => (
              <div
                key={idx}
                className={cn(
                  'border rounded-lg p-4',
                  getSectionStyle(section.type)
                )}
              >
                <div className="flex items-start gap-3">
                  <Icon
                    name={getSectionIcon(section.type)}
                    className="shrink-0 mt-0.5"
                    size="sm"
                  />
                  <div className="flex-1 min-w-0">
                    {section.title && (
                      <h4 className="font-semibold mb-1">{section.title}</h4>
                    )}
                    {isMarkdown ? (
                      <div className="prose prose-sm max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {section.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <p className="text-sm">{section.content}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Completion badge */}
      <div className="mt-6 flex justify-end">
        <Badge variant="success">Complete</Badge>
      </div>
    </Card>
  )
}

export default TextRenderer
