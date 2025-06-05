# NWWS Metrics Package

The metrics package provides comprehensive metrics collection, registry management, and export capabilities for the NWWS2MQTT system. It implements a flexible metrics system that supports counters, gauges, and histograms with Prometheus-compatible export functionality.

## Overview

The metrics system is designed to provide real-time observability into the NWWS2MQTT application's performance, health, and operational characteristics. It follows Prometheus conventions and supports both pull-based and push-based metric collection patterns.

## Architecture

The metrics package consists of several key components:

- **MetricRegistry**: Central registry for all metrics
- **MetricsCollector**: High-level interface for collecting metrics
- **PrometheusExporter**: Exports metrics in Prometheus format
- **Metric Types**: Core data structures for different metric types

```python
from nwws.metrics import MetricRegistry, MetricsCollector, PrometheusExporter

# Initialize metrics system
registry = MetricRegistry()
collector = MetricsCollector(registry)
exporter = PrometheusExporter(registry)
```

## Core Components

### MetricRegistry

The central registry that manages all metrics in the system. It provides thread-safe operations for registering, updating, and retrieving metrics.

**Key Features:**
- Thread-safe metric storage and retrieval
- Automatic metric creation with type validation
- Label-based metric organization
- Efficient lookup and enumeration

**Usage Example:**
```python
from nwws.metrics import MetricRegistry, MetricType

registry = MetricRegistry()

# Register a counter
registry.get_or_create_metric(
    name="messages_processed_total",
    metric_type=MetricType.COUNTER,
    help_text="Total number of messages processed",
    labels={"handler": "mqtt"}
)

# Increment the counter
registry.increment_counter("messages_processed_total", labels={"handler": "mqtt"})

# Set a gauge value
registry.set_gauge("connection_status", 1.0, labels={"service": "xmpp"})
```

### MetricsCollector

High-level interface for collecting metrics with convenient methods and context managers.

**Key Features:**
- Simplified metric collection API
- Timing context managers
- Automatic timestamp management
- Integration with application components

**Usage Example:**
```python
from nwws.metrics import MetricsCollector, TimingContext

collector = MetricsCollector(registry)

# Increment counters
collector.increment("requests_total", labels={"endpoint": "/metrics"})

# Set gauge values
collector.set_gauge("active_connections", 5.0)

# Time operations
with collector.timer("request_duration_ms") as timer:
    # Perform operation
    process_request()
    # Duration automatically recorded

# Manual timing
timer = collector.start_timer("manual_operation_ms")
perform_operation()
collector.stop_timer(timer)
```

### PrometheusExporter

Exports metrics in Prometheus text format, compatible with Prometheus scraping and other monitoring systems.

**Key Features:**
- Prometheus text format compliance
- HTTP endpoint integration
- Configurable metric filtering
- Performance optimized rendering

**Usage Example:**
```python
from nwws.metrics import PrometheusExporter

exporter = PrometheusExporter(registry)

# Export all metrics
metrics_text = exporter.export()

# Export with filtering
filtered_metrics = exporter.export(name_filter="nwws_")

# HTTP endpoint integration
@app.get("/metrics")
async def metrics_endpoint():
    return Response(
        content=exporter.export(),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )
```

## Metric Types

### Counter

Monotonically increasing values that represent cumulative totals.

**Use Cases:**
- Request counts
- Error counts
- Message processing totals
- Connection attempts

**Example:**
```python
# Register counter
registry.get_or_create_metric(
    name="http_requests_total",
    metric_type=MetricType.COUNTER,
    help_text="Total HTTP requests",
    labels={"method": "GET", "endpoint": "/api"}
)

# Increment counter
registry.increment_counter("http_requests_total", 
                         amount=1.0, 
                         labels={"method": "GET", "endpoint": "/api"})
```

### Gauge

Current values that can increase or decrease, representing point-in-time measurements.

**Use Cases:**
- Connection status
- Queue sizes
- Memory usage
- Temperature readings

