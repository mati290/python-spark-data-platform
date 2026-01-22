import pytest
from pyspark.sql import SparkSession, Row
from spark_jobs.process_orders import process_orders


@pytest.fixture(scope="function")
def spark():
    spark = (
        SparkSession.builder
        .master("local[1]")
        .appName("pytest-spark")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )
    yield spark


    spark.stop()


def test_process_orders_daily_revenue(spark, tmp_path):
    data = [
        Row(order_id=1, order_date="2024-01-01", customer_id=1002, product_id=2002, quantity=1, price=1.0),
        Row(order_id=2, order_date="2024-01-02", customer_id=1003, product_id=2003, quantity=3, price=5.0),
        
    ]

    df = spark.createDataFrame(data)

    input_path = tmp_path / "input"
    output_path = tmp_path / "output_orders"

    df.write.mode("overwrite").parquet(str(input_path))


    process_orders(str(input_path), str(output_path))


    result_df = spark.read.parquet(str(output_path))
    result = {
        row["order_date"]: row["daily_revenue"]
        for row in result_df.collect()
    }

    assert result["2024-01-01"] == 1.0
    assert result["2024-01-02"] == 15.0
