-- session_id가 NULL인 고아 데이터 삭제
DELETE FROM message_ratings WHERE session_id IS NULL;

-- session_id NOT NULL 제약 추가
ALTER TABLE message_ratings ALTER COLUMN session_id SET NOT NULL;
