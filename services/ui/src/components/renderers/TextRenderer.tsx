import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { TextRenderSpec } from '@/types/renderSpec'
import { Card, Badge, Button, Icon } from '@/components/common'
import { copyToClipboard, cn } from '@/utils'

interface TextRendererProps {
  spec: TextRenderSpec
}

const TextRenderer: React.FC<TextRendererProps> = ({ spec }) => {
  const handleCopy = async () => {
    await copyToClipboard(spec.content)
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
      <Button variant="secondary" size="sm" icon="picture_as_pdf">
        Export PDF
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
      {spec.markdown ? (
        <div className="prose prose-slate prose-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{spec.content}</ReactMarkdown>
        </div>
      ) : (
        <div className="text-slate-700 text-sm whitespace-pre-wrap">{spec.content}</div>
      )}

      {/* Sections */}
      {spec.sections && spec.sections.length > 0 && (
        <div className="mt-6 space-y-4">
          {spec.sections.map((section, idx) => (
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
                  {spec.markdown ? (
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

      {/* Completion badge */}
      <div className="mt-6 flex justify-end">
        <Badge variant="success">Complete</Badge>
      </div>
    </Card>
  )
}

export default TextRenderer
