#!/bin/bash
set -e
echo "=== Ingestion Phase ==="
python3 -c 'from ingestion.read_orders import read_orders_csv; read_orders_csv("input/orders/orders_sample.csv")'
echo "✓ Ingestion completed"

echo ""
echo "=== Processing Phase ==="
python3 spark_jobs/process_orders.py
echo "✓ Processing completed"

echo ""
echo "=== Verify data in PostgreSQL ==="
psql -h orders-postgres -U orders_user -d orders_db -c "SELECT order_date, daily_revenue FROM daily_sales ORDER BY order_date DESC LIMIT 10;"
echo "✓ Query completed"
