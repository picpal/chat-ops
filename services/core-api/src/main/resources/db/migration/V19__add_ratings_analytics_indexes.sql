-- 별점 분석 쿼리 성능용 인덱스
CREATE INDEX IF NOT EXISTS idx_message_ratings_created_at ON message_ratings(created_at);
CREATE INDEX IF NOT EXISTS idx_message_ratings_rating ON message_ratings(rating);
