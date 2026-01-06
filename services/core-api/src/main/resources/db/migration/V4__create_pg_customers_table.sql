-- Create pg_customers table (PG 고객)
CREATE TABLE pg_customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    merchant_id VARCHAR(50) NOT NULL REFERENCES merchants(merchant_id),

    -- Customer info
    email VARCHAR(255),
    name VARCHAR(100),
    phone VARCHAR(20),

    -- Shipping address
    shipping_name VARCHAR(100),
    shipping_phone VARCHAR(20),
    shipping_address TEXT,
    shipping_postal_code VARCHAR(10),

    -- Default payment method
    default_payment_method_id VARCHAR(50),

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_pg_customers_merchant_id ON pg_customers(merchant_id);
CREATE INDEX idx_pg_customers_email ON pg_customers(email);
CREATE INDEX idx_pg_customers_created_at ON pg_customers(created_at DESC);

-- Comment
COMMENT ON TABLE pg_customers IS 'PG 고객 정보';
COMMENT ON COLUMN pg_customers.customer_id IS '고객 고유 ID (cus_xxx 형식)';
