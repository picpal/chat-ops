-- Create payments table (결제 트랜잭션 - 핵심 테이블)
CREATE TABLE payments (
    -- Primary identifiers
    payment_key VARCHAR(200) PRIMARY KEY,
    order_id VARCHAR(64) NOT NULL,

    -- Relations
    merchant_id VARCHAR(50) NOT NULL REFERENCES merchants(merchant_id),
    customer_id VARCHAR(50) REFERENCES pg_customers(customer_id),
    payment_method_id VARCHAR(50) REFERENCES payment_methods(payment_method_id),

    -- Payment info
    order_name VARCHAR(100) NOT NULL,
    amount BIGINT NOT NULL,
    currency VARCHAR(3) DEFAULT 'KRW',

    -- Payment method snapshot
    method VARCHAR(30) NOT NULL,
    method_detail JSONB,

    -- Amount breakdown
    balance_amount BIGINT NOT NULL,
    supplied_amount BIGINT,
    vat BIGINT,
    tax_free_amount BIGINT DEFAULT 0,

    -- Status
    status VARCHAR(30) NOT NULL DEFAULT 'READY',

    -- Approval info
    approved_at TIMESTAMP WITH TIME ZONE,
    receipt_url VARCHAR(500),

    -- Card approval (method = 'CARD')
    card_approval_number VARCHAR(20),
    card_installment_months INTEGER DEFAULT 0,
    card_is_interest_free BOOLEAN DEFAULT FALSE,

    -- Virtual account (method = 'VIRTUAL_ACCOUNT')
    virtual_account_bank_code VARCHAR(10),
    virtual_account_number VARCHAR(50),
    virtual_account_holder VARCHAR(100),
    virtual_account_due_date TIMESTAMP WITH TIME ZONE,
    virtual_account_refund_status VARCHAR(20),

    -- Cancellation
    canceled_at TIMESTAMP WITH TIME ZONE,
    canceled_amount BIGINT DEFAULT 0,
    cancel_reason VARCHAR(200),

    -- Failure
    failure_code VARCHAR(50),
    failure_message VARCHAR(500),

    -- Settlement
    is_settled BOOLEAN DEFAULT FALSE,
    settlement_id VARCHAR(50),

    -- Request metadata
    request_id VARCHAR(100),
    client_ip VARCHAR(45),
    user_agent VARCHAR(500),

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_merchant_id ON payments(merchant_id);
CREATE INDEX idx_payments_customer_id ON payments(customer_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_method ON payments(method);
CREATE INDEX idx_payments_created_at ON payments(created_at DESC);
CREATE INDEX idx_payments_approved_at ON payments(approved_at DESC);
CREATE INDEX idx_payments_is_settled ON payments(is_settled) WHERE is_settled = FALSE;
CREATE INDEX idx_payments_settlement_id ON payments(settlement_id);

-- Composite indexes
CREATE INDEX idx_payments_merchant_created ON payments(merchant_id, created_at DESC);
CREATE INDEX idx_payments_merchant_status ON payments(merchant_id, status);

-- Comment
COMMENT ON TABLE payments IS 'PG 결제 트랜잭션 메인 테이블';
COMMENT ON COLUMN payments.payment_key IS 'PG 발급 결제 고유키 (Toss paymentKey 참고)';
COMMENT ON COLUMN payments.balance_amount IS '취소 가능한 잔액';
COMMENT ON COLUMN payments.status IS 'READY, IN_PROGRESS, WAITING_FOR_DEPOSIT, DONE, CANCELED, PARTIAL_CANCELED, ABORTED, EXPIRED';
