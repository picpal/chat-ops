-- Create merchants table (PG 가맹점)
CREATE TABLE merchants (
    merchant_id VARCHAR(50) PRIMARY KEY,
    business_name VARCHAR(255) NOT NULL,
    business_number VARCHAR(20) NOT NULL UNIQUE,
    representative_name VARCHAR(100) NOT NULL,
    business_type VARCHAR(50),
    business_category VARCHAR(100),

    -- Contact info
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    postal_code VARCHAR(10),

    -- Settlement info
    settlement_bank_code VARCHAR(10),
    settlement_account_number VARCHAR(50),
    settlement_account_holder VARCHAR(100),
    settlement_cycle VARCHAR(20) DEFAULT 'D+1',

    -- Fee
    fee_rate DECIMAL(5, 4) DEFAULT 0.0350,

    -- API keys
    api_key_live VARCHAR(100),
    api_key_test VARCHAR(100),

    -- Status
    status VARCHAR(20) DEFAULT 'PENDING',
    verified_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_merchants_status ON merchants(status);
CREATE INDEX idx_merchants_business_number ON merchants(business_number);
CREATE INDEX idx_merchants_created_at ON merchants(created_at DESC);

-- Comment
COMMENT ON TABLE merchants IS 'PG 가맹점 정보';
COMMENT ON COLUMN merchants.merchant_id IS '가맹점 고유 ID (mer_xxx 형식)';
COMMENT ON COLUMN merchants.settlement_cycle IS '정산주기: D+0, D+1, D+2, WEEKLY, MONTHLY';
COMMENT ON COLUMN merchants.fee_rate IS '수수료율 (0.0350 = 3.5%)';
COMMENT ON COLUMN merchants.status IS 'PENDING, ACTIVE, SUSPENDED, TERMINATED';