**Example:**
```python
# Register gauge
registry.get_or_create_metric(
    name="queue_size",
    metric_type=MetricType.GAUGE,
    help_text="Current queue size"
)

# Set gauge value
registry.set_gauge("queue_size", 42.0)
```

### Histogram

Distribution of values across configurable buckets, useful for measuring latencies and sizes.

**Use Cases:**
- Request latencies
- Message sizes
- Processing times
- Response times

**Example:**
```python
from nwws.metrics.types import Histogram

# Create histogram with custom buckets
buckets = [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
histogram = Histogram(buckets=buckets)

# Register histogram metric
registry.get_or_create_metric(
    name="request_duration_seconds",
    metric_type=MetricType.HISTOGRAM,
    help_text="Request duration in seconds",
    value=histogram
)

# Record observations
registry.observe_histogram("request_duration_seconds", 1.23)
registry.observe_histogram("request_duration_seconds", 0.45)
```

## TimingContext

Context manager for automatic timing of operations with histogram recording.

**Features:**
- Automatic start/stop timing
- Exception handling
- Multiple timing units
- Integration with histograms

**Usage Examples:**
```python
from nwws.metrics import TimingContext

# Basic timing context
with TimingContext(collector, "operation_duration_ms") as timer:
    perform_operation()
    # Duration automatically recorded in milliseconds

# Timing with labels
with TimingContext(collector, "db_query_duration_ms", labels={"query": "select"}) as timer:
    execute_database_query()

# Custom histogram buckets
timing_histogram = Histogram.create_default_timing_histogram()
with TimingContext(collector, "custom_timing", histogram=timing_histogram) as timer:
    custom_operation()
```

## Standard Metrics

The NWWS2MQTT application defines standard metrics that are automatically collected:

### Application Metrics
- `nwws2mqtt_application_info`: Application version and metadata
- `nwws2mqtt_application_uptime_seconds`: Application uptime
- `nwws2mqtt_connection_status`: XMPP connection status
- `nwws2mqtt_connection_uptime_seconds`: Current connection uptime

### Message Processing Metrics
- `nwws2mqtt_messages_received_total`: Total messages received
- `nwws2mqtt_messages_processed_total`: Total messages processed
- `nwws2mqtt_messages_failed_total`: Total failed messages
- `nwws2mqtt_message_processing_success_rate`: Processing success rate

### Product Classification Metrics
- `nwws2mqtt_wmo_codes_total`: Count by WMO product code
- `nwws2mqtt_sources_total`: Count by weather office source
- `nwws2mqtt_afos_codes_total`: Count by AFOS code

### Output Handler Metrics
- `nwws2mqtt_output_handler_status`: Handler connection status
- `nwws2mqtt_output_handler_published_total`: Messages published per handler
- `nwws2mqtt_output_handler_success_rate`: Handler success rate

## Performance Considerations

### Memory Usage
- **Registry**: O(n) where n is the number of unique metric keys
- **Histograms**: O(b) where b is the number of buckets
- **Labels**: Each unique label combination creates a separate metric instance

### Thread Safety
All metric operations are thread-safe:
- Registry operations use appropriate locking
- Atomic operations for counter increments
- Safe concurrent access to metric values

### Performance Optimization
- Lazy metric creation reduces memory overhead
- Efficient label hashing for fast metric lookup
- Batch operations for bulk metric updates

## Configuration

### Registry Configuration
```python
from nwws.metrics import MetricRegistry

# Create registry with custom settings
registry = MetricRegistry()

# Configure default histogram buckets
default_buckets = [0.001, 0.01, 0.1, 1.0, 10.0]
```

### Collector Configuration
```python
from nwws.metrics import MetricsCollector

# Create collector with registry
collector = MetricsCollector(registry)

# Configure timing units
collector.set_default_timing_unit("milliseconds")
```

### Exporter Configuration
```python
from nwws.metrics import PrometheusExporter

# Create exporter
exporter = PrometheusExporter(registry)

# Configure export options
exporter.set_name_prefix("nwws2mqtt_")
exporter.set_help_text_override({"custom_metric": "Custom help text"})
```

## Integration Examples

