import logging
import pandas as pd
from pathlib import Path
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, to_date, sum as spark_sum, date_format

from spark_jobs.spark_session import get_spark_session
from spark_jobs.save_to_db import save_to_postgres

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfiguracja ścieżek
DATA_LAKE_RAW = Path("data_lake") / "raw" / "orders"
DATA_LAKE_PROCESSED = Path("data_lake") / "processed" / "daily_sales"

REQUIRED_COLUMNS = {"order_id", "order_date", "customer_id", "product_id", "quantity", "price"}


def _validate_schema(df) -> None:
    """Waliduje schemat dataframe'u."""
    if isinstance(df, type(None)):
        raise ValueError("DataFrame jest None")
    
    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        raise ValueError(f"Brakujące kolumny: {missing_cols}")
    logger.info("✓ Schemat danych jest prawidłowy")


def _clean_orders(df):
    """Czyści dane zamówień."""
    logger.info("Czyszczenie danych...")
    
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
    
    logger.info(f"Usunięto {removed} nieprawidłowych wierszy ({rows_before} → {rows_after})")
    
    return df_clean


def _aggregate_daily_sales(df):
    """Agreguje dane do dziennych sprzedaży."""
    logger.info("Agregacja danych do dziennych sprzedaży...")
    
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
    logger.info(f"Utworzono {count} dni ze sprzedażą")
    
    return df_daily


def process_orders(input_path: str, output_path: str) -> None:
    """
    Przetwarzaj zamówienia z raw do processed.
    
    Args:
        input_path: Ścieżka do parquetu z surowymi danymi
        output_path: Ścieżka do zapisania przetworzonych danych
        
    Raises:
        FileNotFoundError: Jeśli input_path nie istnieje
        ValueError: Jeśli dane mają nieprawidłowy schemat
    """
    try:
        spark = get_spark_session()
        
        # Weryfikacja ścieżki
        input_p = Path(input_path)
        if not input_p.exists():
            raise FileNotFoundError(f"Ścieżka input nie istnieje: {input_path}")
        
        logger.info(f"Wczytywanie danych z {input_path}")
        df_orders = spark.read.parquet(input_path)
        logger.info(f"Wczytano {df_orders.count()} wierszy")
        
        # Walidacja
        _validate_schema(df_orders)
        
        # Przetwarzanie
        df_clean = _clean_orders(df_orders)
        df_sales = _aggregate_daily_sales(df_clean)
        
        # Zapis do Parquetu
        output_p = Path(output_path)
        output_p.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Zapis do {output_path}")
        # Aby zachować typ string dla `order_date` i ułatwić konsumpcję poza Sparkiem,
        # rzutujemy datę na string i zapisujemy bez partycjonowania.
        df_to_write = df_sales.withColumn("order_date", date_format(col("order_date"), "yyyy-MM-dd"))
        (df_to_write
            .write
            .mode("overwrite")
            .parquet(output_path)
        )
        
        # Konwersja do Pandas dla zapisu do DB
        logger.info("Konwersja do Pandas dla zapisu do PostgreSQL...")
        df_sales_pandas = df_sales.toPandas()
        
        # Zapis do PostgreSQL
        db_success = save_to_postgres(df_sales_pandas)
        if db_success:
            logger.info("✓ Dane zapisane do PostgreSQL pomyślnie")
        else:
            logger.warning("⚠ Zapis do PostgreSQL nie udał się, ale przetwarzanie kontynuuje")
        
        logger.info("✓ Przetwarzanie zakończone pomyślnie")
        
    except FileNotFoundError as e:
        logger.error(f"Błąd: {e}")
        raise
    except ValueError as e:
        logger.error(f"Błąd walidacji: {e}")
        raise
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd: {e}")
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