# Advanced Monitoring & Alerting

## Overview

The Orders ETL Platform includes comprehensive monitoring and alerting capabilities powered by Prometheus, Grafana, and postgres_exporter.

## Architecture

### Components

1. **Prometheus** (port 9090)
   - Time-series database for metrics collection
   - Scrapes metrics from Airflow, PostgreSQL, and application endpoints
   - Stores metrics with 15-second scrape interval

2. **Grafana** (port 3000)
   - Visualization and dashboard platform
   - Pre-configured dashboards for platform monitoring
   - Default credentials: admin / admin

3. **postgres-exporter** (port 9187)
   - PostgreSQL metrics exporter
   - Tracks connections, table sizes, query performance, disk space

4. **Alert Rules**
   - PostgreSQL health (connectivity, connection limits, disk space)
   - Airflow orchestration (scheduler health, task/DAG failures)
   - Data lake operations (ingestion lag, missing daily imports)

## Quick Start

### 1. Start Monitoring Stack

```bash
cd docker
docker-compose up -d prometheus grafana postgres-exporter
```

Verify services:
```bash
docker-compose ps
```

### 2. Access UI Dashboards

| Component | URL | Default Credentials |
|-----------|-----|-------------------|
| Prometheus | http://localhost:9090 | No auth |
| Grafana | http://localhost:3000 | admin / admin |
| postgres-exporter | http://localhost:9187/metrics | No auth |

### 3. Configure Grafana Datasource

Grafana automatically discovers Prometheus as a datasource (via provisioning).

1. Visit http://localhost:3000
2. Log in with admin/admin
3. Dashboard "Orders ETL Platform - Overview" should be pre-loaded
4. View metrics for Airflow tasks, PostgreSQL connections, data lake operations

## Monitoring Metrics

### Ingestion Pipeline
- `orders_ingestion_records_total` - Records successfully ingested (counter)
- `orders_ingestion_duration_seconds` - Ingestion job runtime (histogram)

### Processing Pipeline
- `orders_processing_records_total` - Records processed (counter)
- `orders_processing_duration_seconds` - Processing job runtime (histogram)

### Data Warehouse
- `orders_db_operation_duration_seconds` - Database operation timing (histogram)
- `orders_db_inserts_total` - Rows inserted to warehouse (counter)
- `orders_postgres_table_rows` - Current row count in PostgreSQL tables (gauge)

### Data Lake
- `orders_datalake_files_total` - Files in bronze/silver/gold layers (gauge)
- `orders_pipeline_lag_seconds` - Time between ingestion and processing (gauge)

### System Health
- `airflow_scheduler_heartbeat` - Scheduler health status
- `airflow_task_duration_total` - Task execution duration
- `pg_stat_activity_count` - Active PostgreSQL connections
- `pg_database_size_bytes` - PostgreSQL database disk usage

## Alert Rules

Configured in `monitoring/alert_rules.yml`:

### PostgreSQL Alerts
| Alert | Severity | Threshold | Action |
|-------|----------|-----------|--------|
| PostgreSQL Down | Critical | N/A | Service unavailable |
| High Connection Count | Warning | >80 connections | Check for connection leaks |
| Low Disk Space | Warning | <20% free | Add storage capacity |

### Airflow Alerts
| Alert | Severity | Threshold | Action |
|-------|----------|-----------|--------|
| Scheduler Down | Critical | N/A | Restart scheduler service |
| DAG Failures | Warning | DAG failure rate | Investigate failed tasks |
| Task Failures | Critical | >10 failures in 1h | Review task logs |

### Data Lake Alerts
| Alert | Severity | Threshold | Action |
|-------|----------|-----------|--------|
| High Ingestion Latency | Warning | >300s | Optimize CSV parsing |
| Missing Daily Import | Warning | No data today | Check data source |

## Custom Alerting

### Add Email Notifications

1. Configure AlertManager (Prometheus must be integrated with AlertManager)
2. Update `docker-compose.yml` to add AlertManager service:

```yaml
alertmanager:
  image: prom/alertmanager:latest
  ports:
    - "9093:9093"
  volumes:
    - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml
```

3. Create `monitoring/alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m
  smtp_smarthost: smtp.gmail.com:587
  smtp_auth_username: your-email@gmail.com
  smtp_auth_password: your-app-password

route:
  receiver: 'email'
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h

receivers:
  - name: 'email'
    email_configs:
      - to: 'alerts@company.com'
        from: 'prometheus@company.com'
```

### Add Slack Notifications

Update AlertManager config:

```yaml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
        title: 'Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

## Troubleshooting

### Prometheus not scraping metrics
- Check Prometheus UI: http://localhost:9090/targets
- Verify service health checks pass: `docker-compose ps`
- Review Prometheus logs: `docker logs orders-prometheus`

### Grafana dashboards empty
- Verify Prometheus datasource is connected (Configuration → Data Sources)
- Check metric names match `monitoring/grafana-dashboard.json`
- Review Prometheus for available metrics: http://localhost:9090/graph

### Alerts not firing
- Verify AlertManager connectivity in Prometheus config
- Check alert rule syntax: `promtool check rules monitoring/alert_rules.yml`
- Review Prometheus alerts UI: http://localhost:9090/alerts

## Advanced Configuration

### Scrape Interval Tuning

In `monitoring/prometheus.yml`:
```yaml
global:
  scrape_interval: 15s      # Default 15s
  evaluation_interval: 15s  # How often to evaluate rules
```

Higher intervals = less load, higher latency
Lower intervals = more load, lower latency

### Retention Policy

In `docker-compose.yml` prometheus service:
```yaml
command:
  - '--storage.tsdb.retention.time=30d'  # Keep 30 days of data
```

### Custom Dashboards

1. Create dashboard in Grafana UI
2. Export as JSON: Dashboard Settings → JSON Model
3. Save to `monitoring/custom-dashboard.json`
4. Add to docker-compose volume mounts

## Integration with Airflow

Airflow automatically exposes metrics on port 8080:
- `/metrics` endpoint (Prometheus format)
- Tracked: DAG runs, task duration, scheduler heartbeat

## Integration with Applications

Add to your Spark jobs and Python scripts:

```python
from monitoring.metrics import track_ingestion, ingestion_records

@track_ingestion
def read_orders_csv(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    ingestion_records.labels(status='success').inc(len(df))
    return df
```

Start metrics server:
```python
from prometheus_client import start_http_server
start_http_server(8000)  # Expose metrics on :8000/metrics
```

## Performance Considerations

- **Cardinality**: Avoid high-cardinality labels (e.g., unique user IDs)
- **Storage**: Prometheus stores ~1.3KB per metric per hour
- **Query Performance**: Use recording rules for complex queries
- **Grafana Refresh**: Set dashboard refresh to 30-60s for balance

## Security Best Practices

- **Reverse Proxy**: Place Prometheus/Grafana behind reverse proxy with authentication
- **Network Policy**: Restrict port access (9090, 3000, 9187) in production
- **Credentials**: Change Grafana admin password: http://localhost:3000/admin/users/1/edit
- **TLS**: Enable HTTPS for all external connections

## Related Documentation

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [PostgreSQL Exporter Metrics](https://github.com/prometheus-community/postgres_exporter)
- [Airflow Metrics](https://airflow.apache.org/docs/apache-airflow/stable/logging-monitoring/metrics.html)
