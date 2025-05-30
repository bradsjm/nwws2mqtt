# pyright: strict
"""Example usage of the new metrics system."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path so we can import nwws modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nwws.metrics import (
    JSONExporter,
    LogExporter,
    MetricRegistry,
    MetricsCollector,
    PrometheusExporter,
    TimingContext,
)


async def example_basic_usage() -> None:
    """Demonstrate basic metrics usage."""
    # Create a metric registry
    registry = MetricRegistry()
    
    # Create a metrics collector with a prefix
    collector = MetricsCollector(registry, prefix="example_app")
    
    # Record some basic metrics
    collector.increment_counter(
        "requests_total",
        labels={"method": "GET", "endpoint": "/api/data"},
        help_text="Total number of HTTP requests",
    )
    
    collector.set_gauge(
        "active_connections",
        42,
        labels={"service": "api"},
        help_text="Number of active connections",
    )
    
    # Record timing data
    collector.observe_histogram(
        "request_duration_ms",
        150.5,
        labels={"method": "GET", "status": "200"},
        help_text="Request duration in milliseconds",
    )
    
    # Use the timing context manager
    with TimingContext(collector, "database_query", labels={"table": "users"}):
        # Simulate some work
        await asyncio.sleep(0.1)
        
    # Record operations with success/failure
    collector.record_operation(
        "user_creation",
        success=True,
        duration_ms=25.3,
        labels={"source": "api"},
    )
    
    # Record errors
    collector.record_error(
        "validation_error",
        operation="user_creation",
        labels={"field": "email"},
    )
    
    # Update component status
    collector.update_status(
        "database",
        "connected",
        labels={"host": "db-primary"},
    )
    
    print("Basic metrics recorded successfully!")


def example_exporters() -> None:
    """Demonstrate different metric exporters."""
    registry = MetricRegistry()
    collector = MetricsCollector(registry, prefix="weather_service")
    
    # Add some sample metrics
    collector.increment_counter("messages_processed", 150, labels={"type": "weather_alert"})
    collector.set_gauge("queue_size", 23, labels={"queue": "processing"})
    collector.observe_histogram("processing_time_ms", 45.2, labels={"processor": "noaa"})
    
    # Prometheus format
    prometheus_exporter = PrometheusExporter(registry)
    print("=== Prometheus Format ===")
    print(prometheus_exporter.export())
    
    # JSON format
    json_exporter = JSONExporter(registry)
    print("=== JSON Format ===")
    print(json_exporter.export())
    
    # Log format (would normally use a real logger)
    log_exporter = LogExporter(registry)
    print("=== Log Format ===")
    log_exporter.export()


def example_weather_wire_metrics() -> None:
    """Example of metrics similar to what WeatherWire would collect."""
    registry = MetricRegistry()
    receiver_collector = MetricsCollector(registry, prefix="weather_wire")
    pipeline_collector = MetricsCollector(registry, prefix="pipeline")
    
    # Simulate receiver metrics
    receiver_labels = {"receiver": "weather_wire"}
    
    # Connection metrics
    receiver_collector.record_operation(
        "connection",
        success=True,
        duration_ms=1250.0,
        labels=receiver_labels,
    )
    
    # Message processing
    for i in range(50):
        receiver_collector.record_operation(
            "message_processing",
            success=True,
            duration_ms=15.0 + (i * 0.5),  # Simulate varying processing times
            labels=receiver_labels,
        )
    
    # Some failures
    receiver_collector.record_operation(
        "message_processing",
        success=False,
        labels={**receiver_labels, "error": "parse_error"},
    )
    
    # Status updates
    receiver_collector.update_status("connection", "connected", labels=receiver_labels)
    receiver_collector.set_gauge("last_message_age_seconds", 5.2, labels=receiver_labels)
    
    # Pipeline metrics
    pipeline_labels = {"stage": "transform", "component": "noaa_transformer"}
    
    for i in range(45):  # Fewer processed due to some filtering
        pipeline_collector.record_operation(
            "transform",
            success=True,
            duration_ms=8.0 + (i * 0.2),
            labels=pipeline_labels,
        )
    
    pipeline_collector.set_gauge("queue_size", 12, labels=pipeline_labels)
    
    # Show summary
    print("=== Weather Wire Metrics Summary ===")
    summary = registry.get_registry_summary()
    
    print(f"Total metrics: {summary['total_metrics']}")
    print(f"Counters: {len(summary['counters'])}")
    print(f"Gauges: {len(summary['gauges'])}")
    print(f"Histograms: {len(summary['histograms'])}")
    
    # Export as Prometheus for monitoring
    exporter = PrometheusExporter(registry)
    metrics_file = Path("/tmp/weather_wire_metrics.txt")
    metrics_file.write_text(exporter.export())
    print("Metrics exported to /tmp/weather_wire_metrics.txt")


def example_performance_monitoring() -> None:
    """Example of using metrics for performance monitoring."""
    registry = MetricRegistry()
    collector = MetricsCollector(registry, prefix="performance_test")
    
    # Simulate different operation patterns
    operations = ["fast_op", "medium_op", "slow_op"]
    base_times = [5.0, 50.0, 200.0]  # milliseconds
    
    for op, base_time in zip(operations, base_times, strict=True):
        for i in range(100):
            # Add some variance
            duration = base_time + (i % 10) * 2.0
            success = i < 95  # 5% failure rate
            
            collector.record_operation(
                op,
                success=success,
                duration_ms=duration,
                labels={"batch": "test_batch_1"},
            )
    
    # Check some metrics
    print("=== Performance Monitoring Results ===")
    
    # Get operation counts
    for op in operations:
        total_ops = registry.get_metric_value(
            "performance_test_operations_total",
            labels={"operation": op, "batch": "test_batch_1"}
        )
        successful_ops = registry.get_metric_value(
            "performance_test_operation_results_total",
            labels={"operation": op, "result": "success", "batch": "test_batch_1"}
        )
        print(f"{op}: {successful_ops}/{total_ops} successful operations")
    
    # Export for analysis
    json_exporter = JSONExporter(registry)
    metrics_file = Path("/tmp/performance_metrics.json")
    metrics_file.write_text(json_exporter.export())
    print("Performance metrics exported to /tmp/performance_metrics.json")


async def main() -> None:
    """Run all examples."""
    print("=== NWWS2MQTT Metrics System Examples ===\n")
    
    print("1. Basic Usage:")
    await example_basic_usage()
    print()
    
    print("2. Different Export Formats:")
    example_exporters()
    print()
    
    print("3. Weather Wire Simulation:")
    example_weather_wire_metrics()
    print()
    
    print("4. Performance Monitoring:")
    example_performance_monitoring()
    print()
    
    print("Examples completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())