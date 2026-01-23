import pytest
import pandas as pd
from pathlib import Path
from datetime import date

from ingestion.read_orders import read_orders_csv


def test_read_orders_file_not_found():
    """Test error handling - file does not exist."""
    with pytest.raises(FileNotFoundError):
        read_orders_csv('nonexistent/file.csv')


def test_read_orders_empty_file(tmp_path):
    """Test error handling - empty CSV file."""
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("order_id,order_date,customer_id,product_id,quantity,price\n")
    
    with pytest.raises(ValueError, match="empty"):
        read_orders_csv(str(csv_file))


def test_read_orders_missing_required_columns(tmp_path):
    """Test error handling - missing required columns."""
    csv_file = tmp_path / "missing_cols.csv"
    csv_file.write_text("order_id,order_date\n1,2024-01-01\n")
    
    with pytest.raises(ValueError, match="Missing columns"):
        read_orders_csv(str(csv_file))


def test_read_orders_with_extra_columns(tmp_path):
    """Test - extra columns should be ignored."""
    csv_content = """order_id,order_date,customer_id,product_id,quantity,price,extra_col
1,2024-01-01,1001,2001,2,19.99,unused
2,2024-01-02,1002,2002,1,9.99,unused
"""
    csv_file = tmp_path / "extra.csv"
    csv_file.write_text(csv_content)
    
    df = read_orders_csv(str(csv_file))
    
    # Should load data and write to parquet
    assert len(df) == 2
    assert 'extra_col' in df.columns


def test_read_orders_large_file(tmp_path):
    """Test - large file (1000 rows)."""
    rows = ["order_id,order_date,customer_id,product_id,quantity,price"]
    for i in range(1, 1001):
        rows.append(f"{i},2024-01-01,{1000+i},{2000+i},{i % 10 + 1},{i * 0.1}")
    
    csv_file = tmp_path / "large.csv"
    csv_file.write_text("\n".join(rows))
    
    df = read_orders_csv(str(csv_file))
    
    assert len(df) == 1000
    assert df['price'].min() > 0


def test_read_orders_invalid_date_format(tmp_path):
    """Test - invalid date format."""
    csv_content = """order_id,order_date,customer_id,product_id,quantity,price
1,invalid-date,1001,2001,2,19.99
2,2024-01-02,1002,2002,1,9.99
"""
    csv_file = tmp_path / "invalid_date.csv"
    csv_file.write_text(csv_content)
    
    # Should pass - validation does not check date format
    df = read_orders_csv(str(csv_file))
    assert len(df) == 2


def test_read_orders_zero_and_negative_prices(tmp_path):
    """Test - zero and negative prices."""
    csv_content = """order_id,order_date,customer_id,product_id,quantity,price
1,2024-01-01,1001,2001,2,0.0
2,2024-01-02,1002,2002,1,-5.0
3,2024-01-03,1003,2003,3,10.0
"""
    csv_file = tmp_path / "special_prices.csv"
    csv_file.write_text(csv_content)
    
    # Validation does not check values, only schema
    df = read_orders_csv(str(csv_file))
    assert len(df) == 3
    
    # These values will be filtered in processing


def test_read_orders_parquet_output_exists(tmp_path):
    """Test - verify that parquet file was created."""
    csv_content = """order_id,order_date,customer_id,product_id,quantity,price
1,2024-01-01,1001,2001,2,19.99
"""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)
    
    # Temporarily change data_lake path
    original_cwd = Path.cwd()
    
    try:
        df = read_orders_csv(str(csv_file))
        
        # Check if parquet was written
        ingestion_date = date.today().isoformat()
        parquet_path = Path("data_lake") / "raw" / "orders" / f"ingestion_date={ingestion_date}"
        
        assert parquet_path.exists()
        assert (parquet_path / "orders.parquet").exists()
    finally:
        # Cleanup
        import shutil
        if Path("data_lake").exists():
            shutil.rmtree("data_lake")
