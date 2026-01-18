-- Create chat_messages table for storing chat messages
CREATE TABLE chat_messages (
    message_id VARCHAR(100) PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT,
    render_spec JSONB,
    query_result JSONB,
    query_plan JSONB,
    status VARCHAR(20) DEFAULT 'success',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for session lookup
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);

-- Index for session + created_at (for listing messages in chronological order)
CREATE INDEX idx_chat_messages_session_created ON chat_messages(session_id, created_at ASC);

-- Comments
COMMENT ON TABLE chat_messages IS 'Chat messages with rich content';
COMMENT ON COLUMN chat_messages.message_id IS 'Unique message identifier';
COMMENT ON COLUMN chat_messages.session_id IS 'Parent session ID';
COMMENT ON COLUMN chat_messages.role IS 'Message role: user, assistant, system';
COMMENT ON COLUMN chat_messages.content IS 'Text content of the message';
COMMENT ON COLUMN chat_messages.render_spec IS 'RenderSpec JSON for UI rendering';
COMMENT ON COLUMN chat_messages.query_result IS 'QueryResult JSON from Core API';
COMMENT ON COLUMN chat_messages.query_plan IS 'QueryPlan JSON sent to Core API';
COMMENT ON COLUMN chat_messages.status IS 'Message status: success, error, pending';
