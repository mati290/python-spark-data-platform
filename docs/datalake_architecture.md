# DataLake Architecture

## Overview

The DataLake is organized following a **medallion architecture** (bronze/silver/gold layers) adapted for this orders processing platform.

```
data_lake/
├── raw/                           # Bronze layer - raw data as ingested
│   └── orders/
│       └── ingestion_date=YYYY-MM-DD/
│           └── orders.parquet
│
└── processed/                      # Silver layer - cleaned and aggregated
    └── daily_sales/
        └── processing_date=YYYY-MM-DD/
            └── part-*.parquet
```

## Layers

### Bronze (Raw)
- **Purpose**: Unmodified, as-ingested data
- **Location**: `data_lake/raw/orders/`
- **Partitioning**: By `ingestion_date` (format: YYYY-MM-DD)
- **Format**: Parquet
- **Schema**: Matches input CSV (order_id, order_date, customer_id, product_id, quantity, price)
- **Retention**: Keep all historical ingestions (full append-only)

### Silver (Processed)
- **Purpose**: Cleaned, validated, and aggregated data
- **Location**: `data_lake/processed/daily_sales/`
- **Partitioning**: By `processing_date` (format: YYYY-MM-DD)
- **Format**: Parquet
- **Schema**: Aggregated daily revenue (order_date, daily_revenue)
- **Retention**: Keep all historical processing runs

### Gold (Warehouse)
- **Purpose**: Business-ready data for analytics
- **Location**: PostgreSQL `daily_sales` table
- **Update Strategy**: UPSERT (overwrite by order_date)
- **Query**: `SELECT * FROM daily_sales ORDER BY order_date DESC;`

## Naming Conventions

### Partitions
- Format: `{partition_key}=YYYY-MM-DD`
- Examples:
  - `ingestion_date=2026-01-22`
  - `processing_date=2026-01-22`

### Files
- Parquet partitions: `part-00000-abc123-c000.snappy.parquet`
- Generated automatically by Spark/Pandas

### Metadata
Each layer includes implicit metadata:
- `_SUCCESS` marker (indicates complete write)
- `_metadata` and `_common_metadata` (Parquet metadata)

## Data Governance

### Quality Checks
**Bronze to Silver:**
- Remove null order IDs
- Filter invalid prices (must be > 0)
- Filter invalid quantities (must be > 0)
- Validate order_date format (YYYY-MM-DD)

**Silver to Gold:**
- Ensure unique order_date in daily_sales
- Verify daily_revenue >= 0
- Log successful/failed writes

### Lineage
```
input/orders/orders_sample.csv
        ↓
    [ingestion]
        ↓
data_lake/raw/orders/ingestion_date=2026-01-22/orders.parquet
        ↓
    [processing]
        ↓
data_lake/processed/daily_sales/processing_date=2026-01-22/
        ↓
    [warehouse]
        ↓
PostgreSQL public.daily_sales
```

## Access Patterns

### Read Raw Data (Bronze)
```python
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("DataLake").getOrCreate()
df = spark.read.parquet("data_lake/raw/orders/ingestion_date=2026-01-22/")
```

### Read Processed Data (Silver)
```python
df = spark.read.parquet("data_lake/processed/daily_sales/processing_date=2026-01-22/")
```

### Query Gold Layer (PostgreSQL)
```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("postgresql://orders_user:orders_pass@postgres:5432/orders_db")
df = pd.read_sql("SELECT * FROM daily_sales ORDER BY order_date DESC", engine)
```

## Maintenance

### Cleanup (Optional)
To keep disk usage in check, optionally archive or delete old partitions:

```bash
# List all partitions
ls -la data_lake/raw/orders/
ls -la data_lake/processed/daily_sales/

# Delete partition (example)
rm -rf data_lake/raw/orders/ingestion_date=2026-01-01/
```

### Backups
- DataLake files (Parquet): Part of container volumes, backed up with Docker volume snapshots
- PostgreSQL: Use `pg_dump` for backups:
  ```bash
  docker exec orders-postgres pg_dump -U orders_user orders_db > backup.sql
  ```

## Performance Tuning

### Compression
- Parquet uses Snappy compression by default
- Trade-off: 3:1 compression ratio, fast read/write

### Partitioning
- Current strategy: date-based partitions (effective for time-series)
- Partition pruning: Filters on `ingestion_date` or `processing_date` are highly efficient

### Indexing
- PostgreSQL: Index on `daily_sales(order_date DESC)` for fast queries
- Parquet: No indexes, relies on partition pruning and columnar format

## Future Enhancements

- [ ] Add `_changes` layer for CDC (Change Data Capture)
- [ ] Implement schema versioning for backward compatibility
- [ ] Add data quality metrics (row counts, null rates, etc.)
- [ ] Enable Iceberg for ACID transactions
- [ ] Add time-travel/versioning for data reprocessing
