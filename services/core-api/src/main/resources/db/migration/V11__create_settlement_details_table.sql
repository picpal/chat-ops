-- Create settlement_details table (정산 상세)
CREATE TABLE settlement_details (
    detail_id BIGSERIAL PRIMARY KEY,
    settlement_id VARCHAR(50) NOT NULL REFERENCES settlements(settlement_id),

    -- Transaction reference
    transaction_type VARCHAR(20) NOT NULL,
    payment_key VARCHAR(200) REFERENCES payments(payment_key),
    refund_key VARCHAR(200) REFERENCES refunds(refund_key),

    -- Amount
    amount BIGINT NOT NULL,
    fee BIGINT DEFAULT 0,
    net_amount BIGINT NOT NULL,

    -- Payment method
    method VARCHAR(30),

    -- Original transaction time
    transaction_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_settlement_details_settlement_id ON settlement_details(settlement_id);
CREATE INDEX idx_settlement_details_payment_key ON settlement_details(payment_key);
CREATE INDEX idx_settlement_details_refund_key ON settlement_details(refund_key);
CREATE INDEX idx_settlement_details_transaction_at ON settlement_details(transaction_at DESC);

-- Comment
COMMENT ON TABLE settlement_details IS '정산 상세 내역 (정산에 포함된 개별 거래)';
COMMENT ON COLUMN settlement_details.transaction_type IS 'PAYMENT, REFUND';
