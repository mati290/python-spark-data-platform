"""
Orders ETL Pipeline - Apache Airflow DAG

Orchestrates the complete data pipeline:
1. Ingest orders from CSV to Parquet (raw)
2. Process and aggregate daily sales (processed)
3. Load results to PostgreSQL warehouse
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

# Default arguments for DAG
default_args = {
    'owner': 'data-engineering',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': days_ago(1),
    'email': ['admin@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
}

# DAG definition
dag = DAG(
    'orders_etl_pipeline',
    default_args=default_args,
    description='ETL pipeline: CSV → Parquet → Aggregation → PostgreSQL',
    schedule_interval='@daily',  # Run daily
    catchup=False,
    tags=['orders', 'etl', 'spark', 'postgresql'],
)


def run_ingestion(**context):
    """Run ingestion phase: CSV → Parquet"""
    from ingestion.read_orders import read_orders_csv
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("Starting ingestion phase...")
    
    try:
        df = read_orders_csv('input/orders/orders_sample.csv')
        logger.info(f"Successfully ingested {len(df)} rows")
        return {'status': 'success', 'rows': len(df)}
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise


def run_processing(**context):
    """Run processing phase: Aggregate → PostgreSQL"""
    from spark_jobs.process_orders import process_orders
    from datetime import date
    import logging
    from pathlib import Path
    
    logger = logging.getLogger(__name__)
    logger.info("Starting processing phase...")
    
    try:
        input_path = str(Path("data_lake") / "raw" / "orders" / f"ingestion_date={date.today().isoformat()}")
        output_path = str(Path("data_lake") / "processed" / "daily_sales" / f"processing_date={date.today().isoformat()}")
        
        process_orders(input_path, output_path)
        logger.info("Processing phase completed successfully")
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise


def check_warehouse(**context):
    """Verify data in PostgreSQL warehouse"""
    import logging
    from sqlalchemy import create_engine, text
    import os
    
    logger = logging.getLogger(__name__)
    
    try:
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://orders_user:orders_pass@postgres:5432/orders_db"
        )
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) as total FROM daily_sales;"))
            count = result.fetchone()[0]
            logger.info(f"✓ Warehouse check: {count} records in daily_sales")
            return {'status': 'success', 'warehouse_records': count}
    except Exception as e:
        logger.warning(f"Warehouse check failed (non-critical): {e}")
        return {'status': 'warning'}


# Task definitions
task_ingestion = PythonOperator(
    task_id='ingestion',
    python_callable=run_ingestion,
    dag=dag,
)

task_processing = PythonOperator(
    task_id='processing',
    python_callable=run_processing,
    dag=dag,
)

task_warehouse_check = PythonOperator(
    task_id='warehouse_check',
    python_callable=check_warehouse,
    dag=dag,
)

# Task dependencies: ingestion → processing → warehouse_check
task_ingestion >> task_processing >> task_warehouse_check
