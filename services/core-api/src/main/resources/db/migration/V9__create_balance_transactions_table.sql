-- Create balance_transactions table (잔액 거래내역)
CREATE TABLE balance_transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    merchant_id VARCHAR(50) NOT NULL REFERENCES merchants(merchant_id),

    -- Source
    source_type VARCHAR(30) NOT NULL,
    source_id VARCHAR(200) NOT NULL,

    -- Amount
    amount BIGINT NOT NULL,
    fee BIGINT DEFAULT 0,
    net BIGINT NOT NULL,
    currency VARCHAR(3) DEFAULT 'KRW',

    -- Balance
    balance_before BIGINT,
    balance_after BIGINT,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    available_on TIMESTAMP WITH TIME ZONE,

    -- Description
    description VARCHAR(500),

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_balance_transactions_merchant_id ON balance_transactions(merchant_id);
CREATE INDEX idx_balance_transactions_source ON balance_transactions(source_type, source_id);
CREATE INDEX idx_balance_transactions_status ON balance_transactions(status);
CREATE INDEX idx_balance_transactions_created_at ON balance_transactions(created_at DESC);
CREATE INDEX idx_balance_transactions_available_on ON balance_transactions(available_on);
CREATE INDEX idx_balance_tx_merchant_status ON balance_transactions(merchant_id, status);

-- Comment
COMMENT ON TABLE balance_transactions IS '가맹점 잔액 변동 내역 (Stripe balance_transactions 참고)';
COMMENT ON COLUMN balance_transactions.source_type IS 'PAYMENT, REFUND, ADJUSTMENT, PAYOUT, FEE';
COMMENT ON COLUMN balance_transactions.status IS 'PENDING, AVAILABLE, SETTLED';
