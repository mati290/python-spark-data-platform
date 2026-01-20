import pandas as pd
import pytest
from ingestion.read_orders import read_orders_csv

def test_read_orders_csv(tmp_path):
    
    csv_content = """order_id,order_date,customer_id,product_id,quantity,price
1,2024-01-01,1001,2001,2,19.99
2,2024-01-02,1002,2002,1,9.99
3,2024-01-03,1003,2003,5,4.99
"""

    file_path = tmp_path / "orders.csv"
    file_path.write_text(csv_content)

    df = read_orders_csv(file_path)
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "order_id" in df.columns
    
def test_read_orders_csv_invalid_schema(tmp_path):
    csv_content = """order_id,order_date,customer_id,quantity
1,2024-01-01,1001,2,19.99
2,2024-01-02,1002,1,9.99
3,2024-01-03,1003,5,4.99
"""

    file_path = tmp_path / "orders_invalid.csv"
    file_path.write_text(csv_content)
    
    with pytest.raises(ValueError):
        read_orders_csv(file_path)