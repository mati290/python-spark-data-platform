import logging
import pandas as pd
from datetime import date
from ingestion.validate_orders import validate_orders_schema

logging.basicConfig(level=logging.INFO)


def read_orders_csv(path: str) -> str:
    """
    Reads orders CSV, validates schema and writes data to Data Lake (RAW layer).
    Returns path to RAW data for further processing.
    """
    logging.info(f"Reading orders data from {path}")

    df_orders_raw = pd.read_csv(path)
    df_orders_valid = validate_orders_schema(df_orders_raw)

    ingestion_date = date.today().isoformat()
    output_path = f"data_lake/raw/orders/ingestion_date={ingestion_date}"

    logging.info(f"Writing RAW orders data to {output_path}")

    df_orders_valid.to_parquet(
        output_path,
        index=False
    )

    return output_path
