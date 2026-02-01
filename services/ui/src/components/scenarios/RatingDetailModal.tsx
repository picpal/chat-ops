import { useState, useEffect } from 'react'
import StarRating from '@/components/common/StarRating'
import { useRatingContext, useUpdateFeedback } from '@/hooks/useRatingsAnalytics'

interface RatingDetailModalProps {
  requestId: string | null
  onClose: () => void
}

export function RatingDetailModal({ requestId, onClose }: RatingDetailModalProps) {
  const { data, isLoading } = useRatingContext(requestId)
  const updateFeedback = useUpdateFeedback()
  const [feedback, setFeedback] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data?.feedback) {
      setFeedback(data.feedback)
    } else {
      setFeedback('')
    }
    setSaved(false)
  }, [data])

  if (!requestId) return null

  const handleSave = () => {
    if (!requestId) return
    updateFeedback.mutate(
      { requestId, feedback },
      {
        onSuccess: () => {
          setSaved(true)
          setTimeout(() => setSaved(false), 2000)
        },
      },
    )
  }

  const conversations = data?.conversations ?? []
  const lastIndex = conversations.length - 1

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-900">
              {isLoading ? '로딩 중...' : data?.sessionTitle || '평가 상세'}
            </h2>
            {data && <StarRating rating={data.rating} readonly size="sm" />}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <span className="material-symbols-outlined" style={{ fontSize: 22 }}>close</span>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {isLoading ? (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="space-y-2">
                  <div className="h-4 w-3/4 bg-gray-200 rounded animate-pulse" />
                  <div className="h-4 w-full bg-gray-100 rounded animate-pulse" />
                </div>
              ))}
            </div>
          ) : conversations.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-8">대화 이력이 없습니다</p>
          ) : (
            conversations.map((conv, idx) => {
              const isRated = idx === lastIndex
              return (
                <div
                  key={idx}
                  className={`rounded-lg border p-4 ${
                    isRated ? 'border-amber-300 bg-amber-50/50' : 'border-gray-200'
                  }`}
                >
                  {isRated && (
                    <span className="inline-block text-xs font-medium text-amber-600 bg-amber-100 px-2 py-0.5 rounded mb-2">
                      평가 대상
                    </span>
                  )}
                  {/* User question */}
                  <div className="flex items-start gap-2 mb-2">
                    <span
                      className="material-symbols-outlined text-blue-500 mt-0.5"
                      style={{ fontSize: 18, fontVariationSettings: "'FILL' 1" }}
                    >
                      person
                    </span>
                    <p className="text-sm text-gray-800">{conv.userQuestion}</p>
                  </div>
                  {/* AI response */}
                  <div className="flex items-start gap-2">
                    <span
                      className="material-symbols-outlined text-purple-500 mt-0.5"
                      style={{ fontSize: 18, fontVariationSettings: "'FILL' 1" }}
                    >
                      smart_toy
                    </span>
                    <p className="text-sm text-gray-600 whitespace-pre-wrap">{conv.aiResponse}</p>
                  </div>
                  {conv.createdAt && (
                    <p className="text-xs text-gray-400 mt-2 text-right">
                      {new Date(conv.createdAt).toLocaleString('ko-KR')}
                    </p>
                  )}
                </div>
              )
            })
          )}
        </div>

        {/* Feedback section */}
        <div className="border-t px-6 py-4 space-y-3">
          <label className="text-sm font-medium text-gray-700">피드백</label>
          <textarea
            className="w-full border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-300 focus:border-blue-400"
            rows={3}
            placeholder="피드백을 입력하세요..."
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
          />
          <div className="flex items-center justify-end gap-2">
            {saved && <span className="text-xs text-green-600">저장되었습니다</span>}
            <button
              onClick={handleSave}
              disabled={updateFeedback.isPending}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {updateFeedback.isPending ? '저장 중...' : '저장'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
