-- Create refunds table (환불/취소)
CREATE TABLE refunds (
    refund_key VARCHAR(200) PRIMARY KEY,
    payment_key VARCHAR(200) NOT NULL REFERENCES payments(payment_key),

    -- Refund amount
    amount BIGINT NOT NULL,
    tax_free_amount BIGINT DEFAULT 0,

    -- Reason
    reason VARCHAR(200) NOT NULL,
    cancel_reason_code VARCHAR(50),

    -- Status
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',

    -- Result
    approved_at TIMESTAMP WITH TIME ZONE,
    failure_code VARCHAR(50),
    failure_message VARCHAR(500),

    -- Virtual account refund
    refund_bank_code VARCHAR(10),
    refund_account_number VARCHAR(50),
    refund_account_holder VARCHAR(100),

    -- Request info
    request_id VARCHAR(100),
    requested_by VARCHAR(50),
    requester_id VARCHAR(50),

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_refunds_payment_key ON refunds(payment_key);
CREATE INDEX idx_refunds_status ON refunds(status);
CREATE INDEX idx_refunds_created_at ON refunds(created_at DESC);

-- Comment
COMMENT ON TABLE refunds IS '결제 취소/환불 트랜잭션';
COMMENT ON COLUMN refunds.status IS 'PENDING, SUCCEEDED, FAILED';
COMMENT ON COLUMN refunds.requested_by IS 'MERCHANT, ADMIN, CUSTOMER';
