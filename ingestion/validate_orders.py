import logging
from ingestion.schemas import ORDERS_SCHEMA

logging.basicConfig(level=logging.INFO)

def validate_orders_schema(df):
    missing_columns = set(ORDERS_SCHEMA) - set(df.columns)
    
    if missing_columns:
        logging.error(f"Missing columns in orders data: {missing_columns}")
        raise ValueError(f"Missing columns: {missing_columns}")
    
    logging.info("All required columns are present in orders data.")
    return df
    