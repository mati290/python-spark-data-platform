# python-spark-data-platform

End-to-end data engineering platform built with Python and Apache Spark for processing orders data.

## Tech stack
- Python 3.10+
- Apache Spark 3.5.1
- Pandas + PyArrow
- PostgreSQL (planned)
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

## Status

- [x] Ingestion module
- [x] Processing module
- [x] Unit tests
- [x] Docker configuration
- [ ] Airflow DAGs
- [ ] PostgreSQL integration
- [ ] CI/CD pipeline

## License

MIT
