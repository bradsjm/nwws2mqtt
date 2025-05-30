# NWWS2MQTT Metrics System

The NWWS2MQTT application includes a comprehensive metrics system designed for production monitoring and observability. This system provides structured collection, storage, and export of application metrics with support for multiple backends including Prometheus, JSON logging, and structured log output.

## Overview

The metrics system is built around several core components:

- **MetricRegistry**: Central storage for all metrics with thread-safe operations
- **MetricsCollector**: High-level interface for recording metrics with common patterns
- **Metric Types**: Support for counters, gauges, and histograms
- **Exporters**: Pluggable backends for different monitoring systems
- **Labels**: Dimensional metrics with key-value pairs for filtering and aggregation

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Application   │───▶│  MetricsCollector │───▶│  MetricRegistry │
│   Components    │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                                               ┌─────────────────┐
                                               │    Exporters    │
                                               │                 │
                                               │ • Prometheus    │
                                               │ • JSON          │
                                               │ • Logs          │
                                               │ • OpenTelemetry │
                                               └─────────────────┘
```

## Metric Types

### Counters
Monotonically increasing values, typically for counting events.

```python
collector.increment_counter(
    "requests_total",
    labels={"method": "GET", "endpoint": "/api/data"}
)
```

### Gauges
Current values that can increase or decrease.

```python
collector.set_gauge(
    "active_connections",
    42,
    labels={"service": "api"}
)
```

### Histograms
Distribution of values with configurable buckets, ideal for timing metrics.

```python
collector.observe_histogram(
    "request_duration_ms",
    150.5,
    labels={"method": "GET", "status": "200"}
)
```

## Usage Examples

### Basic Metrics Collection

```python
from nwws.metrics import MetricRegistry, MetricsCollector

# Create registry and collector
registry = MetricRegistry()
collector = MetricsCollector(registry, prefix="weather_service")

# Record metrics
collector.increment_counter("messages_processed", labels={"type": "alert"})
collector.set_gauge("queue_size", 23)
collector.observe_histogram("processing_time_ms", 45.2)
```

### Timing Operations

```python
from nwws.metrics import TimingContext

# Using context manager
with TimingContext(collector, "database_query", labels={"table": "users"}):
    # Your operation here
    result = await database.query("SELECT * FROM users")

# Or record operations with success/failure
collector.record_operation(
    "user_creation",
    success=True,
    duration_ms=25.3,
    labels={"source": "api"}
)
```

### Error Tracking

```python
collector.record_error(
    "validation_error",
    operation="user_creation",
    labels={"field": "email"}
)
```

### Status Monitoring

```python
collector.update_status(
    "database",
    "connected",  # or "disconnected"
    labels={"host": "db-primary"}
)
```

## Exporters

### Prometheus Exporter

Exports metrics in Prometheus exposition format for scraping:

```python
from nwws.metrics import PrometheusExporter

exporter = PrometheusExporter(registry)
prometheus_text = exporter.export()
# Use in HTTP endpoint: return Response(prometheus_text, media_type=exporter.get_content_type())
```

### JSON Exporter

Exports all metrics as structured JSON:

```python
from nwws.metrics import JSONExporter

exporter = JSONExporter(registry)
json_data = exporter.export()
```

### Log Exporter

Outputs metrics through structured logging:

```python
from nwws.metrics import LogExporter

exporter = LogExporter(registry, logger=my_logger)
exporter.export()  # Logs metrics using the provided logger
```

## Application Integration

### Pipeline Metrics

The pipeline system automatically collects:

- Processing times per stage
- Throughput metrics
- Queue sizes
- Success/failure rates
- Error counts by type

### Receiver Metrics

The Weather Wire receiver tracks:

- Connection attempts and success rates
- Authentication failures
- Message processing times
- Disconnection events
- Idle timeouts
- Message delays

### Common Metrics

Both components provide:

```python
# Get current metric values
total_messages = registry.get_metric_value(
    "weather_wire_operation_results_total",
    labels={"operation": "message_processing", "result": "success"}
)

# Get registry summary
summary = registry.get_registry_summary()
```

## Production Deployment

### Prometheus Integration

1. Expose metrics endpoint:

```python
from fastapi import FastAPI, Response
from nwws.metrics import PrometheusExporter

app = FastAPI()

@app.get("/metrics")
def metrics():
    exporter = PrometheusExporter(app.metric_registry)
    return Response(exporter.export(), media_type=exporter.get_content_type())
```

2. Configure Prometheus to scrape the endpoint:

```yaml
scrape_configs:
  - job_name: 'nwws2mqtt'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### Structured Logging

For log-based monitoring:

```python
import asyncio
from nwws.metrics import LogExporter

async def periodic_metrics_export(registry, interval=60):
    exporter = LogExporter(registry, logger)
    while True:
        exporter.export()
        await asyncio.sleep(interval)
```

### Health Checks

```python
@app.get("/health")
def health():
    connection_status = registry.get_metric_value(
        "weather_wire_component_status",
        labels={"component": "connection"}
    )

    if connection_status == 1.0:
        return {"status": "healthy"}
    else:
        return {"status": "unhealthy"}, 503
```

## Best Practices

### Naming Conventions

- Use `snake_case` for metric names
- Add appropriate suffixes (`_total`, `_seconds`, `_bytes`)
- Use consistent label names across metrics

### Labels

- Keep label cardinality reasonable (avoid user IDs, timestamps)
- Use labels for dimensions you want to filter/aggregate on
- Consistent label naming across related metrics

### Performance

- The metrics system is thread-safe and optimized for high throughput
- Histogram observations are more expensive than counter increments
- Registry lookups are cached for performance

### Monitoring

Key metrics to alert on:

- `weather_wire_component_status{component="connection"}` - Connection health
- `weather_wire_operation_results_total{result="failure"}` - Error rates
- `weather_wire_last_message_age_seconds` - Data freshness
- `pipeline_queue_size` - Processing backlog
