/**
 * 문서 생성/수정 폼 모달 컴포넌트
 */
import { useState, useEffect, useRef } from 'react'
import { useDocumentStore } from '@/store/documentStore'
import { useDocument, useCreateDocument, useUpdateDocument, useUploadDocument } from '@/hooks/useDocuments'
import { DocType, DocumentStatus, DOC_TYPE_LABELS } from '@/types/document'

export function DocumentForm() {
  const { modalType, selectedDocument, closeModal } = useDocumentStore()
  const isEdit = modalType === 'edit'

  const { data: fullDocument } = useDocument(isEdit && selectedDocument ? selectedDocument.id : null)
  const createMutation = useCreateDocument()
  const updateMutation = useUpdateDocument()
  const uploadMutation = useUploadDocument()

  const [formData, setFormData] = useState({
    doc_type: 'entity' as DocType,
    title: '',
    content: '',
    metadata: '{}',
    status: 'pending' as DocumentStatus,
    submitted_by: '',
    skip_embedding: false,
    regenerate_embedding: true,
  })

  const [errors, setErrors] = useState<Record<string, string>>({})

  // 파일 업로드 관련 상태
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 수정 모드일 때 데이터 로드
  useEffect(() => {
    if (isEdit && fullDocument) {
      setFormData({
        doc_type: fullDocument.doc_type,
        title: fullDocument.title,
        content: fullDocument.content,
        metadata: JSON.stringify(fullDocument.metadata || {}, null, 2),
        status: fullDocument.status,
        submitted_by: fullDocument.submitted_by || '',
        skip_embedding: false,
        regenerate_embedding: true,
      })
    }
  }, [isEdit, fullDocument])

  const validateAndSetFile = (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (!['md', 'txt', 'pdf'].includes(ext || '')) {
      setErrors((prev) => ({ ...prev, file: '지원하지 않는 파일 형식입니다. (md, txt, pdf만 가능)' }))
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      setErrors((prev) => ({ ...prev, file: '파일 크기가 10MB를 초과합니다.' }))
      return
    }
    setSelectedFile(file)
    setErrors((prev) => ({ ...prev, file: '' }))
    // 제목 자동 설정 (확장자 제외한 파일명)
    if (!formData.title) {
      setFormData((prev) => ({ ...prev, title: file.name.replace(/\.[^/.]+$/, '') }))
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    const file = e.dataTransfer?.files[0]
    if (file) validateAndSetFile(file)
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const validate = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.title.trim()) {
      newErrors.title = '제목을 입력해주세요.'
    }

    // 생성 모드에서는 파일 검증, 수정 모드에서는 content 검증
    if (isEdit) {
      if (!formData.content.trim()) {
        newErrors.content = '내용을 입력해주세요.'
      }
    } else {
      if (!selectedFile) {
        newErrors.file = '파일을 선택해주세요.'
      }
    }

    try {
      JSON.parse(formData.metadata)
    } catch {
      newErrors.metadata = '올바른 JSON 형식이 아닙니다.'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) return

    try {
      let metadata: Record<string, unknown> = {}
      try {
        metadata = JSON.parse(formData.metadata)
      } catch {
        // 이미 validate에서 체크됨
      }

      if (isEdit && selectedDocument) {
        await updateMutation.mutateAsync({
          id: selectedDocument.id,
          data: {
            doc_type: formData.doc_type,
            title: formData.title,
            content: formData.content,
            metadata,
            regenerate_embedding: formData.regenerate_embedding,
          },
        })
        alert('문서가 수정되었습니다.')
      } else if (selectedFile) {
        // 파일 업로드로 문서 생성
        await uploadMutation.mutateAsync({
          file: selectedFile,
          doc_type: formData.doc_type,
          title: formData.title || undefined,
          status: formData.status,
          submitted_by: formData.submitted_by || undefined,
          skip_embedding: formData.skip_embedding,
        })
        alert('문서가 생성되었습니다.')
      }
      closeModal()
    } catch (error) {
      alert('저장 중 오류가 발생했습니다.')
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending || uploadMutation.isPending

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
        {/* 백드롭 */}
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75" onClick={closeModal} />

        {/* 모달 */}
        <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
          {/* 헤더 */}
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">
              {isEdit ? '문서 수정' : '새 문서 등록'}
            </h2>
            <button onClick={closeModal} className="text-gray-400 hover:text-gray-500">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* 폼 */}
          <form onSubmit={handleSubmit} className="px-6 py-4 overflow-y-auto max-h-[60vh]">
            <div className="space-y-4">
              {/* 문서 타입 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  문서 타입 <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.doc_type}
                  onChange={(e) => setFormData({ ...formData, doc_type: e.target.value as DocType })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {Object.entries(DOC_TYPE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>

              {/* 제목 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  제목 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="문서 제목을 입력하세요"
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                    errors.title ? 'border-red-500' : 'border-gray-300'
                  }`}
                />
                {errors.title && <p className="mt-1 text-sm text-red-500">{errors.title}</p>}
              </div>

              {/* 파일 업로드 영역 (생성 모드에서만) */}
              {!isEdit && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    파일 업로드 <span className="text-red-500">*</span>
                  </label>
                  <div
                    onDrop={handleDrop}
                    onDragOver={(e) => {
                      e.preventDefault()
                      setDragActive(true)
                    }}
                    onDragLeave={() => setDragActive(false)}
                    onClick={() => fileInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
                      ${dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
                      ${errors.file ? 'border-red-500' : ''}
                    `}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".md,.txt,.pdf"
                      onChange={(e) => e.target.files?.[0] && validateAndSetFile(e.target.files[0])}
                      className="hidden"
                    />
                    <svg
                      className="mx-auto h-12 w-12 text-gray-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                      />
                    </svg>
                    <p className="mt-2 text-sm text-gray-600">
                      파일을 여기에 드래그하거나 클릭하여 선택
                    </p>
                    <p className="mt-1 text-xs text-gray-500">지원 형식: .md, .txt, .pdf (최대 10MB)</p>
                  </div>
                  {errors.file && <p className="mt-1 text-sm text-red-500">{errors.file}</p>}

                  {/* 선택된 파일 정보 */}
                  {selectedFile && (
                    <div className="mt-3 flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                      <svg
                        className="h-8 w-8 text-blue-500"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={1.5}
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                      </svg>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{selectedFile.name}</p>
                        <p className="text-xs text-gray-500">{formatFileSize(selectedFile.size)}</p>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedFile(null)
                        }}
                        className="text-gray-400 hover:text-gray-500"
                      >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M6 18L18 6M6 6l12 12"
                          />
                        </svg>
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* 내용 (수정 모드에서만) */}
              {isEdit && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    내용 <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    value={formData.content}
                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                    placeholder="문서 내용을 입력하세요"
                    rows={8}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                      errors.content ? 'border-red-500' : 'border-gray-300'
                    }`}
                  />
                  {errors.content && <p className="mt-1 text-sm text-red-500">{errors.content}</p>}
                </div>
              )}

              {/* 메타데이터 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  메타데이터 (JSON)
                </label>
                <textarea
                  value={formData.metadata}
                  onChange={(e) => setFormData({ ...formData, metadata: e.target.value })}
                  placeholder="{}"
                  rows={3}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm ${
                    errors.metadata ? 'border-red-500' : 'border-gray-300'
                  }`}
                />
                {errors.metadata && <p className="mt-1 text-sm text-red-500">{errors.metadata}</p>}
              </div>

              {/* 생성 시에만 보이는 옵션 */}
              {!isEdit && (
                <>
                  {/* 상태 */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">초기 상태</label>
                    <select
                      value={formData.status}
                      onChange={(e) =>
                        setFormData({ ...formData, status: e.target.value as DocumentStatus })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="pending">승인 대기</option>
                      <option value="active">바로 승인 (관리자)</option>
                    </select>
                    <p className="mt-1 text-xs text-gray-500">
                      '바로 승인'을 선택하면 임베딩이 생성되고 RAG 검색에 즉시 사용됩니다.
                    </p>
                  </div>

                  {/* 제출자 */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">제출자</label>
                    <input
                      type="text"
                      value={formData.submitted_by}
                      onChange={(e) => setFormData({ ...formData, submitted_by: e.target.value })}
                      placeholder="제출자 이름/ID"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  {/* 임베딩 건너뛰기 */}
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="skip_embedding"
                      checked={formData.skip_embedding}
                      onChange={(e) =>
                        setFormData({ ...formData, skip_embedding: e.target.checked })
                      }
                      className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <label htmlFor="skip_embedding" className="ml-2 text-sm text-gray-700">
                      임베딩 생성 건너뛰기 (나중에 일괄 생성)
                    </label>
                  </div>
                </>
              )}

              {/* 수정 시에만 보이는 옵션 */}
              {isEdit && (
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="regenerate_embedding"
                    checked={formData.regenerate_embedding}
                    onChange={(e) =>
                      setFormData({ ...formData, regenerate_embedding: e.target.checked })
                    }
                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <label htmlFor="regenerate_embedding" className="ml-2 text-sm text-gray-700">
                    내용 변경 시 임베딩 재생성
                  </label>
                </div>
              )}
            </div>
          </form>

          {/* 푸터 */}
          <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-end gap-2 bg-gray-50">
            <button
              type="button"
              onClick={closeModal}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100"
            >
              취소
            </button>
            <button
              onClick={handleSubmit}
              disabled={isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {isPending ? '저장 중...' : isEdit ? '수정' : '등록'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
