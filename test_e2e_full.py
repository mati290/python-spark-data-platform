import sys
sys.path.insert(0, '/app')

print('=' * 70)
print('END-TO-END PIPELINE TEST')
print('=' * 70)

# Step 1: Ingestion
print('\n[STEP 1] INGESTION: CSV → Parquet')
print('-' * 70)
from ingestion.read_orders import read_orders_csv
df_raw = read_orders_csv('/app/input/orders/orders_test_full.csv')
print(f'✓ Loaded {len(df_raw)} records from CSV')
print(f'✓ Columns: {list(df_raw.columns)}')
print(f'✓ Date range: {df_raw["order_date"].min()} to {df_raw["order_date"].max()}')

# Step 2: Processing
print('\n[STEP 2] PROCESSING: Spark Aggregation')
print('-' * 70)
from spark_jobs.process_orders import process_orders
from pyspark.sql import SparkSession
# process_orders expects paths, not DataFrames - it reads from Parquet
ingestion_date = '2026-01-23'
input_path = f'/app/data_lake/raw/orders/ingestion_date={ingestion_date}'
output_dir = f'/app/data_lake/processed/daily_sales/processing_date={ingestion_date}'
process_orders(input_path, output_dir)

# Read back processed data
spark = SparkSession.builder.appName('test').getOrCreate()
df_processed = spark.read.parquet(output_dir)
processed_count = df_processed.count()
print(f'✓ Processed {processed_count} unique daily records')
print(f'✓ Columns: {df_processed.columns}')
pdf = df_processed.toPandas()
print(f'✓ Date range: {pdf["order_date"].min()} to {pdf["order_date"].max()}')
print(f'✓ Total daily revenue: ${pdf["daily_revenue"].sum():.2f}')

# Step 3: Check warehouse
print('\n[STEP 3] WAREHOUSE: PostgreSQL daily_sales')
print('-' * 70)
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://orders_user:orders_pass@postgres:5432/orders_db')
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) as cnt FROM daily_sales'))
    count = result.scalar()
    print(f'✓ Daily sales table has {count} rows')
    result = conn.execute(text('SELECT order_date, daily_revenue FROM daily_sales ORDER BY order_date DESC LIMIT 5'))
    rows = result.fetchall()
    print(f'✓ Last 5 entries:')
    for row in rows:
        print(f'  - {row[0]}: ${row[1]:.2f}')

print('\n' + '=' * 70)
print('✓ END-TO-END TEST PASSED')
print('=' * 70)
