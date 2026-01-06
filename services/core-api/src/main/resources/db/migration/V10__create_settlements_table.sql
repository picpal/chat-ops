-- Create settlements table (정산)
CREATE TABLE settlements (
    settlement_id VARCHAR(50) PRIMARY KEY,
    merchant_id VARCHAR(50) NOT NULL REFERENCES merchants(merchant_id),

    -- Settlement period
    settlement_date DATE NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Amount
    total_payment_amount BIGINT NOT NULL,
    total_refund_amount BIGINT DEFAULT 0,
    total_fee BIGINT DEFAULT 0,
    net_amount BIGINT NOT NULL,

    -- Count
    payment_count INTEGER DEFAULT 0,
    refund_count INTEGER DEFAULT 0,

    -- Status
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',

    -- Payout info
    payout_bank_code VARCHAR(10),
    payout_account_number VARCHAR(50),
    payout_account_holder VARCHAR(100),
    payout_reference VARCHAR(100),

    -- Timestamps
    processed_at TIMESTAMP WITH TIME ZONE,
    paid_out_at TIMESTAMP WITH TIME ZONE,

    -- Failure
    failure_code VARCHAR(50),
    failure_message VARCHAR(500),

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_settlements_merchant_id ON settlements(merchant_id);
CREATE INDEX idx_settlements_date ON settlements(settlement_date DESC);
CREATE INDEX idx_settlements_status ON settlements(status);
CREATE INDEX idx_settlements_period ON settlements(period_start, period_end);

-- Unique constraint (one settlement per merchant per day)
CREATE UNIQUE INDEX idx_settlements_merchant_date ON settlements(merchant_id, settlement_date);

-- Comment
COMMENT ON TABLE settlements IS 'PG 정산 메인 테이블';
COMMENT ON COLUMN settlements.status IS 'PENDING, PROCESSING, COMPLETED, FAILED';
