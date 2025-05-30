# pyright: strict
"""Example HTTP endpoint for exposing metrics in production environments."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, Response

from nwws.metrics import (
    JSONExporter,
    MetricRegistry,
    MetricsCollector,
    PrometheusExporter,
)


class MetricsServer:
    """HTTP server for exposing application metrics."""

    def __init__(
        self, registry: MetricRegistry, host: str = "0.0.0.0", port: int = 8080
    ) -> None:
        """Initialize the metrics server."""
        self.registry = registry
        self.host = host
        self.port = port
        self.app = FastAPI(title="NWWS2MQTT Metrics", version="1.0.0")
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Set up HTTP routes for metrics endpoints."""

        @self.app.get("/metrics")
        def prometheus_metrics() -> Response:
            """Prometheus-compatible metrics endpoint."""
            exporter = PrometheusExporter(self.registry)
            return Response(
                content=exporter.export(), media_type=exporter.get_content_type()
            )

        @self.app.get("/metrics/json")
        def json_metrics() -> Response:
            """JSON format metrics endpoint."""
            exporter = JSONExporter(self.registry)
            return Response(
                content=exporter.export(), media_type=exporter.get_content_type()
            )

        @self.app.get("/health")
        def health_check() -> dict[str, str]:
            """Basic health check endpoint."""
            # Check if we have connection status metrics
            connection_status = self.registry.get_metric_value(
                "weather_wire_component_status",
                labels={"receiver": "weather_wire", "component": "connection"},
            )

            if connection_status == 1.0:
                return {"status": "healthy", "receiver": "connected"}
            if connection_status == 0.0:
                return {"status": "degraded", "receiver": "disconnected"}
            return {"status": "unknown", "receiver": "status_unknown"}

        @self.app.get("/health/ready")
        def readiness_check() -> dict[str, str]:
            """Kubernetes-style readiness check."""
            # Check if we have any metrics at all (indicates system is running)
            metrics_count = len(self.registry.list_metrics())

            if metrics_count > 0:
                return {"status": "ready"}
            return {"status": "not_ready"}

        @self.app.get("/")
        def root() -> dict[str, str]:
            """Root endpoint with available endpoints."""
            return {
                "service": "NWWS2MQTT Metrics",
                "endpoints": {
                    "/metrics": "Prometheus format metrics",
                    "/metrics/json": "JSON format metrics",
                    "/health": "Health check",
                    "/health/ready": "Readiness check",
                },
            }

    async def start(self) -> None:
        """Start the metrics server."""
        import uvicorn

        config = uvicorn.Config(
            app=self.app, host=self.host, port=self.port, log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


async def demo_metrics_server() -> None:
    """Demonstrate the metrics HTTP server with sample data."""
    # Create registry and add sample metrics
    registry = MetricRegistry()

    # Simulate weather wire receiver metrics
    receiver_collector = MetricsCollector(registry, prefix="weather_wire")
    receiver_labels = {"receiver": "weather_wire"}

    # Add connection status
    receiver_collector.update_status("connection", "connected", labels=receiver_labels)

    # Add some operation metrics
    for i in range(100):
        receiver_collector.record_operation(
            "message_processing",
            success=i < 95,  # 5% failure rate
            duration_ms=10.0 + (i % 20),
            labels=receiver_labels,
        )

    # Add pipeline metrics
    pipeline_collector = MetricsCollector(registry, prefix="weather_wire_pipeline")
    pipeline_labels = {"stage": "transform", "stage_id": "noaa_transformer"}

    for i in range(90):  # Some messages filtered out
        pipeline_collector.record_operation(
            "transform",
            success=True,
            duration_ms=5.0 + (i % 10),
            labels=pipeline_labels,
        )

    # Update queue size
    pipeline_collector.set_gauge("queue_size", 12, labels=pipeline_labels)

    # Add some delayed messages
    for i in range(10):
        receiver_collector.observe_histogram(
            "message_delay_ms", 100.0 + (i * 50), labels=receiver_labels
        )

    # Start the metrics server
    print("Starting metrics server on http://localhost:8080")
    print("Available endpoints:")
    print("  - http://localhost:8080/metrics (Prometheus format)")
    print("  - http://localhost:8080/metrics/json (JSON format)")
    print("  - http://localhost:8080/health (Health check)")
    print("  - http://localhost:8080/health/ready (Readiness check)")
    print("\nPress Ctrl+C to stop the server")

    server = MetricsServer(registry, host="127.0.0.1", port=8080)
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\nShutting down metrics server")


if __name__ == "__main__":
    asyncio.run(demo_metrics_server())
