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

**Krok 1: Ingestia (CSV → Parquet)**
```bash
python -c "from ingestion.read_orders import read_orders_csv; read_orders_csv('input/orders/orders_sample.csv')"
```

**Krok 2: Przetwarzanie (Spark)**
```bash
python spark_jobs/process_orders.py
```

### 3. Run Tests
```bash
# Wszystkie testy
pytest tests/ -v

# Tylko ingestia
pytest tests/ingestion/ -v

# Tylko processing
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
├── ingestion/                    # CSV → Parquet ingestia
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

## CI — lokalna symulacja (Docker)

Możesz zasymulować działanie GitHub Actions lokalnie, uruchamiając kroki CI w kontenerze. Przydatne gdy chcesz zweryfikować workflow przed pushem.

```bash
# Build image (jeśli jeszcze nie zbudowano)
docker build -f docker/Dockerfile -t spark-platform:latest .

# Unix / macOS
docker run --rm -v $(pwd):/app -w /app spark-platform:latest bash -lc "python3 -m pip install --upgrade pip && pip install -r requirements.txt && pytest tests/ -v"

# Windows (PowerShell)
docker run --rm -v C:\Users\<USER>\python-spark-data-platform:/app -w /app spark-platform:latest bash -lc "python3 -m pip install --upgrade pip && pip install -r requirements.txt && pytest tests/ -v"
```

Workflow CI znajduje się w: `.github/workflows/ci.yml` — po wypchnięciu do repozytorium testy będą uruchamiane automatycznie na GitHubie.

## PostgreSQL — Development & Warehouse

Projekt integruje się z PostgreSQL do przechowywania przetworzonych danych. Do uruchomienia bazy używamy Docker Compose.

### Start PostgreSQL + Spark
```bash
# Uruchom oba serwisy (Spark + PostgreSQL)
docker-compose -f docker/docker-compose.yml up -d

# Sprawdź logi
docker-compose -f docker/docker-compose.yml logs -f spark

# Zatrzymaj serwisy
docker-compose -f docker/docker-compose.yml down
```

### Łączenie się z bazą
```bash
# Z hosta (jeśli Docker desktop)
psql postgresql://orders_user:orders_pass@localhost:5432/orders_db

# Z kontenera
psql postgresql://orders_user:orders_pass@postgres:5432/orders_db
```

### Tabela daily_sales
Przetwarzane dane (przychód dzienny) są zapisywane do tabeli `daily_sales`:

```sql
SELECT * FROM daily_sales ORDER BY order_date DESC;
```

Schemat bazy jest automatycznie tworzony przy starcie kontenera (plik `sql/create_tables.sql`).

## Apache Airflow — Orchestration

Airflow koordynuje całą pipelinę ETL (ingestia → przetwarzanie → zapis do bazy).

### Start Airflow + PostgreSQL + Spark
```bash
# Uruchom wszystkie serwisy (Spark + PostgreSQL + Airflow)
docker-compose -f docker/docker-compose.yml up -d

# Sprawdź status
docker-compose -f docker/docker-compose.yml ps

# Wyłącz
docker-compose -f docker/docker-compose.yml down
```

### Airflow Web UI
Dostępny na: **http://localhost:8080**
- Domyślny login: `airflow` / `airflow`
- DAG: `orders_etl_pipeline` uruchamia się codziennie o północy (schedule: `@daily`)

### Ręczne uruchomienie DAG
```bash
# Trigger DAG z hosta
docker exec -i orders-airflow-scheduler airflow dags trigger orders_etl_pipeline

# Sprawdź status zadań
docker exec -i orders-airflow-scheduler airflow tasks list orders_etl_pipeline
```

### DAG Tasks
Trzy główne zadania:
1. **ingestion** — Czyta CSV, zapisuje Parquet do `data_lake/raw/orders/`
2. **processing** — Agreguje dane, zapisuje do Parquetu i PostgreSQL
3. **warehouse_check** — Weryfikuje liczbę wierszy w tabeli `daily_sales`

## DataLake

Architektura **medallion** (bronze/silver/gold):

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
Pełna dokumentacja: [docs/datalake_architecture.md](docs/datalake_architecture.md)
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
