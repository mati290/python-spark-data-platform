"""Save processed daily sales data to PostgreSQL."""

import os
import logging
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def save_to_postgres(df: pd.DataFrame, table_name: str = "daily_sales") -> bool:
    """
    Save DataFrame to PostgreSQL table.
    
    Args:
        df: DataFrame with columns [order_date, daily_revenue]
        table_name: Target table name (default: daily_sales)
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Get database URL from environment or use default for Docker
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://orders_user:orders_pass@localhost:5432/orders_db"
    )
    
    if df is None or df.empty:
        logger.warning(f"Empty or None DataFrame provided. Skipping save to {table_name}")
        return False
    
    try:
        logger.info(f"Connecting to PostgreSQL: {db_url.split('@')[1]}")
        engine = create_engine(db_url, echo=False)
        
        # Verify connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            logger.info(f"Connected to PostgreSQL: {version.split(',')[0]}")
        
        # Ensure order_date is datetime (handle both string and date types)
        if df["order_date"].dtype == "object":
            df["order_date"] = pd.to_datetime(df["order_date"])
        
        # Convert to date if needed
        if hasattr(df["order_date"].dtype, 'name') and df["order_date"].dtype.name == 'datetime64[ns]':
            df["order_date"] = df["order_date"].dt.date
        
        # For SQLAlchemy 1.4.x compatibility, use raw SQL INSERT
        with engine.begin() as conn:
            # Schema must stay in sync with sql/create_tables.sql
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS daily_sales (
                    id SERIAL PRIMARY KEY,
                    order_date DATE NOT NULL,
                    daily_revenue FLOAT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(order_date)
                )
            """))

            # Bulk upsert instead of row-by-row inserts
            records = [
                {"order_date": row["order_date"], "daily_revenue": float(row["daily_revenue"])}
                for _, row in df.iterrows()
            ]
            conn.execute(text("""
                INSERT INTO daily_sales (order_date, daily_revenue)
                VALUES (:order_date, :daily_revenue)
                ON CONFLICT (order_date) DO UPDATE
                SET daily_revenue = :daily_revenue
            """), records)
        
        logger.info(f"Successfully saved {len(df)} rows to {table_name}")
        
        # Log summary
        with engine.connect() as conn:
            count = conn.execute(
                text(f"SELECT COUNT(*) FROM {table_name};")
            ).fetchone()[0]
            logger.info(f"Total records in {table_name}: {count}")
        
        engine.dispose()
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving to {table_name}: {e}")
        return False


if __name__ == "__main__":
    # Example: test with sample data
    logging.basicConfig(level=logging.INFO)
    
    sample_df = pd.DataFrame({
        "order_date": ["2026-01-20", "2026-01-21", "2026-01-22"],
        "daily_revenue": [1500.50, 2200.75, 1800.25]
    })
    
    success = save_to_postgres(sample_df)
    print(f"Save result: {success}")
