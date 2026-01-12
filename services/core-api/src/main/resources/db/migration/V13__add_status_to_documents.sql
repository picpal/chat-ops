-- =============================================
-- V10: documents 테이블에 승인 워크플로우 컬럼 추가
-- =============================================

-- 문서 상태 컬럼 추가 (기본값: 'active'로 기존 데이터 호환)
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active';

-- 제출자 정보
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS submitted_by VARCHAR(100);

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP WITH TIME ZONE;

-- 검토자 정보
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS reviewed_by VARCHAR(100);

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP WITH TIME ZONE;

-- 반려 사유
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status);
CREATE INDEX IF NOT EXISTS idx_documents_status_doc_type ON documents (status, doc_type);

-- 상태 값 제약 조건 (pending, active, rejected만 허용)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_documents_status'
    ) THEN
        ALTER TABLE documents
        ADD CONSTRAINT chk_documents_status
        CHECK (status IN ('pending', 'active', 'rejected'));
    END IF;
END $$;

-- 코멘트 추가
COMMENT ON COLUMN documents.status IS '문서 상태: pending(승인대기), active(승인됨), rejected(반려됨)';
COMMENT ON COLUMN documents.submitted_by IS '문서 제출자 ID/이름';
COMMENT ON COLUMN documents.submitted_at IS '문서 제출 시각';
COMMENT ON COLUMN documents.reviewed_by IS '검토자 ID/이름';
COMMENT ON COLUMN documents.reviewed_at IS '검토 시각';
COMMENT ON COLUMN documents.rejection_reason IS '반려 사유';
