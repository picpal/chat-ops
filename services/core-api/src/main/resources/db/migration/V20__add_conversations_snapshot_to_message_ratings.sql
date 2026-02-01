-- 평가 저장 시 대화 이력 스냅샷을 보존하기 위한 JSONB 컬럼 추가
-- 세션 hard delete 후에도 평가 모달에서 대화 이력을 볼 수 있도록 함
ALTER TABLE message_ratings ADD COLUMN conversations JSONB;
