import logging
import pandas as pd
from pathlib import Path
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, to_date, sum as spark_sum, date_format

from spark_jobs.spark_session import get_spark_session
from spark_jobs.save_to_db import save_to_postgres
from ingestion.schemas import ORDERS_SCHEMA

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration paths
DATA_LAKE_RAW = Path("data_lake") / "raw" / "orders"
DATA_LAKE_PROCESSED = Path("data_lake") / "processed" / "daily_sales"

REQUIRED_COLUMNS = set(ORDERS_SCHEMA)


def _validate_schema(df) -> None:
    """Validate DataFrame schema."""
    if isinstance(df, type(None)):
        raise ValueError("DataFrame is None")
    
    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing columns: {missing_cols}")
    logger.info("✓ Data schema is valid")


def _clean_orders(df):
    """Clean order data."""
    logger.info("Cleaning data...")
    
    # Obsługa zarówno Pandas jak i Spark DataFrame
    is_pandas = hasattr(df, 'copy') and not hasattr(df, 'withColumn')
    
    if is_pandas:
        df_clean = df.copy()
        df_clean['order_date'] = pd.to_datetime(df_clean['order_date'])
        df_clean = df_clean[df_clean['order_id'].notna()]
        df_clean = df_clean[df_clean['price'].notna()]
        df_clean = df_clean[df_clean['quantity'].notna()]
        df_clean = df_clean[(df_clean['quantity'] > 0) & (df_clean['price'] > 0)]
    else:
        # Spark DataFrame
        df_clean = (df
            .withColumn("order_date", to_date(col("order_date")))
            .filter(col("order_id").isNotNull())
            .filter(col("price").isNotNull())
            .filter(col("quantity").isNotNull())
            .filter(col("quantity") > 0)
            .filter(col("price") > 0)
        )
    
    rows_before = len(df) if is_pandas else df.count()
    rows_after = len(df_clean) if is_pandas else df_clean.count()
    removed = rows_before - rows_after
    
    logger.info(f"Removed {removed} invalid rows ({rows_before} → {rows_after})")
    
    return df_clean


def _aggregate_daily_sales(df):
    """Aggregate data to daily sales."""
    logger.info("Aggregating data to daily sales...")
    
    is_pandas = hasattr(df, 'groupby') and not hasattr(df, 'withColumn')
    
    if is_pandas:
        # Najpierw oblicz revenue dla każdego wiersza
        df_revenue = df.copy()
        df_revenue['revenue'] = df_revenue['quantity'] * df_revenue['price']
        
        # Następnie agreguj
        df_daily = df_revenue.groupby('order_date')['revenue'].sum().reset_index()
        df_daily.columns = ['order_date', 'daily_revenue']
        df_daily = df_daily.sort_values('order_date').reset_index(drop=True)
    else:
        # Spark DataFrame
        df_daily = (df
            .groupBy("order_date")
            .agg(spark_sum(col("quantity") * col("price")).alias("daily_revenue"))
            .orderBy("order_date")
            # zapisz datę jako string w formacie YYYY-MM-DD aby ułatwić konsumpcję poza Sparkiem
            .withColumn("order_date", date_format(col("order_date"), "yyyy-MM-dd"))
        )
    
    count = len(df_daily) if is_pandas else df_daily.count()
    logger.info(f"Created {count} days with sales")
    
    return df_daily


def process_orders(input_path: str, output_path: str) -> None:
    """
    Process orders from raw to processed.
    
    Args:
        input_path: Path to parquet with raw data
        output_path: Path to write processed data
        
    Raises:
        FileNotFoundError: If input_path does not exist
        ValueError: If data has invalid schema
    """
    try:
        spark = get_spark_session()
        
        # Path verification
        input_p = Path(input_path)
        if not input_p.exists():
            raise FileNotFoundError(f"Input path does not exist: {input_path}")
        
        logger.info(f"Loading data from {input_path}")
        df_orders = spark.read.parquet(input_path)
        logger.info(f"Loaded {df_orders.count()} rows")
        
        # Validation
        _validate_schema(df_orders)
        
        # Processing
        df_clean = _clean_orders(df_orders)
        df_sales = _aggregate_daily_sales(df_clean)
        
        # Write to Parquet
        output_p = Path(output_path)
        output_p.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Writing to {output_path}")
        # To preserve string type for `order_date` and ease consumption outside Spark,
        # cast date to string and write without partitioning.
        df_to_write = df_sales.withColumn("order_date", date_format(col("order_date"), "yyyy-MM-dd"))
        (df_to_write
            .write
            .mode("overwrite")
            .parquet(output_path)
        )
        
        # Convert to Pandas for DB write
        logger.info("Converting to Pandas for PostgreSQL write...")
        df_sales_pandas = df_sales.toPandas()
        
        # Write to PostgreSQL
        db_success = save_to_postgres(df_sales_pandas)
        if not db_success:
            raise RuntimeError("Failed to write processed data to PostgreSQL")
        logger.info("✓ Data written to PostgreSQL successfully")
        
        logger.info("✓ Processing completed successfully")
        
    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    import sys
    from datetime import date
    
    # Domyślne ścieżki - mogą być nadpisane argumentami
    default_input = str(DATA_LAKE_RAW / f"ingestion_date={date.today().isoformat()}")
    default_output = str(DATA_LAKE_PROCESSED / f"processing_date={date.today().isoformat()}")
    
    input_path = sys.argv[1] if len(sys.argv) > 1 else default_input
    output_path = sys.argv[2] if len(sys.argv) > 2 else default_output
    
    process_orders(input_path, output_path)