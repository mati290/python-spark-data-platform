#!/usr/bin/env python3
"""
Test end-to-end pipeline: RAW → PROCESSED
"""
from pathlib import Path
from datetime import date
import pandas as pd

print("\n=== INGESTION: CSV → Parquet ===")
from ingestion.read_orders import read_orders_csv

df_raw = read_orders_csv('input/orders/orders_sample.csv')
print(f"✓ Loaded {len(df_raw)} rows")
print(df_raw)

print("\n=== PROCESSING: Raw → Processed ===")

# Cleaning
df_clean = df_raw.copy()
df_clean['order_date'] = pd.to_datetime(df_clean['order_date'])
df_clean = df_clean[df_clean['order_id'].notna()]
df_clean = df_clean[df_clean['price'].notna()]
df_clean = df_clean[df_clean['quantity'].notna()]
df_clean = df_clean[(df_clean['quantity'] > 0) & (df_clean['price'] > 0)]

rows_before = len(df_raw)
rows_after = len(df_clean)
rows_removed = rows_before - rows_after
print(f"Cleaning: {rows_removed} rows removed ({rows_before} → {rows_after})")

# Agregacja
df_daily = df_clean.groupby('order_date').agg({
    'quantity': 'sum',
    'price': 'sum'
}).reset_index()
df_daily['daily_revenue'] = df_daily['quantity'] * df_daily['price']
df_daily = df_daily[['order_date', 'daily_revenue']].sort_values('order_date')

print(f"Agregacja: {len(df_daily)} dni sprzedaży")

# Zapis
output_dir = Path('data_lake/processed/daily_sales') / f'processing_date={date.today().isoformat()}'
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / 'daily_sales.parquet'
df_daily.to_parquet(str(output_file), index=False)

print(f"✓ Zapisano do {output_file}")

print("\n=== WYNIK ===")
print(df_daily)
print("\n✅ Pipeline RAW → PROCESSED zakończony!")
