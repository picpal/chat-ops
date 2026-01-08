import React, { useState } from 'react'
import { Icon } from '@/components/common'
import { useChat } from '@/hooks'
import { useChatStore } from '@/store'
import { ICONS } from '@/utils'

const ChatPanel: React.FC = () => {
  const [message, setMessage] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const { sendMessage, isLoading } = useChat()
  const { currentSessionId, sessions } = useChatStore()

  const currentSession = sessions.find((s) => s.id === currentSessionId)
  const hasMessages = currentSession && currentSession.messages.length > 0

  // Hide chat panel when no session is active
  if (!currentSessionId) {
    return null
  }

  const handleSend = () => {
    if (!message.trim() || !currentSessionId) return

    sendMessage({
      message: message.trim(),
      sessionId: currentSessionId,
    })

    setMessage('')
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className={`absolute left-0 right-0 z-30 flex flex-col items-center px-6 pointer-events-none transition-all duration-300 ${
      hasMessages ? 'bottom-0 pb-6' : 'top-[41%] -translate-y-1/2'
    }`}>
      {/* Greeting Message */}
      {!hasMessages && currentSessionId && (
        <div className="text-center mb-8 pointer-events-none">
          <h2 className="text-2xl font-semibold text-stone-800 mb-2">무엇을 도와드릴까요?</h2>
          <p className="text-stone-500 text-sm">결제, 정산, 거래 내역 등 궁금한 것을 물어보세요</p>
        </div>
      )}

      <div className={`w-full max-w-3xl relative z-10 flex flex-col bg-white/95 backdrop-blur-md border-2 shadow-xl rounded-2xl overflow-hidden pointer-events-auto transition-all duration-200 ${
        isFocused
          ? 'border-primary/60 shadow-primary/10'
          : 'border-slate-200/80 shadow-slate-200/50'
      }`}>
        {/* Bot Message Display (optional) */}
        {isLoading && (
          <div className="flex-1 overflow-y-auto p-4 flex flex-row items-start gap-3 w-full">
            <div
              className="shrink-0 bg-center bg-no-repeat bg-cover rounded-full h-8 w-8 ring-2 ring-primary/10 shadow-sm mt-0.5"
              style={{
                backgroundImage:
                  'url("https://lh3.googleusercontent.com/aida-public/AB6AXuBjsEEKehp63EhYOSDmPjuPmVSg0_-Y7gcGwe3SyUh33OnTp-G6F6q3zl-ZGJAjRls4JIxDC-if51KSup19ATjElOJ7h2wvE83XNyYGKU9FYNg0QXtlnxZAAIeGmFsw_OgyUOb8k_wodNw3SWH23Rdpyh3--ku2ZdXsdpI_3RlAnTGEU8qd_yg9pMbEPy6GRA3lqWQq0pQqM7MV5Z5E7MBMj9b2OANfbIfAOJ3Rhf6fcvF0tPSW1Ju2ztCiFr97c1fjH54ibdbMgjYV")',
              }}
            />
            <div className="flex-1 min-w-0 text-sm py-1">
              <span className="text-slate-600">Processing your request...</span>
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="relative flex items-end p-2 transition-all bg-slate-50/30">
          <button
            className="p-2.5 text-slate-400 hover:text-primary hover:bg-slate-50 rounded-xl transition-colors shrink-0"
            title="Attach file"
          >
            <Icon name={ICONS.ADD_CIRCLE} />
          </button>

          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            disabled={!currentSessionId || isLoading}
            className="w-full bg-transparent border-0 text-slate-800 placeholder-slate-400 focus:ring-0 resize-none py-3 px-3 max-h-32 min-h-[48px] leading-relaxed focus:outline-none"
            placeholder={
              currentSessionId
                ? 'Ask about transactions, settlements, or PG status...'
                : 'Create a new analysis to start chatting...'
            }
            rows={1}
          />

          <div className="flex items-center gap-1 shrink-0 pb-0.5 pr-0.5">
            <button
              className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-50 rounded-xl transition-colors"
              title="Voice Input"
            >
              <Icon name={ICONS.MIC} />
            </button>

            <button
              onClick={handleSend}
              disabled={!message.trim() || !currentSessionId || isLoading}
              className="bg-primary hover:bg-blue-600 active:bg-blue-700 text-white p-2.5 rounded-xl transition-colors shadow-sm shadow-blue-500/30 flex items-center justify-center group disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Icon
                name={ICONS.SEND}
                className="group-hover:translate-x-0.5 transition-transform"
              />
            </button>
          </div>
        </div>

        {/* Disclaimer */}
        <div className="bg-slate-50/50 border-t border-slate-200/50">
          <p className="text-center text-[11px] text-slate-400 py-1.5 font-medium opacity-80">
            FinBot can make mistakes. Please verify sensitive financial data.
          </p>
        </div>
      </div>
    </div>
  )
}

export default ChatPanel
