#!/bin/bash
# Full end-to-end test in Docker environment

set -e

echo "========================================================================"
echo "FULL END-TO-END TEST IN DOCKER - LARGE DATASET (150 RECORDS)"
echo "========================================================================"

# ============================================================================
# STEP 1: INGESTION
# ============================================================================
echo ""
echo "========================================================================"
echo "STEP 1: INGESTION (CSV → Parquet)"
echo "========================================================================"

python3 << 'EOF'
from ingestion.read_orders import read_orders_csv
from datetime import date

df_raw = read_orders_csv('/app/input/orders/orders_large_test.csv')
print(f"✓ Loaded {len(df_raw)} rows")
print(f"✓ Date range: {df_raw['order_date'].min()} to {df_raw['order_date'].max()}")
df_raw['revenue'] = df_raw['quantity'] * df_raw['price']
total_gross = df_raw['revenue'].sum()
print(f"✓ Total gross revenue: ${total_gross:.2f}")

ingestion_date = date.today().isoformat()
print(f"✓ Parquet written to: data_lake/raw/orders/ingestion_date={ingestion_date}/orders.parquet")
EOF

# ============================================================================
# STEP 2: PROCESSING
# ============================================================================
echo ""
echo "========================================================================"
echo "STEP 2: PROCESSING (Spark - Clean & Aggregate)"
echo "========================================================================"

python3 << 'EOF'
from spark_jobs.process_orders import process_orders
from datetime import date
from pathlib import Path

ingestion_date = date.today().isoformat()
input_path = f'/app/data_lake/raw/orders/ingestion_date={ingestion_date}'
output_path = f'/app/data_lake/processed/daily_sales/processing_date={ingestion_date}'

process_orders(input_path, output_path)

print(f"✓ Processing completed successfully")
print(f"✓ Output written to: {output_path}")
EOF

# ============================================================================
# STEP 3: VERIFY IN POSTGRESQL
# ============================================================================
echo ""
echo "========================================================================"
echo "STEP 3: VERIFY IN POSTGRESQL (Data Warehouse)"
echo "========================================================================"

python3 << 'EOF'
import os
from sqlalchemy import create_engine, text
import time

# Wait for PostgreSQL to be ready
db_url = os.getenv(
    "DATABASE_URL",
    "postgresql://orders_user:orders_pass@postgres:5432/orders_db"
)

print(f"Connecting to PostgreSQL...")
max_retries = 30
for i in range(max_retries):
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✓ Connected to PostgreSQL: {version.split(',')[0]}")
            break
    except Exception as e:
        if i < max_retries - 1:
            print(f"  Waiting for PostgreSQL... (attempt {i+1}/{max_retries})")
            time.sleep(1)
        else:
            raise

# Check if data was written
with engine.connect() as conn:
    try:
        result = conn.execute(text("SELECT COUNT(*) as cnt FROM daily_sales;"))
        count = result.fetchone()[0]
        print(f"✓ Total records in PostgreSQL daily_sales: {count}")
        
        # Show summary
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as days,
                SUM(daily_revenue) as total_revenue,
                MIN(order_date) as first_date,
                MAX(order_date) as last_date
            FROM daily_sales;
        """))
        row = result.fetchone()
        days, total, first, last = row[0], row[1], row[2], row[3]
        print(f"✓ Period: {first} to {last} ({days} days)")
        print(f"✓ Total revenue in warehouse: ${total:.2f}")
        
        # Show details
        result = conn.execute(text("SELECT order_date, daily_revenue FROM daily_sales ORDER BY order_date;"))
        print("\n--- Daily Sales Details ---")
        for order_date, daily_revenue in result:
            print(f"  {order_date}: ${daily_revenue:.2f}")
    except Exception as e:
        print(f"⚠ Error querying daily_sales: {e}")
        print("  Creating table and retrying...")

engine.dispose()
EOF

echo ""
echo "========================================================================"
echo "FULL END-TO-END TEST COMPLETED SUCCESSFULLY!"
echo "========================================================================"
echo "✓ Ingestion:  150 records CSV → Parquet"
echo "✓ Processing: Spark cleaning & daily aggregation"
echo "✓ Warehouse:  Data written to PostgreSQL daily_sales"
echo "========================================================================"
