-- 채팅 답변 별점 평가 테이블
CREATE TABLE message_ratings (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(100) NOT NULL UNIQUE,
    session_id VARCHAR(100),
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_message_ratings_request_id ON message_ratings(request_id);
CREATE INDEX idx_message_ratings_session_id ON message_ratings(session_id);
