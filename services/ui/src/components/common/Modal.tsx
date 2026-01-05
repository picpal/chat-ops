import React, { useEffect, useCallback } from 'react'
import { Icon } from '@/components/common'
import { ICONS } from '@/utils'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  subtitle?: string
  children: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
  showCloseButton?: boolean
  showGradientBar?: boolean
  className?: string
}

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-4xl',
  xl: 'max-w-6xl',
  full: 'max-w-[95vw] max-h-[95vh]',
}

const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  size = 'md',
  showCloseButton = true,
  showGradientBar = true,
  className = '',
}) => {
  // ESC key handler
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    },
    [onClose]
  )

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [isOpen, handleKeyDown])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal Container */}
      <div
        className={`relative w-full ${sizeClasses[size]} bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden animate-fade-in-up transform transition-all flex flex-col ${className}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Gradient Header Bar */}
        {showGradientBar && (
          <div className="h-1.5 w-full bg-gradient-to-r from-primary to-blue-400 flex-shrink-0" />
        )}

        {/* Close Button */}
        {showCloseButton && (
          <button
            onClick={onClose}
            className="absolute top-4 right-4 z-10 w-8 h-8 bg-white rounded-full shadow-lg flex items-center justify-center hover:bg-slate-50 transition-colors border border-slate-200"
          >
            <Icon name={ICONS.CLOSE} size="sm" className="text-slate-600" />
          </button>
        )}

        {/* Header (optional) */}
        {(title || subtitle) && (
          <div className="px-6 pt-5 pb-4 border-b border-slate-100 flex-shrink-0">
            {title && (
              <h2 className="text-lg font-bold text-slate-900 pr-10">{title}</h2>
            )}
            {subtitle && (
              <p className="text-sm text-slate-500 mt-1">{subtitle}</p>
            )}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-auto">{children}</div>
      </div>
    </div>
  )
}

export default Modal
