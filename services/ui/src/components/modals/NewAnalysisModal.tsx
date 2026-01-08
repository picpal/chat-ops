import React, { useState } from 'react'
import { useModal } from '@/hooks'
import { useChatStore } from '@/store'
import { Icon, Button } from '@/components/common'
import { ICONS } from '@/utils'

const NewAnalysisModal: React.FC = () => {
  const { isOpen, type, close } = useModal()
  const { createSession } = useChatStore()
  const [title, setTitle] = useState('')

  if (!isOpen || type !== 'newAnalysis') return null

  const handleConfirm = () => {
    if (!title.trim()) return

    createSession(title.trim())
    setTitle('')
    close()
  }

  const handleClose = () => {
    setTitle('')
    close()
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleConfirm()
    }
    if (e.key === 'Escape') {
      handleClose()
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-sm bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden animate-fade-in-up transform transition-all">
        {/* Content */}
        <div className="px-6 py-6">
          {/* Header */}
          <div className="flex justify-between items-start mb-6">
            <div>
              <h3 className="text-lg font-bold text-slate-900">New Analysis</h3>
              <p className="text-xs text-slate-500 mt-1">
                Start a new session with FinBot
              </p>
            </div>
            <button
              onClick={handleClose}
              className="text-slate-400 hover:text-slate-600 transition-colors p-1 rounded-full hover:bg-slate-100"
            >
              <Icon name={ICONS.CLOSE} size="sm" />
            </button>
          </div>

          {/* Form */}
          <div className="space-y-6">
            <div>
              <label
                htmlFor="analysis-title"
                className="block text-sm font-semibold text-slate-700 mb-2"
              >
                Title
              </label>
              <input
                id="analysis-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="e.g., Weekly Settlement Review"
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary shadow-sm transition-all"
                autoFocus
              />
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
              <Button
                onClick={handleClose}
                variant="secondary"
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={handleConfirm}
                variant="primary"
                className="flex-1"
                disabled={!title.trim()}
              >
                Confirm
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default NewAnalysisModal
