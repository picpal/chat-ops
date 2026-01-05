-- Create orders table
CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    order_date TIMESTAMP NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL,
    payment_gateway VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for common queries
CREATE INDEX idx_orders_order_date ON orders(order_date DESC);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);

-- Insert sample data
INSERT INTO orders (customer_id, order_date, total_amount, status, payment_gateway) VALUES
(101, '2024-01-05 10:30:00', 2499.00, 'PAID', 'Stripe'),
(102, '2024-01-05 11:15:00', 199.00, 'PENDING', 'PayPal'),
(103, '2024-01-04 16:45:00', 1299.99, 'SHIPPED', 'Stripe'),
(104, '2024-01-04 09:20:00', 599.00, 'PAID', 'Stripe'),
(105, '2024-01-03 14:30:00', 89.99, 'DELIVERED', 'PayPal'),
(101, '2024-01-03 08:15:00', 1499.00, 'PAID', 'Stripe'),
(106, '2024-01-02 18:45:00', 299.00, 'CANCELLED', 'Stripe'),
(107, '2024-01-02 12:00:00', 3999.00, 'PAID', 'Bank Transfer');

-- Add comment
COMMENT ON TABLE orders IS 'E-commerce order transactions';
