# Kontrakt Projektu: Python Spark Data Platform

## Cel
End-to-end platform do ETL (Extract-Transform-Load) danych zamówień przy użyciu PySpark i Pythona.

## Architektura

```
Input CSV
    ↓
[ingestion] → read_orders.py
    ↓
data_lake/raw/orders/ingestion_date=YYYY-MM-DD
    ↓
[processing] → process_orders.py
    ↓
data_lake/processed/daily_sales/processing_date=YYYY-MM-DD
    ↓
Output: Daily Revenue Report
```

## Komponenty

### 1. Ingestion (ingestion/)
- `read_orders.py`: Czyta CSV, waliduje schemat, zapisuje do Parquet
- `validate_orders.py`: Walidacja schemy zamówień
- `schemas.py`: Definicja schemy danych

**Input:** `input/orders/orders_sample.csv`
**Output:** `data_lake/raw/orders/ingestion_date={YYYY-MM-DD}/orders.parquet`

### 2. Processing (spark_jobs/)
- `process_orders.py`: Czyści dane, agreguje do dziennych sprzedaży
- `spark_session.py`: Tworzenie sesji Spark

**Input:** `data_lake/raw/orders/ingestion_date={YYYY-MM-DD}`
**Output:** `data_lake/processed/daily_sales/processing_date={YYYY-MM-DD}`

### 3. Dane

**Schema zamówień:**
```python
{
    "order_id": int,
    "order_date": string (YYYY-MM-DD),
    "customer_id": int,
    "product_id": int,
    "quantity": int,
    "price": float
}
```

**Schema dziennej sprzedaży:**
```python
{
    "order_date": date,
    "daily_revenue": float
}
```

## Pipeline

### Krok 1: Ingestia
```bash
python -c "from ingestion.read_orders import read_orders_csv; read_orders_csv('input/orders/orders_sample.csv')"
```

### Krok 2: Przetwarzanie
```bash
python spark_jobs/process_orders.py \
    "data_lake/raw/orders/ingestion_date=2026-01-22" \
    "data_lake/processed/daily_sales/processing_date=2026-01-22"
```

## Obsługa błędów

| Błąd | Przyczyna | Rozwiązanie |
|------|-----------|-----------|
| `FileNotFoundError` | Plik wejściowy nie istnieje | Sprawdzić ścieżkę |
| `ValueError` | Schemat danych nieprawidłowy | Dodać brakujące kolumny |
| `OSError` | Brak dostępu do dysku | Sprawdzić uprawnienia |
| `EmptyDataError` | Plik CSV jest pusty | Dodać dane do pliku |

## Walidacja

### read_orders.py
- ✓ Plik istnieje
- ✓ Wszystkie wymagane kolumny są obecne
- ✓ DataFrame nie jest pusty

### process_orders.py
- ✓ Schemat jest poprawny
- ✓ Wartości price > 0
- ✓ Wartości quantity > 0
- ✓ order_id nie jest NULL
- ✓ Konwersja daty

## Testowanie

```bash
# Testy unitowe ingestii
pytest tests/ingestion/test_read_orders.py -v

# Testy unitowe przetwarzania
pytest tests/spark_jobs/test_process_orders.py -v

# Wszystkie testy
pytest tests/ -v
```

## Docker

```bash
# Build
docker build -f docker/Dockerfile -t spark-platform:latest .

# Run
docker-compose -f docker/docker-compose.yml up
```

## Konfiguracja ścieżek

`process_orders.py` nie czyta ścieżek ze zmiennych środowiskowych — przyjmuje je jako argumenty pozycyjne CLI (patrz sekcja "Pipeline" powyżej). Gdy uruchamiany bez argumentów, domyślnie używa:

| Ścieżka | Domyślna wartość |
|---------|-------------------|
| Input | `data_lake/raw/orders/ingestion_date={dzisiejsza data}` |
| Output | `data_lake/processed/daily_sales/processing_date={dzisiejsza data}` |

Master Sparka jest zahardkodowany na `local[*]` w `spark_jobs/spark_session.py` i nie jest obecnie konfigurowalny.

## Historia zmian

- **v1.0.0** (2026-01-22): Początkowa implementacja ETL pipeline'u
  - Ingestia CSV → Parquet
  - Przetwarzanie: czyszczenie i agregacja
  - Obsługa błędów
  - Testy jednostkowe
