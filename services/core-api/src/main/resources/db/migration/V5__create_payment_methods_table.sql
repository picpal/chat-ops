-- Create payment_methods table (결제수단)
CREATE TABLE payment_methods (
    payment_method_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES pg_customers(customer_id),

    -- Payment method type
    type VARCHAR(30) NOT NULL,

    -- Card info (type = 'CARD')
    card_company VARCHAR(50),
    card_number_masked VARCHAR(20),
    card_type VARCHAR(20),
    card_owner_type VARCHAR(20),
    card_exp_month INTEGER,
    card_exp_year INTEGER,
    card_issuer_code VARCHAR(10),
    card_acquirer_code VARCHAR(10),

    -- Virtual account info (type = 'VIRTUAL_ACCOUNT')
    bank_code VARCHAR(10),
    account_number VARCHAR(50),
    account_holder VARCHAR(100),

    -- Easy pay info (type = 'EASY_PAY')
    easy_pay_provider VARCHAR(50),

    -- Billing key (for subscription)
    billing_key VARCHAR(100),
    billing_key_expires_at TIMESTAMP WITH TIME ZONE,

    -- Status
    is_default BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'ACTIVE',

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_payment_methods_customer_id ON payment_methods(customer_id);
CREATE INDEX idx_payment_methods_type ON payment_methods(type);
CREATE INDEX idx_payment_methods_status ON payment_methods(status);

-- Comment
COMMENT ON TABLE payment_methods IS '결제수단 정보';
COMMENT ON COLUMN payment_methods.type IS 'CARD, VIRTUAL_ACCOUNT, BANK_TRANSFER, MOBILE, EASY_PAY';
COMMENT ON COLUMN payment_methods.card_type IS 'CREDIT, DEBIT, PREPAID';
COMMENT ON COLUMN payment_methods.card_owner_type IS 'PERSONAL, CORPORATE';
COMMENT ON COLUMN payment_methods.easy_pay_provider IS 'KAKAOPAY, NAVERPAY, TOSSPAY, PAYCO 등';
