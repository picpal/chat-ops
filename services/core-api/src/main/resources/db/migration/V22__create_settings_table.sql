-- Settings table for application configuration
-- Stores key-value pairs with JSONB support for complex settings

CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL DEFAULT '{}',
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for efficient lookups
CREATE INDEX idx_settings_key ON settings(key);

-- Insert default setting for Quality Answer RAG feature
INSERT INTO settings (key, value, description) VALUES
('quality_answer_rag', '{"enabled": true, "minRating": 4}', 'Quality Answer RAG 기능 토글 - 높은 별점 답변을 참고하여 답변 품질 향상');

-- Add comment for documentation
COMMENT ON TABLE settings IS 'Application settings stored as key-value pairs with JSONB support';
COMMENT ON COLUMN settings.key IS 'Unique setting identifier';
COMMENT ON COLUMN settings.value IS 'Setting value as JSONB for flexibility';
COMMENT ON COLUMN settings.description IS 'Human-readable description of the setting';
