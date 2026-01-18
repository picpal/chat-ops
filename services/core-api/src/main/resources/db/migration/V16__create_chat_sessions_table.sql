-- Create chat_sessions table for chat session management
CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL REFERENCES chat_users(user_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    subtitle VARCHAR(500),
    icon VARCHAR(50) DEFAULT 'chat',
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for user lookup
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);

-- Index for user + updated_at (for listing sessions)
CREATE INDEX idx_chat_sessions_user_updated ON chat_sessions(user_id, updated_at DESC);

-- Comments
COMMENT ON TABLE chat_sessions IS 'Chat sessions for organizing conversations';
COMMENT ON COLUMN chat_sessions.session_id IS 'Unique session identifier';
COMMENT ON COLUMN chat_sessions.user_id IS 'Owner user ID';
COMMENT ON COLUMN chat_sessions.title IS 'Session title';
COMMENT ON COLUMN chat_sessions.subtitle IS 'Session subtitle/description';
COMMENT ON COLUMN chat_sessions.icon IS 'Icon name for UI';
COMMENT ON COLUMN chat_sessions.status IS 'Session status: ACTIVE, ARCHIVED, DELETED';
