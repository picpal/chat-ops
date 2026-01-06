-- Create payment_history table (결제 상태 이력)
CREATE TABLE payment_history (
    history_id BIGSERIAL PRIMARY KEY,
    payment_key VARCHAR(200) NOT NULL REFERENCES payments(payment_key),

    -- Status change
    previous_status VARCHAR(30),
    new_status VARCHAR(30) NOT NULL,

    -- Amount change
    amount_change BIGINT DEFAULT 0,
    balance_after BIGINT,

    -- Reason
    reason VARCHAR(200),
    reason_code VARCHAR(50),

    -- Processor info
    processed_by VARCHAR(50),
    processor_id VARCHAR(50),

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_payment_history_payment_key ON payment_history(payment_key);
CREATE INDEX idx_payment_history_created_at ON payment_history(created_at DESC);
CREATE INDEX idx_payment_history_new_status ON payment_history(new_status);

-- Comment
COMMENT ON TABLE payment_history IS '결제 상태 변경 이력 (audit trail)';
COMMENT ON COLUMN payment_history.processed_by IS 'SYSTEM, ADMIN, MERCHANT, CUSTOMER';