### FastAPI Integration
```python
from fastapi import FastAPI, Response
from nwws.metrics import MetricRegistry, PrometheusExporter

app = FastAPI()
registry = MetricRegistry()
exporter = PrometheusExporter(registry)

@app.middleware("http")
async def metrics_middleware(request, call_next):
    # Increment request counter
    registry.increment_counter("http_requests_total", 
                             labels={"method": request.method})
    
    # Time the request
    with registry.timer("http_request_duration_seconds"):
        response = await call_next(request)
    
    return response

@app.get("/metrics")
async def prometheus_metrics():
    return Response(
        content=exporter.export(),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )
```

### Custom Metric Collection
```python
from nwws.metrics import MetricsCollector

class WeatherStationMetrics:
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        
        # Initialize metrics
        self.collector.registry.get_or_create_metric(
            "weather_readings_total",
            MetricType.COUNTER,
            "Total weather readings processed"
        )
        
    def record_temperature_reading(self, temperature: float, station: str):
        # Record the reading
        self.collector.increment("weather_readings_total", 
                               labels={"station": station, "type": "temperature"})
        
        # Record the value
        self.collector.set_gauge("current_temperature", 
                               temperature, 
                               labels={"station": station})
```

## Error Handling

The metrics system includes comprehensive error handling:

### Metric Registration Errors
```python
try:
    registry.get_or_create_metric("invalid_metric", "invalid_type")
except ValueError as e:
    logger.error("Failed to create metric", error=str(e))
```

### Export Errors
```python
try:
    metrics_text = exporter.export()
except Exception as e:
    logger.error("Failed to export metrics", error=str(e))
    # Return cached or empty metrics
```

### Collection Errors
```python
try:
    collector.increment("missing_metric")
except KeyError as e:
    logger.warning("Metric not found", metric=str(e))
```

## Best Practices

1. **Metric Naming**: Use clear, descriptive names with consistent units
2. **Label Management**: Keep label cardinality reasonable to avoid memory issues
3. **Histogram Buckets**: Choose appropriate buckets based on expected value distribution
4. **Error Handling**: Always handle metric collection errors gracefully
5. **Performance**: Avoid creating metrics in hot code paths
6. **Documentation**: Document custom metrics with clear help text

## Monitoring and Alerting

### Prometheus Queries
```promql
# Request rate
rate(nwws2mqtt_messages_processed_total[5m])

# Error rate
rate(nwws2mqtt_messages_failed_total[5m]) / rate(nwws2mqtt_messages_received_total[5m])

# 99th percentile latency
histogram_quantile(0.99, rate(nwws2mqtt_request_duration_seconds_bucket[5m]))
```

### Alert Rules
```yaml
groups:
  - name: nwws2mqtt
    rules:
      - alert: HighErrorRate
        expr: rate(nwws2mqtt_messages_failed_total[5m]) / rate(nwws2mqtt_messages_received_total[5m]) > 0.05
        for: 2m
        annotations:
          summary: "High error rate in NWWS2MQTT"
          
      - alert: ConnectionDown
        expr: nwws2mqtt_connection_status == 0
        for: 1m
        annotations:
          summary: "NWWS2MQTT connection is down"
```

## Testing

### Unit Testing Metrics
```python
import pytest
from nwws.metrics import MetricRegistry, MetricType

def test_counter_increment():
    registry = MetricRegistry()
    
    # Create counter
    registry.get_or_create_metric("test_counter", MetricType.COUNTER)
    
    # Increment and verify
    registry.increment_counter("test_counter", 5.0)
    metric = registry.get_metric("test_counter")
    assert metric.value == 5.0

def test_histogram_observation():
    registry = MetricRegistry()
    histogram = Histogram([1.0, 5.0, 10.0])
    
    registry.get_or_create_metric("test_histogram", MetricType.HISTOGRAM, value=histogram)
    registry.observe_histogram("test_histogram", 2.5)
    
    metric = registry.get_metric("test_histogram")
    assert metric.value.count == 1
```

This metrics package provides a robust foundation for observability in the NWWS2MQTT system, enabling comprehensive monitoring and performance analysis.