# python-spark-data-platform

End-to-end data engineering platform built with Python and Apache Spark for processing orders data.

## Quick Links
- **Prometheus** (metrics): http://localhost:9090
- **Grafana** (dashboards): http://localhost:3000 (admin/admin)
- **Airflow** (orchestration): http://localhost:8080 (airflow/airflow)
- **postgres-exporter** (metrics): http://localhost:9187

## Tech stack
- Python 3.10+
- Apache Spark 3.5.1
- Pandas + PyArrow
- PostgreSQL (data warehouse)
- Apache Airflow (orchestration)
- Prometheus + Grafana (monitoring)
- Docker & Docker Compose
- pytest

## Quick Start

### 1. Setup
```bash
pip install -r requirements.txt
```

### 2. Run ETL Pipeline

**Step 1: Ingestion (CSV → Parquet)**
```bash
python -c "from ingestion.read_orders import read_orders_csv; read_orders_csv('input/orders/orders_sample.csv')"
```

**Step 2: Processing (Spark)**
```bash
python spark_jobs/process_orders.py
```

### 3. Run Tests
```bash
# All tests
pytest tests/ -v

# Ingestion only
pytest tests/ingestion/ -v

# Processing only
pytest tests/spark_jobs/ -v
```

## Architecture

```
Input CSV
    ↓
[ingestion/read_orders.py]
    ↓
data_lake/raw/orders/ingestion_date={DATE}
    ↓
[spark_jobs/process_orders.py]
    ↓
data_lake/processed/daily_sales/processing_date={DATE}
    ↓
Output: Daily Revenue Report
```

## Project Structure

```
.
├── ingestion/                    # CSV → Parquet ingestion
│   ├── read_orders.py           # Main ingestion logic
│   ├── validate_orders.py       # Schema validation
│   └── schemas.py               # Data schemas
├── spark_jobs/                  # Spark processing
│   ├── process_orders.py        # Main processing logic
│   └── spark_session.py         # Spark session setup
├── tests/                       # Unit tests
│   ├── ingestion/
│   └── spark_jobs/
├── docker/                      # Docker configuration
│   ├── Dockerfile
│   └── docker-compose.yml
├── sql/                         # Database schema
│   └── create_tables.sql        # PostgreSQL initialization
├── data_lake/                   # Data storage
│   ├── raw/                     # Raw data
│   └── processed/               # Processed data
├── input/                       # Input data samples
├── docs/                        # Documentation
│   └── kontrakt_projektu.md    # Project contract
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Data Flow

### Ingestion Phase
- **Input:** CSV file (`input/orders/orders_sample.csv`)
- **Validation:** Check required columns
- **Output:** Parquet file in `data_lake/raw/orders/ingestion_date={YYYY-MM-DD}`

### Processing Phase
- **Input:** Raw Parquet from data lake
- **Cleaning:** Remove invalid rows, convert dates
- **Aggregation:** Daily revenue calculation
- **Output:** Processed Parquet in `data_lake/processed/daily_sales/processing_date={YYYY-MM-DD}`

## Data Schema

**Orders (Raw)**
```
order_id: int
order_date: string (YYYY-MM-DD)
customer_id: int
product_id: int
quantity: int
price: float
```

**Daily Sales (Processed)**
```
order_date: date
daily_revenue: float
```

## Error Handling

All components have comprehensive error handling:
- ✓ File existence validation
- ✓ Schema validation
- ✓ Data quality checks
- ✓ Detailed logging
- ✓ Proper exception handling

## Docker

```bash
# Build image
docker build -f docker/Dockerfile -t spark-platform:latest .

# Run with Docker Compose
docker-compose -f docker/docker-compose.yml up

# Run specific command
docker run -v $(pwd):/app spark-platform:latest python spark_jobs/process_orders.py
```

## CI/CD — Local Simulation (Docker)

You can simulate GitHub Actions locally by running CI steps in a container. Useful for verifying workflows before pushing.

```bash
# Build image
docker build -f docker/Dockerfile -t spark-platform:latest .

# Unix / macOS
docker run --rm -v $(pwd):/app -w /app spark-platform:latest bash -lc "python3 -m pip install --upgrade pip && pip install -r requirements.txt && pytest tests/ -v"

# Windows (PowerShell)
docker run --rm -v C:\Users\<USER>\python-spark-data-platform:/app -w /app spark-platform:latest bash -lc "python3 -m pip install --upgrade pip && pip install -r requirements.txt && pytest tests/ -v"
```

CI workflow is located in `.github/workflows/ci.yml` — tests run automatically on GitHub after push.

## PostgreSQL — Development & Data Warehouse

The project integrates with PostgreSQL to store processed data. Docker Compose is used to run the database.

### Start PostgreSQL + Spark
```bash
# Start both services (Spark + PostgreSQL)
docker-compose -f docker/docker-compose.yml up -d

