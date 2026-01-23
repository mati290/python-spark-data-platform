import logging
import pandas as pd
from datetime import date
from pathlib import Path

from ingestion.validate_orders import validate_orders_schema

# Optional: Import metrics for monitoring (graceful degradation if not available)
try:
    from monitoring.metrics import track_ingestion, ingestion_records
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data lake configuration
DATA_LAKE_PATH = Path("data_lake") / "raw" / "orders"
PARQUET_FILENAME = "orders.parquet"


def read_orders_csv(path: str) -> pd.DataFrame:
    """
    Read and validate order data from CSV file and write to data lake.
    
    Args:
        path: Path to CSV file
        
    Returns:
        DataFrame with validated data
        
    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If schema is invalid or DataFrame is empty
        OSError: If write to disk fails
    """
    
    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(f"File does not exist: {path}")
    
    logger.info(f"Reading data from {path}")
    
   
    df = pd.read_csv(path)
    
    if df.empty:
        raise ValueError("CSV file is empty")
    
    logger.info(f"Loaded {len(df)} rows")
    if METRICS_ENABLED:
        ingestion_records.labels(status='read').inc(len(df))
    
    df_valid = validate_orders_schema(df)
    
    
    ingestion_date = date.today().isoformat()
    output_dir = DATA_LAKE_PATH / f"ingestion_date={ingestion_date}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / PARQUET_FILENAME
    
    try:
        df_valid.to_parquet(str(output_file), index=False)
        logger.info(f"Data written to {output_file}")
        if METRICS_ENABLED:
            ingestion_records.labels(status='success').inc(len(df_valid))
    except OSError as e:
        logger.error(f"Error writing to Parquet: {e}")
        if METRICS_ENABLED:
            ingestion_records.labels(status='error').inc()
        raise
    
    return df_valid
