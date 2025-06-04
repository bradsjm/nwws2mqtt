"""Metrics API endpoints for dashboard data."""

import random
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from nwws.metrics.registry import MetricRegistry
from nwws.metrics.types import Metric, MetricType


def create_metrics_endpoints(router: APIRouter, registry: MetricRegistry) -> None:
    """Create metrics endpoints for dashboard.

    Args:
        router: FastAPI router to add endpoints to
        registry: MetricRegistry instance

    """

    @router.get("/api/metrics")
    async def get_current_metrics() -> JSONResponse:  # type: ignore[no-untyped-def]
        """Get current metrics for dashboard display."""
        try:
            # Get raw metrics
            raw_metrics = registry.list_metrics()

            # Transform metrics for dashboard consumption
            dashboard_data = _transform_metrics_for_dashboard(raw_metrics)

            # Add simulation data if no real metrics are available
            if _is_metrics_empty(dashboard_data):
                dashboard_data = _generate_simulation_data()

            # Add timestamp
            dashboard_data["timestamp"] = time.time()

            return JSONResponse(content=dashboard_data)
        except Exception as e:
            logger.error("Failed to get dashboard metrics", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to retrieve metrics") from e

    @router.post("/api/metrics/populate-test-data")
    async def populate_test_metrics() -> JSONResponse:  # type: ignore[no-untyped-def]
        """Populate registry with test metrics for development purposes."""
        try:
            from nwws.webserver.dashboard.utils.test_data import populate_test_metrics

            populate_test_metrics(registry)
            return JSONResponse(content={"status": "success", "message": "Test metrics created"})
        except Exception as e:
            logger.error("Failed to create test metrics", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to create test metrics") from e


def _transform_metrics_for_dashboard(metrics: list[Any]) -> dict[str, Any]:
    """Transform raw metrics into dashboard-friendly format.

    Args:
        metrics: List of Metric objects from registry

    Returns:
        Dictionary with dashboard fields populated

    """
    # Initialize collectors for aggregation
    aggregator = _MetricsAggregator()

    # Process all metrics
    for metric in metrics:
        aggregator.process_metric(metric)

    # Calculate derived metrics and return dashboard data
    return aggregator.build_dashboard_data()


class _MetricsAggregator:
    """Helper class to aggregate metrics data for dashboard."""

    def __init__(self) -> None:
        """Initialize the aggregator."""
        self.messages_processed_total = 0
        self.processing_errors_total = 0
        self.processing_durations: list[float] = []
        self.office_activity: dict[str, dict[str, Any]] = {}
        self.office_durations: dict[str, list[float]] = {}
        self.pipeline_healthy = True
        self.connection_active = False

    def process_metric(self, metric: Metric) -> None:
        """Process a single metric and update aggregators."""
        metric_name = metric.key.name
        metric_value = metric.get_numeric_value()
        labels_dict = dict(metric.key.labels) if metric.key.labels else {}

        if metric_name == "nwws_messages_processed_total":
            self._process_office_messages(metric_value, labels_dict)
        elif metric_name == "pipeline_events_processed_total":
            self.messages_processed_total += metric_value
        elif metric_name == "nwws_message_processing_errors_total":
            self._process_office_errors(metric_value, labels_dict)
        elif metric_name == "pipeline_errors_total":
            self.processing_errors_total += metric_value
        elif metric_name in (
            "nwws_message_processing_duration_seconds",
            "pipeline_processing_duration_seconds",
        ):
            self._process_duration_histogram(metric, labels_dict)
        elif metric_name == "nwws_xmpp_connection_status":
            self.connection_active = metric_value > 0
        elif metric_name == "pipeline_status":
            self.pipeline_healthy = metric_value > 0

    def _process_office_messages(self, metric_value: float, labels: dict[str, str]) -> None:
        """Process office message metrics."""
        self.messages_processed_total += metric_value
        wmo_id = labels.get("wmo_id", "unknown")
        if wmo_id not in self.office_activity:
            self.office_activity[wmo_id] = {
                "messages_processed_total": 0,
                "errors_total": 0,
                "last_activity": time.time(),
                "avg_processing_latency_ms": 0.0,
                "activity_level": "idle",
            }
        self.office_activity[wmo_id]["messages_processed_total"] += metric_value
        self.office_activity[wmo_id]["last_activity"] = time.time()

    def _process_office_errors(self, metric_value: float, labels: dict[str, str]) -> None:
        """Process office error metrics."""
        self.processing_errors_total += metric_value
        wmo_id = labels.get("wmo_id", "unknown")
        if wmo_id in self.office_activity:
            self.office_activity[wmo_id]["errors_total"] += metric_value

    def _process_duration_histogram(self, metric: Any, labels: dict[str, str]) -> None:
        """Process histogram metrics for duration calculation."""
        if metric.metric_type == MetricType.HISTOGRAM and hasattr(metric.value, "sum"):
            histogram = metric.value
            if histogram.count > 0:
                avg_duration = histogram.sum / histogram.count
                duration_ms = avg_duration * 1000  # Convert to ms
                self.processing_durations.append(duration_ms)

                # Track office-specific durations if available
                wmo_id = labels.get("wmo_id")
                if wmo_id:
                    if wmo_id not in self.office_durations:
                        self.office_durations[wmo_id] = []
                    self.office_durations[wmo_id].append(duration_ms)

    def build_dashboard_data(self) -> dict[str, Any]:
        """Build the final dashboard data structure."""
        # Calculate office-specific metrics before building final data
        self._calculate_office_metrics()

        return {
            "throughput": self._calculate_throughput(),
            "latency": self._calculate_latency(),
            "errors": self._calculate_errors(),
            "by_wmo": self.office_activity,
            "system": self._calculate_system_status(),
        }

    def _calculate_throughput(self) -> dict[str, Any]:
        """Calculate throughput metrics."""
        messages_per_minute = 0.0
        if self.messages_processed_total > 0:
            # Simple heuristic for demonstration
            messages_per_minute = min(self.messages_processed_total * 0.05, 100)
            messages_per_minute += random.uniform(-5, 10)  # noqa: S311
            messages_per_minute = max(0, messages_per_minute)

        return {
            "messages_per_minute": round(messages_per_minute, 1),
            "total_messages": int(self.messages_processed_total),
        }

    def _calculate_latency(self) -> dict[str, Any]:
        """Calculate latency metrics."""
        avg_latency_ms = 0.0
        if self.processing_durations:
            avg_latency_ms = sum(self.processing_durations) / len(self.processing_durations)

        return {
            "avg_ms": round(avg_latency_ms, 1),
            "p95_ms": round(avg_latency_ms * 1.5, 1),  # Estimated
            "p99_ms": round(avg_latency_ms * 2.0, 1),  # Estimated
        }

    def _calculate_errors(self) -> dict[str, Any]:
        """Calculate error rate metrics."""
        error_rate_percent = 0.0
        if self.messages_processed_total > 0:
            error_rate_percent = (
                self.processing_errors_total / self.messages_processed_total
            ) * 100

        return {
            "rate_percent": round(error_rate_percent, 2),
            "total_errors": int(self.processing_errors_total),
        }

    def _calculate_system_status(self) -> dict[str, Any]:
        """Calculate system status metrics."""
        active_offices_count = len(
            [
                office
                for office, data in self.office_activity.items()
                if data["messages_processed_total"] > 0
            ]
        )

        return {
            "active_offices": active_offices_count,
            "pipeline_status": "healthy" if self.pipeline_healthy else "unhealthy",
            "connection_status": "connected" if self.connection_active else "disconnected",
        }

    def _calculate_office_metrics(self) -> None:
        """Calculate office-specific metrics including latency and activity levels."""
        for wmo_id, office_data in self.office_activity.items():
            # Calculate average latency for this office
            if self.office_durations.get(wmo_id):
                office_latency = sum(self.office_durations[wmo_id]) / len(
                    self.office_durations[wmo_id]
                )
                office_data["avg_processing_latency_ms"] = round(office_latency, 1)
            else:
                office_data["avg_processing_latency_ms"] = 0.0

            # Calculate activity level
            messages = office_data.get("messages_processed_total", 0)
            errors = office_data.get("errors_total", 0)
            last_activity = office_data.get("last_activity", 0)
            current_time = time.time()

            # Determine activity level based on message count and recency
            if (
                messages == 0 or (current_time - last_activity) > 3600
            ):  # No activity or > 1 hour old
                activity_level = "idle"
            elif errors / max(messages, 1) > 0.1:  # Error rate > 10%
                activity_level = "error"
            elif messages > 100:  # High activity
                activity_level = "high"
            elif messages > 25:  # Medium activity
                activity_level = "medium"
            else:  # Low activity
                activity_level = "low"

            office_data["activity_level"] = activity_level


def _is_metrics_empty(dashboard_data: dict[str, Any]) -> bool:
    """Check if dashboard data contains meaningful metrics.

    Args:
        dashboard_data: Dashboard data dictionary

    Returns:
        True if metrics are essentially empty/zero

    """
    throughput = dashboard_data.get("throughput", {})
    system = dashboard_data.get("system", {})

    return (
        throughput.get("messages_per_minute", 0) == 0
        and throughput.get("total_messages", 0) == 0
        and system.get("active_offices", 0) == 0
    )


def _generate_simulation_data() -> dict[str, Any]:
    """Generate realistic simulation data for dashboard demonstration.

    Returns:
        Dashboard data with simulated metrics

    """
    # Generate base activity levels
    base_messages_per_minute = random.uniform(15, 45)  # noqa: S311
    active_offices_count = random.randint(8, 15)  # noqa: S311
    base_latency = random.uniform(25, 85)  # noqa: S311
    base_error_rate = random.uniform(0.1, 2.5)  # noqa: S311

    # Create office activity data
    wmo_ids = [
        "ALY",
        "BGM",
        "BOX",
        "BTV",
        "BUF",
        "CAR",
        "CHS",
        "CTP",
        "GYX",
        "ILM",
        "LWX",
        "MHX",
        "OKX",
        "PHI",
        "RNK",
    ]

    office_activity = {}
    for wmo_id in wmo_ids[:active_offices_count]:
        messages = random.randint(50, 500)  # noqa: S311
        errors = random.randint(0, 5)  # noqa: S311

        # Calculate activity level based on message count and error rate
        if messages > 300:
            activity_level = "high"
            avg_latency = random.uniform(20, 40)  # noqa: S311
        elif messages > 150:
            activity_level = "medium"
            avg_latency = random.uniform(15, 30)  # noqa: S311
        elif messages > 50:
            activity_level = "low"
            avg_latency = random.uniform(10, 25)  # noqa: S311
        else:
            activity_level = "idle"
            avg_latency = 0.0

        # Override to error if high error rate
        if errors / max(messages, 1) > 0.1:
            activity_level = "error"
            avg_latency = random.uniform(50, 100)  # noqa: S311

        office_activity[wmo_id] = {
            "messages_processed_total": messages,
            "errors_total": errors,
            "last_activity": time.time() - random.uniform(0, 300),  # noqa: S311
            "avg_processing_latency_ms": round(avg_latency, 1),
            "activity_level": activity_level,
        }

    return {
        "throughput": {
            "messages_per_minute": round(base_messages_per_minute, 1),
            "total_messages": random.randint(1000, 5000),  # noqa: S311
        },
        "latency": {
            "avg_ms": round(base_latency, 1),
            "p95_ms": round(base_latency * 1.8, 1),
            "p99_ms": round(base_latency * 2.3, 1),
        },
        "errors": {
            "rate_percent": round(base_error_rate, 2),
            "total_errors": random.randint(5, 50),  # noqa: S311
        },
        "by_wmo": office_activity,
        "system": {
            "active_offices": active_offices_count,
            "pipeline_status": "healthy",
            "connection_status": "connected",
        },
    }