# Check logs
docker-compose -f docker/docker-compose.yml logs -f spark

# Stop services
docker-compose -f docker/docker-compose.yml down
```

### Connect to Database
```bash
# From host (if Docker desktop)
psql postgresql://orders_user:orders_pass@localhost:5432/orders_db

# From container
psql postgresql://orders_user:orders_pass@postgres:5432/orders_db
```

### Daily Sales Table
Processed data (daily revenue) is written to `daily_sales` table:

```sql
SELECT * FROM daily_sales ORDER BY order_date DESC;
```

Database schema is automatically created when the container starts (file `sql/create_tables.sql`).

## Apache Airflow — Orchestration

Airflow orchestrates the entire ETL pipeline (ingestion → processing → database write).

### Start Airflow + PostgreSQL + Spark
```bash
# Start all services (Spark + PostgreSQL + Airflow)
docker-compose -f docker/docker-compose.yml up -d

# Check status
docker-compose -f docker/docker-compose.yml ps

# Stop
docker-compose -f docker/docker-compose.yml down
```

### Airflow Web UI
Available at: **http://localhost:8080**
- Default login: `airflow` / `airflow`
- DAG: `orders_etl_pipeline` runs daily at midnight (schedule: `@daily`)

### Manual DAG trigger
```bash
# Trigger DAG from host
docker exec -i orders-airflow-scheduler airflow dags trigger orders_etl_pipeline

# Check task status
docker exec -i orders-airflow-scheduler airflow tasks list orders_etl_pipeline
```

### DAG Tasks
Three main tasks:
1. **ingestion** — Read CSV, write Parquet to `data_lake/raw/orders/`
2. **processing** — Aggregate data, write to Parquet and PostgreSQL
3. **warehouse_check** — Verify row count in `daily_sales` table

## DataLake

**Medallion** architecture (bronze/silver/gold):

```
data_lake/
├── raw/               # Bronze - raw ingested data
│   └── orders/
│       └── ingestion_date=YYYY-MM-DD/
│           └── orders.parquet
│
└── processed/         # Silver - cleaned & aggregated
    └── daily_sales/
        └── processing_date=YYYY-MM-DD/
            └── part-*.parquet
            
        ↓ (upsert into)
        
PostgreSQL: daily_sales table (Gold)
```

### Initialize DataLake
```bash
python scripts/init_datalake.py
```

### DataLake Details
Full documentation: [docs/datalake_architecture.md](docs/datalake_architecture.md)
- Partitioning strategy (date-based)
- Data governance & quality checks
- Access patterns (PySpark, SQL)
- Maintenance & backups

## Development

### Adding New Tests
```bash
# Create test file in tests/ directory
pytest tests/ -v --cov=ingestion,spark_jobs
```

### Code Quality
```bash
# Format code
black .

# Type checking (if using mypy)
mypy --ignore-missing-imports .
```

## Documentation

See [docs/kontrakt_projektu.md](docs/kontrakt_projektu.md) for detailed project specification.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `FileNotFoundError` | Check input file path exists |
| `ValueError: Missing columns` | Ensure CSV has all required columns |
| `PermissionError` | Check directory write permissions |
| `PySpark not installed` | Run `pip install -r requirements.txt` |

## Advanced Monitoring & Alerting

Platform includes comprehensive monitoring with Prometheus, Grafana, and automated alerting.

### Start Monitoring Stack
```bash
docker-compose -f docker/docker-compose.yml up -d prometheus grafana postgres-exporter
```

### Access Monitoring UIs
| Component | URL | Credentials |
|-----------|-----|-------------|
| Prometheus | http://localhost:9090 | None |
| Grafana | http://localhost:3000 | admin / admin |
| postgres-exporter | http://localhost:9187/metrics | None |

### Monitored Metrics
- **Ingestion:** Record count, job duration
- **Processing:** Records processed, execution time
- **Data Warehouse:** Connections, table sizes, disk space
- **Airflow:** Scheduler health, task/DAG failures
- **Data Lake:** Ingestion latency, missing daily imports

### Alert Rules
Configured alerts for:
- PostgreSQL down, high connections, low disk space
- Airflow scheduler down, DAG/task failures
- Data lake ingestion lag and missing imports

**Full documentation:** [docs/monitoring.md](docs/monitoring.md)

## Status

- [x] Ingestion module
- [x] Processing module
- [x] Unit tests
- [x] Docker configuration
- [x] PostgreSQL integration (daily_sales table)
- [x] Apache Airflow orchestration
- [x] DataLake medallion architecture
- [x] CI/CD pipeline (GitHub Actions)
- [x] Advanced monitoring & alerting (Prometheus + Grafana)
- [ ] Real-time streaming (future)

## License

MIT
