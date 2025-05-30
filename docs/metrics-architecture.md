# NWWS2MQTT Metrics Architecture

## Overview

The NWWS2MQTT application uses a modern, production-ready metrics system designed for observability and monitoring integration. The architecture has been simplified to eliminate redundant wrapper classes and provide a clean, direct approach to metrics collection.

## Architecture Components

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Application   │───▶│  MetricsCollector │───▶│  MetricRegistry │
│   Components    │    │  (with prefix)    │    │  (thread-safe)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                                               ┌─────────────────┐
                                               │    Exporters    │
                                               │                 │
                                               │ • Prometheus    │
                                               │ • JSON          │
                                               │ • Structured    │
                                               │   Logging       │
                                               └─────────────────┘
```

### Key Classes

1. **MetricRegistry**: Thread-safe central storage for all metrics
2. **MetricsCollector**: High-level interface for recording metrics with prefixes
3. **PipelineStatsCollector**: Pipeline-specific metrics collection
4. **WeatherWireStatsCollector**: Receiver-specific metrics collection
5. **Exporters**: Pluggable backends for different monitoring systems

## Simplified Design Principles

### Eliminated Redundancy
- **Removed**: `PipelineStats` wrapper class
- **Removed**: Generic `StatsCollector` wrapper
- **Result**: Direct usage of `MetricsCollector` with appropriate prefixes

### Unified Storage
- Single `MetricRegistry` shared across all components
- Thread-safe concurrent access
- Consistent metric naming and labeling

### Clear Separation of Concerns
- **Registry**: Storage and retrieval
- **Collectors**: High-level recording interfaces
- **Exporters**: Format-specific output

## Component Details

### MetricRegistry
```python
registry = MetricRegistry()
# Thread-safe storage for all metrics
# Supports counters, gauges, and histograms
# Provides enumeration and summary capabilities
```

### MetricsCollector
```python
collector = MetricsCollector(registry, prefix="weather_wire")
# High-level interface with automatic prefixing
# Common patterns: operations, errors, status updates
# Built-in timing context managers
```

### PipelineStatsCollector
```python
pipeline_stats = PipelineStatsCollector(registry, "pipeline_id")
# Pipeline-specific metrics collection
# Processing times, throughput, queue sizes
# Stage-based labeling and error tracking
```

### WeatherWireStatsCollector
```python
receiver_stats = WeatherWireStatsCollector(registry, "receiver_id")
# Receiver-specific metrics collection
# Connection status, message processing, delays
# Authentication and error tracking
```

## Metric Types and Patterns

### Counters
Monotonically increasing values for event counting:
```python
collector.increment_counter(
    "messages_processed",
    labels={"type": "weather_alert"}
)
```

### Gauges
Current values that can increase or decrease:
```python
collector.set_gauge(
    "queue_size", 
    42, 
    labels={"stage": "transform"}
)
```

### Histograms
Distribution tracking with configurable buckets:
```python
collector.observe_histogram(
    "processing_duration_ms",
    125.5,
    labels={"operation": "parse"}
)
```

### High-Level Operations
Structured operation tracking:
```python
collector.record_operation(
    "message_processing",
    success=True,
    duration_ms=25.3,
    labels={"source": "weather_wire"}
)
```

## Production Integration

### Prometheus Export
```python
exporter = PrometheusExporter(registry)
metrics_text = exporter.export()
# Expose via HTTP endpoint for scraping
```

### Health Monitoring
```python
# Connection status
connection_status = registry.get_metric_value(
    "weather_wire_component_status",
    labels={"component": "connection"}
)

# Service health based on metrics
healthy = connection_status == 1.0
```

### Structured Logging
```python
log_exporter = LogExporter(registry, logger)
log_exporter.export()  # Periodic metric snapshots
```

## Application Flow

### Initialization
```python
# 1. Create shared registry
registry = MetricRegistry()

# 2. Create component-specific collectors
pipeline_stats = PipelineStatsCollector(registry, "weather_wire_pipeline")
receiver_stats = WeatherWireStatsCollector(registry, "weather_wire")

# 3. Pass collectors to components
pipeline = Pipeline(..., stats_collector=pipeline_stats)
receiver = WeatherWire(..., stats_collector=receiver_stats)
```

### Runtime Metrics
```python
# Pipeline records processing metrics
pipeline_stats.record_processing_time(event_id, stage, stage_id, duration_ms)

# Receiver records connection and message metrics
receiver_stats.record_connection_success(duration_ms)
receiver_stats.record_message_received(processing_time)
```

### Export and Monitoring
```python
# Get comprehensive stats
summary = registry.get_registry_summary()

# Export for monitoring systems
prometheus_data = PrometheusExporter(registry).export()
json_data = JSONExporter(registry).export()
```

## Benefits of Simplified Architecture

### Performance
- Reduced object allocation overhead
- Direct metric access without wrapper layers
- Thread-safe operations with minimal locking

### Maintainability
- Clear component responsibilities
- Consistent metric naming patterns
- Easy to add new metric types or exporters

### Observability
- Unified view of all application metrics
- Consistent labeling for dimensional analysis
- Multiple export formats for different monitoring stacks

### Production Readiness
- Thread-safe concurrent access
- Prometheus-compatible output
- Health check integration
- Structured logging support

## Migration Benefits

The simplified architecture provides:
1. **Elimination of redundant wrapper classes**
2. **Direct access to modern metrics capabilities**
3. **Consistent dimensional metrics with labels**
4. **Multi-backend export support**
5. **Production-ready monitoring integration**

This design supports the full range of production monitoring needs while maintaining simplicity and performance.