import pytest
import pandas as pd
from pathlib import Path
from datetime import date

from spark_jobs.process_orders import _clean_orders, _aggregate_daily_sales, _validate_schema
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StructType, StructField, IntegerType, StringType, FloatType


@pytest.fixture
def sample_df():
    """Create sample DataFrame with order data."""
    data = {
        'order_id': [1, 2, 3, 4, 5],
        'order_date': ['2024-01-01', '2024-01-01', '2024-01-02', '2024-01-02', '2024-01-02'],
        'customer_id': [1001, 1002, 1003, 1004, 1005],
        'product_id': [2001, 2002, 2003, 2004, 2005],
        'quantity': [2, 1, 3, 0, 2],  # 0 will be filtered
        'price': [10.0, 5.0, 7.0, -5.0, 3.0]  # -5.0 will be filtered
    }
    return pd.DataFrame(data)


def test_validate_schema_valid(sample_df):
    """Test schema validation - valid schema."""
    # Should pass without error
    try:
        _validate_schema(sample_df)
    except ValueError:
        pytest.fail("Schema validation should not fail for valid data")


def test_validate_schema_missing_columns():
    """Test schema validation - missing columns."""
    df = pd.DataFrame({'order_id': [1], 'order_date': ['2024-01-01']})
    
    with pytest.raises(ValueError, match="Missing columns"):
        _validate_schema(df)


def test_clean_orders(sample_df):
    """Test czyszczenia danych."""
    df_clean = _clean_orders(sample_df)
    
    # Powinno usunąć: quantity=0 (row 4), price<0 (row 4)
    assert len(df_clean) == 4  # Pozostały wiersze: 1, 2, 3, 5
    
    # Verificare price > 0
    assert all(df_clean['price'] > 0)
    
    # Verificare quantity > 0
    assert all(df_clean['quantity'] > 0)


def test_clean_orders_removes_nulls():
    """Test czyszczenia - usunięcie NULL wartości."""
    df = pd.DataFrame({
        'order_id': [1, None, 3],
        'order_date': ['2024-01-01', '2024-01-01', '2024-01-01'],
        'customer_id': [1001, 1002, 1003],
        'product_id': [2001, 2002, 2003],
        'quantity': [1, 1, None],
        'price': [10.0, None, 10.0]
    })
    
    df_clean = _clean_orders(df)
    
    # Powinno usunąć wiersze z NULL wartościami
    assert len(df_clean) == 1
    assert df_clean['order_id'].iloc[0] == 1


def test_aggregate_daily_sales(sample_df):
    """Test agregacji dziennych sprzedaży."""
    # Czyść dane najpierw
    df_clean = _clean_orders(sample_df)
    
    # Agreguj
    df_daily = _aggregate_daily_sales(df_clean)
    
    # Powinno być 2 dni (2024-01-01 i 2024-01-02)
    assert len(df_daily) == 2
    
    # Po czyszczeniu: rows 1,2,3,5 (bez row 4 z quantity=0, price<0)
    # 2024-01-01: rows 1,2 → (2*10.0 + 1*5.0) = 25.0
    # 2024-01-02: rows 3,5 → (3*7.0 + 2*3.0) = 27.0
    day1 = df_daily[df_daily['order_date'] == '2024-01-01']['daily_revenue'].values[0]
    assert day1 == pytest.approx(25.0)
    
    day2 = df_daily[df_daily['order_date'] == '2024-01-02']['daily_revenue'].values[0]
    assert day2 == pytest.approx(27.0)


def test_aggregate_empty_dataframe():
    """Test agregacji dla pustego DataFrame."""
    df_empty = pd.DataFrame({
        'order_id': [],
        'order_date': [],
        'quantity': [],
        'price': []
    })
    
    # Agregacja pustego DataFrame'u powinna zwrócić pusty DataFrame
    df_daily = _aggregate_daily_sales(df_empty)
    assert len(df_daily) == 0


def test_aggregate_daily_sales_ordering():
    """Test czy wyniki są posortowane po dacie."""
    df = pd.DataFrame({
        'order_id': [1, 2, 3, 4],
        'order_date': ['2024-01-03', '2024-01-01', '2024-01-02', '2024-01-01'],
        'customer_id': [1001, 1002, 1003, 1004],
        'product_id': [2001, 2002, 2003, 2004],
        'quantity': [1, 1, 1, 1],
        'price': [10.0, 10.0, 10.0, 10.0]
    })
    
    df_clean = _clean_orders(df)
    df_daily = _aggregate_daily_sales(df_clean)
    
    # Sprawdź czy dane są posortowane
    dates = df_daily['order_date'].tolist()
    assert dates == sorted(dates)
