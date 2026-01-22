-- Create schema for processed daily sales
CREATE TABLE IF NOT EXISTS daily_sales (
    id SERIAL PRIMARY KEY,
    order_date DATE NOT NULL,
    daily_revenue FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(order_date)
);

-- Index for query performance
CREATE INDEX IF NOT EXISTS idx_daily_sales_date ON daily_sales(order_date DESC);

-- Comments
COMMENT ON TABLE daily_sales IS 'Daily aggregated revenue from orders processing pipeline';
COMMENT ON COLUMN daily_sales.order_date IS 'Date of orders (YYYY-MM-DD)';
COMMENT ON COLUMN daily_sales.daily_revenue IS 'Total revenue for the day (sum of quantity * price)';
