/**
 * 로그 분석 설정 페이지 컴포넌트
 */

import { useState } from 'react'
import {
  useLogSettings,
  useUpdateLogSettings,
  useLogPaths,
  useAddLogPath,
  useUpdateLogPath,
  useDeleteLogPath,
  useTestLogPath,
} from '@/hooks/useLogSettings'
import type { LogPath, LogPathCreate, LogPathUpdate, PathTestResult } from '@/types/logSettings'
import { LogPathForm } from './LogPathForm'

export function LogSettingsPage() {
  const { data: settings, isLoading: settingsLoading } = useLogSettings()
  const { data: paths, isLoading: pathsLoading } = useLogPaths()

  const updateSettings = useUpdateLogSettings()
  const addPath = useAddLogPath()
  const updatePath = useUpdateLogPath()
  const deletePath = useDeleteLogPath()
  const testPath = useTestLogPath()

  const [showForm, setShowForm] = useState(false)
  const [editingPath, setEditingPath] = useState<LogPath | null>(null)
  const [testResults, setTestResults] = useState<Record<string, PathTestResult>>({})

  const handleToggleEnabled = () => {
    if (!settings) return
    updateSettings.mutate({ enabled: !settings.enabled })
  }

  const handleToggleMasking = () => {
    if (!settings) return
    updateSettings.mutate({
      masking: { ...settings.masking, enabled: !settings.masking.enabled },
    })
  }

  const handleAddPath = (data: LogPathCreate | LogPathUpdate) => {
    addPath.mutate(data as LogPathCreate, {
      onSuccess: () => {
        setShowForm(false)
      },
    })
  }

  const handleUpdatePath = (data: LogPathCreate | LogPathUpdate) => {
    if (!editingPath) return
    updatePath.mutate(
      { pathId: editingPath.id, data: data as LogPathUpdate },
      {
        onSuccess: () => {
          setEditingPath(null)
        },
      }
    )
  }

  const handleDeletePath = (pathId: string) => {
    if (confirm('이 로그 경로를 삭제하시겠습니까?')) {
      deletePath.mutate(pathId)
    }
  }

  const handleTestPath = async (pathId: string) => {
    const result = await testPath.mutateAsync(pathId)
    setTestResults((prev) => ({ ...prev, [pathId]: result }))
  }

  if (settingsLoading || pathsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <h1 className="text-2xl font-bold text-gray-900">로그 분석 설정</h1>
          <p className="mt-1 text-sm text-gray-500">
            서버 로그 분석 기능의 경로 및 옵션을 관리합니다
          </p>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* 기본 설정 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-medium mb-4">기본 설정</h2>

          <div className="space-y-4">
            {/* 로그 분석 ON/OFF */}
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">로그 분석 기능</p>
                <p className="text-sm text-gray-500">
                  채팅에서 서버 로그 분석 기능을 사용합니다
                </p>
              </div>
              <button
                onClick={handleToggleEnabled}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings?.enabled ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings?.enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* 민감정보 마스킹 ON/OFF */}
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">민감정보 마스킹</p>
                <p className="text-sm text-gray-500">
                  API 키, 비밀번호 등 민감정보를 자동으로 마스킹합니다
                </p>
              </div>
              <button
                onClick={handleToggleMasking}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings?.masking.enabled ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings?.masking.enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* 로그 경로 목록 */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium">로그 경로</h2>
            <button
              onClick={() => setShowForm(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              + 경로 추가
            </button>
          </div>

          {/* 경로 추가 폼 */}
          {showForm && (
            <div className="mb-4">
              <LogPathForm
                onSubmit={handleAddPath}
                onCancel={() => setShowForm(false)}
                isLoading={addPath.isPending}
              />
            </div>
          )}

          {/* 경로 수정 폼 */}
          {editingPath && (
            <div className="mb-4">
              <LogPathForm
                path={editingPath}
                onSubmit={handleUpdatePath}
                onCancel={() => setEditingPath(null)}
                isLoading={updatePath.isPending}
              />
            </div>
          )}

          {/* 경로 목록 */}
          {paths && paths.length > 0 ? (
            <div className="space-y-3">
              {paths.map((path) => (
                <div
                  key={path.id}
                  className={`p-4 border rounded-lg ${
                    path.enabled ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-gray-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{path.name}</p>
                      <p className="text-sm text-gray-600 font-mono">{path.path}</p>
                      <span
                        className={`text-xs ${
                          path.enabled ? 'text-green-600' : 'text-gray-400'
                        }`}
                      >
                        {path.enabled ? '● 활성' : '○ 비활성'}
                      </span>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleTestPath(path.id)}
                        disabled={testPath.isPending}
                        className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
                      >
                        테스트
                      </button>
                      <button
                        onClick={() => setEditingPath(path)}
                        className="px-3 py-1 text-sm bg-blue-100 text-blue-700 hover:bg-blue-200 rounded"
                      >
                        수정
                      </button>
                      <button
                        onClick={() => handleDeletePath(path.id)}
                        className="px-3 py-1 text-sm bg-red-100 text-red-700 hover:bg-red-200 rounded"
                      >
                        삭제
                      </button>
                    </div>
                  </div>

                  {/* 테스트 결과 표시 */}
                  {testResults[path.id] && (
                    <div
                      className={`mt-2 p-2 rounded text-sm ${
                        testResults[path.id].success
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {testResults[path.id].message}
                      {testResults[path.id].fileSize !== undefined && (
                        <span className="ml-2">
                          ({(testResults[path.id].fileSize! / 1024).toFixed(1)} KB)
                        </span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">
              등록된 로그 경로가 없습니다. 위 버튼을 눌러 추가하세요.
            </p>
          )}
        </div>
      </main>
    </div>
  )
}
