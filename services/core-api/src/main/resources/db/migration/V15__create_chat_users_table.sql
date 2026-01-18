-- Create chat_users table for user management
CREATE TABLE chat_users (
    user_id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for email lookup
CREATE INDEX idx_chat_users_email ON chat_users(email);

-- Comment
COMMENT ON TABLE chat_users IS 'Chat users for session management';
COMMENT ON COLUMN chat_users.user_id IS 'Unique user identifier';
COMMENT ON COLUMN chat_users.email IS 'User email (unique)';
COMMENT ON COLUMN chat_users.display_name IS 'Display name for UI';
COMMENT ON COLUMN chat_users.status IS 'User status: ACTIVE, INACTIVE';
