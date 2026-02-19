/**
 * 로그 경로 추가/편집 폼 컴포넌트
 */

import React, { useState } from 'react'
import type { LogPath, LogPathCreate, LogPathUpdate } from '@/types/logSettings'

interface LogPathFormProps {
  path?: LogPath
  onSubmit: (data: LogPathCreate | LogPathUpdate) => void
  onCancel: () => void
  isLoading?: boolean
}

export function LogPathForm({ path, onSubmit, onCancel, isLoading }: LogPathFormProps) {
  const [name, setName] = useState(path?.name || '')
  const [logPath, setLogPath] = useState(path?.path || '')
  const [enabled, setEnabled] = useState(path?.enabled ?? true)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      name,
      path: logPath,
      enabled,
    })
  }

  const isEdit = !!path

  return (
    <form onSubmit={handleSubmit} className="space-y-4 p-4 bg-gray-50 rounded-lg">
      <h3 className="text-lg font-medium">
        {isEdit ? '로그 경로 수정' : '로그 경로 추가'}
      </h3>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          표시 이름
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="예: 메인 서버 로그"
          required
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          로그 파일 경로
        </label>
        <input
          type="text"
          value={logPath}
          onChange={(e) => setLogPath(e.target.value)}
          placeholder="예: /logs/app.log"
          required
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
        />
        <p className="text-xs text-gray-500 mt-1">
          Docker 컨테이너 내부 경로 (예: /logs/...)
        </p>
      </div>

      <div className="flex items-center">
        <input
          type="checkbox"
          id="enabled"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          className="h-4 w-4 text-blue-600 rounded border-gray-300"
        />
        <label htmlFor="enabled" className="ml-2 text-sm text-gray-700">
          활성화
        </label>
      </div>

      <div className="flex space-x-2">
        <button
          type="submit"
          disabled={isLoading}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {isLoading ? '저장 중...' : isEdit ? '수정' : '추가'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
        >
          취소
        </button>
      </div>
    </form>
  )
}
