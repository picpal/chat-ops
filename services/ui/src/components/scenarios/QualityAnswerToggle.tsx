import { useQualityAnswerRagStatus, useUpdateQualityAnswerRag } from '@/hooks/useSettings'

export function QualityAnswerToggle() {
  const { data: status, isLoading, error } = useQualityAnswerRagStatus()
  const updateMutation = useUpdateQualityAnswerRag()

  const handleToggle = () => {
    if (status) {
      updateMutation.mutate({ enabled: !status.enabled })
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-3">
        <div className="w-10 h-5 bg-gray-200 rounded-full animate-pulse" />
        <span className="text-sm text-gray-400">로딩 중...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-sm text-red-500">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span>설정 로드 실패</span>
      </div>
    )
  }

  const enabled = status?.enabled ?? false
  const storedCount = status?.storedCount ?? 0

  return (
    <div className="flex items-center gap-4">
      {/* 토글 스위치 */}
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        onClick={handleToggle}
        disabled={updateMutation.isPending}
        className={`
          relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent
          transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          ${enabled ? 'bg-blue-600' : 'bg-gray-200'}
          ${updateMutation.isPending ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <span
          className={`
            pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0
            transition duration-200 ease-in-out
            ${enabled ? 'translate-x-5' : 'translate-x-0'}
          `}
        />
      </button>

      {/* 라벨 및 설명 */}
      <div className="flex flex-col">
        <span className="text-sm font-medium text-gray-700">
          Quality Answer RAG
        </span>
        <span className="text-xs text-gray-500">
          {enabled ? (
            <>
              고품질 답변 참고 활성화
              {storedCount > 0 && (
                <span className="ml-1 text-blue-600">({storedCount}개 저장됨)</span>
              )}
            </>
          ) : (
            '비활성화됨'
          )}
        </span>
      </div>

      {/* 업데이트 상태 표시 */}
      {updateMutation.isPending && (
        <svg className="w-4 h-4 animate-spin text-blue-500" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      )}
    </div>
  )
}
