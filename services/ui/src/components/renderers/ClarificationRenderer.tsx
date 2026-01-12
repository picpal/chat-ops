import React, { useState } from 'react'
import { Icon } from '@/components/common'
import { ClarificationRenderSpec } from '@/types/renderSpec'

interface ClarificationRendererProps {
  spec: ClarificationRenderSpec
  onOptionSelect?: (optionIndex: number, option: string, metadata?: ClarificationRenderSpec['metadata']) => void
}

const ClarificationRenderer: React.FC<ClarificationRendererProps> = ({
  spec,
  onOptionSelect,
}) => {
  const { clarification, metadata } = spec
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  const handleOptionClick = (index: number, option: string) => {
    if (isProcessing) return

    setSelectedIndex(index)
    setIsProcessing(true)

    if (onOptionSelect) {
      onOptionSelect(index, option, metadata)
    }
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <Icon name="help" className="text-blue-600 flex-shrink-0" size="md" />
        <div className="flex-1">
          <p className="text-blue-900 font-medium mb-3">
            {clarification.question}
          </p>

          {clarification.options && clarification.options.length > 0 && (
            <div className="flex flex-col gap-2">
              {clarification.options.map((option, index) => {
                const isSelected = selectedIndex === index
                const isDisabled = isProcessing && !isSelected

                return (
                  <button
                    key={index}
                    onClick={() => handleOptionClick(index, option)}
                    disabled={isDisabled}
                    className={`
                      w-full text-left px-4 py-3 rounded-lg text-sm font-medium
                      transition-all duration-200 border-2
                      ${isSelected
                        ? 'bg-blue-600 border-blue-600 text-white shadow-md'
                        : isDisabled
                          ? 'bg-slate-50 border-slate-200 text-slate-400 cursor-not-allowed'
                          : 'bg-white border-blue-200 text-blue-700 hover:bg-blue-100 hover:border-blue-400 hover:shadow-sm cursor-pointer'
                      }
                    `}
                  >
                    <div className="flex items-center gap-3">
                      <span className={`
                        flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
                        ${isSelected
                          ? 'bg-white text-blue-600'
                          : 'bg-blue-100 text-blue-600'
                        }
                      `}>
                        {index + 1}
                      </span>
                      <span className="flex-1">{option}</span>
                      {isSelected && isProcessing && (
                        <span className="flex-shrink-0 text-xs opacity-80">
                          처리 중...
                        </span>
                      )}
                    </div>
                  </button>
                )
              })}
            </div>
          )}

          {!isProcessing && (
            <p className="text-xs text-blue-600 mt-3">
              선택하시거나 직접 입력해주세요.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default ClarificationRenderer
