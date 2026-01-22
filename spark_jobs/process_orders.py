from pyspark.sql.functions import col, to_date, sum as spark_sum
from spark_jobs.spark_session import get_spark_session

def process_orders(input_path: str, output_path: str):
    spark = get_spark_session()
    # Wczytywanie danych zamówień
    df_orders = spark.read.parquet(input_path)
        
    
    
    #Czyszczenie
    df_clean = df_orders.withColumn("order_date", to_date(col("order_date"))).filter(col("order_id").isNotNull()).filter(col("price").isNotNull())     
    
    #Aggragacja
    df_daily_sales = df_clean.groupBy("order_date").agg(spark_sum(col("quantity") * col("price")).alias("daily_revenue"))

    # Zapis do Parquet
    
    (df_daily_sales.write.mode("overwrite").partitionBy("order_date").parquet(output_path))