"""Prometheus metrics for monitoring"""
from prometheus_client import Counter, Histogram, Gauge
import time

# Counters
ingestion_records = Counter(
    'orders_ingestion_records_total',
    'Total records ingested',
    ['status']
)

processing_records = Counter(
    'orders_processing_records_total',
    'Total records processed',
    ['status']
)

db_inserts = Counter(
    'orders_db_inserts_total',
    'Total records inserted to database',
    ['table']
)

# Histograms for duration tracking
ingestion_duration = Histogram(
    'orders_ingestion_duration_seconds',
    'Time spent ingesting data',
    buckets=(5, 10, 30, 60, 300)
)

processing_duration = Histogram(
    'orders_processing_duration_seconds',
    'Time spent processing data',
    buckets=(5, 10, 30, 60, 300)
)

db_operation_duration = Histogram(
    'orders_db_operation_duration_seconds',
    'Time spent on database operations',
    ['operation'],
    buckets=(0.1, 0.5, 1, 5, 10)
)

# Gauges for current state
datalake_files = Gauge(
    'orders_datalake_files_total',
    'Total files in data lake',
    ['layer']
)

postgres_table_rows = Gauge(
    'orders_postgres_table_rows',
    'Total rows in PostgreSQL table',
    ['table']
)

pipeline_lag_seconds = Gauge(
    'orders_pipeline_lag_seconds',
    'Lag between ingestion and processing',
)


def track_ingestion(func):
    """Decorator to track ingestion metrics"""
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            ingestion_duration.observe(duration)
            if isinstance(result, object) and hasattr(result, '__len__'):
                ingestion_records.labels(status='success').inc(len(result))
            return result
        except Exception as e:
            ingestion_records.labels(status='error').inc()
            raise
    return wrapper


def track_processing(func):
    """Decorator to track processing metrics"""
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            processing_duration.observe(duration)
            if isinstance(result, object) and hasattr(result, '__len__'):
                processing_records.labels(status='success').inc(len(result))
            return result
        except Exception as e:
            processing_records.labels(status='error').inc()
            raise
    return wrapper


def track_db_operation(operation):
    """Decorator factory for database operation tracking"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                db_operation_duration.labels(operation=operation).observe(duration)
                db_inserts.labels(table=kwargs.get('table', 'unknown')).inc()
                return result
            except Exception as e:
                raise
        return wrapper
    return decorator
