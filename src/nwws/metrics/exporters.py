# pyright: strict
"""Exporters for metrics to various backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .registry import MetricRegistry
    from .types import Metric


class MetricExporter(ABC):
    """Abstract base class for metric exporters."""

    def __init__(self, registry: MetricRegistry) -> None:
        """Initialize the exporter with a metric registry."""
        self.registry = registry

    @abstractmethod
    def export(self) -> str:
        """Export metrics in the format expected by the backend."""

    @abstractmethod
    def get_content_type(self) -> str:
        """Get the content type for the exported format."""


class PrometheusExporter(MetricExporter):
    """Exporter for Prometheus metrics format."""

    def export(self) -> str:
        """Export metrics in Prometheus exposition format."""
        lines: list[str] = []

        for metric in self.registry.list_metrics():
            lines.extend(self._format_metric(metric))

        return "\n".join(lines) + "\n"

    def get_content_type(self) -> str:
        """Get the content type for Prometheus format."""
        return "text/plain; version=0.0.4; charset=utf-8"

    def _format_metric(self, metric: Metric) -> list[str]:
        """Format a single metric for Prometheus."""
        lines: list[str] = []

        # Add help text if available
        if metric.help_text:
            lines.append(f"# HELP {metric.key.name} {metric.help_text}")

        # Add type
        prometheus_type = self._get_prometheus_type(metric)
        lines.append(f"# TYPE {metric.key.name} {prometheus_type}")

        # Add metric lines
        if hasattr(metric.value, "buckets"):  # Histogram
            lines.extend(self._format_histogram(metric))
        else:  # Counter or Gauge
            labels_str = self._format_labels(metric.key.labels_dict())
            lines.append(f"{metric.key.name}{labels_str} {metric.value}")

        return lines

    def _get_prometheus_type(self, metric: Metric) -> str:
        """Get the Prometheus type string for a metric."""
        from .types import MetricType

        type_mapping = {
            MetricType.COUNTER: "counter",
            MetricType.GAUGE: "gauge",
            MetricType.HISTOGRAM: "histogram",
        }
        return type_mapping.get(metric.metric_type, "untyped")

    def _format_histogram(self, metric: Metric) -> list[str]:
        """Format a histogram metric for Prometheus."""
        from .types import Histogram

        lines: list[str] = []
        base_labels = metric.key.labels_dict()

        if not isinstance(metric.value, Histogram):
            return lines

        histogram = metric.value

        # Bucket lines
        for bucket_upper, count in histogram.get_buckets_with_counts():
            bucket_labels = {**base_labels, "le": str(bucket_upper)}
            labels_str = self._format_labels(bucket_labels)
            lines.append(f"{metric.key.name}_bucket{labels_str} {count}")

        # Sum and count
        labels_str = self._format_labels(base_labels)
        lines.append(f"{metric.key.name}_sum{labels_str} {histogram.sum}")
        lines.append(f"{metric.key.name}_count{labels_str} {histogram.count}")

        return lines

    def _format_labels(self, labels: dict[str, str]) -> str:
        """Format labels for Prometheus."""
        if not labels:
            return ""

        label_pairs = [f'{key}="{value}"' for key, value in sorted(labels.items())]
        return "{" + ",".join(label_pairs) + "}"


class JSONExporter(MetricExporter):
    """Exporter for JSON metrics format."""

    def export(self) -> str:
        """Export metrics in JSON format."""
        import json

        metrics_data = {
            "timestamp": self._get_current_timestamp(),
            "metrics": [metric.to_dict() for metric in self.registry.list_metrics()],
        }

        return json.dumps(metrics_data, indent=2)

    def get_content_type(self) -> str:
        """Get the content type for JSON format."""
        return "application/json"

    def _get_current_timestamp(self) -> float:
        """Get current timestamp."""
        import time

        return time.time()


class OpenTelemetryExporter(MetricExporter):
    """Exporter for OpenTelemetry metrics format."""

    def export(self) -> str:
        """Export metrics in OpenTelemetry format."""
        # This would integrate with OpenTelemetry SDK
        # For now, return JSON format as placeholder
        return JSONExporter(self.registry).export()

    def get_content_type(self) -> str:
        """Get the content type for OpenTelemetry format."""
        return "application/json"


class LogExporter(MetricExporter):
    """Exporter that logs metrics using structured logging."""

    def __init__(self, registry: MetricRegistry, logger: Any = None) -> None:
        """Initialize with registry and optional logger."""
        super().__init__(registry)
        self.logger = logger

    def export(self) -> str:
        """Export metrics by logging them."""
        summary = self.registry.get_registry_summary()

        if self.logger:
            self.logger.info("metrics_export", **summary)
        else:
            # Fallback - could integrate with loguru or other logging
            import json
            import sys

            sys.stdout.write(json.dumps(summary, indent=2) + "\n")

        return ""

    def get_content_type(self) -> str:
        """Get the content type (not applicable for logging)."""
        return "text/plain"
