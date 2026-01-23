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

# Konfiguracja ścieżek
DATA_LAKE_PATH = Path("data_lake") / "raw" / "orders"
PARQUET_FILENAME = "orders.parquet"


def read_orders_csv(path: str) -> pd.DataFrame:
    """
    Czyta i waliduje dane zamówień z pliku CSV, zapisuje do data lake'u.
    
    Args:
        path: Ścieżka do pliku CSV
        
    Returns:
        DataFrame ze zwalidowanymi danymi
        
    Raises:
        FileNotFoundError: Jeśli plik nie istnieje
        ValueError: Jeśli schemat jest nieprawidłowy lub DataFrame jest pusty
        OSError: Jeśli zapis do dysku się nie powiedzie
    """
    
    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(f"Plik nie istnieje: {path}")
    
    logger.info(f"Czytanie danych z {path}")
    
   
    df = pd.read_csv(path)
    
    if df.empty:
        raise ValueError("Plik CSV jest pusty")
    
    logger.info(f"Wczytano {len(df)} wierszy")
    if METRICS_ENABLED:
        ingestion_records.labels(status='read').inc(len(df))
    
    df_valid = validate_orders_schema(df)
    
    
    ingestion_date = date.today().isoformat()
    output_dir = DATA_LAKE_PATH / f"ingestion_date={ingestion_date}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / PARQUET_FILENAME
    
    try:
        df_valid.to_parquet(str(output_file), index=False)
        logger.info(f"Dane zapisane do {output_file}")
        if METRICS_ENABLED:
            ingestion_records.labels(status='success').inc(len(df_valid))
    except OSError as e:
        logger.error(f"Błąd zapisu do Parquetu: {e}")
        if METRICS_ENABLED:
            ingestion_records.labels(status='error').inc()
        raise
    
    return df_valid
