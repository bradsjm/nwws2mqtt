# pyright: strict
"""Base metrics collectors with common functionality."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from .registry import MetricRegistry


class MetricsCollector:
    """Base class for collecting metrics with common patterns."""

    def __init__(self, registry: MetricRegistry, prefix: str = "") -> None:
        """Initialize the metrics collector.

        Args:
            registry: The metric registry to store metrics in
            prefix: Optional prefix to add to all metric names

        """
        self.registry = registry
        self.prefix = prefix

    def _metric_name(self, name: str) -> str:
        """Generate a metric name with optional prefix."""
        return f"{self.prefix}_{name}" if self.prefix else name

    def increment_counter(
        self,
        name: str,
        amount: float = 1,
        labels: dict[str, str] | None = None,
        help_text: str = "",
    ) -> None:
        """Increment a counter metric."""
        metric_name = self._metric_name(name)
        metric = self.registry.get_or_create_counter(metric_name, help_text, labels)
        metric.increment(amount)

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
        help_text: str = "",
    ) -> None:
        """Set a gauge metric value."""
        metric_name = self._metric_name(name)
        metric = self.registry.get_or_create_gauge(metric_name, help_text, labels)
        metric.set_value(value)

    def observe_histogram(
        self,
        name: str,
        value: float,
        buckets: list[float] | None = None,
        labels: dict[str, str] | None = None,
        help_text: str = "",
    ) -> None:
        """Record an observation in a histogram."""
        metric_name = self._metric_name(name)
        metric = self.registry.get_or_create_histogram(
            metric_name, buckets, help_text, labels
        )
        metric.observe(value)

    def record_duration_ms(
        self,
        name: str,
        duration_ms: float,
        labels: dict[str, str] | None = None,
        help_text: str = "",
    ) -> None:
        """Record a duration in milliseconds using a histogram."""
        self.observe_histogram(
            f"{name}_duration_ms",
            duration_ms,
            labels=labels,
            help_text=help_text or f"Duration in milliseconds for {name}",
        )

    def record_operation(
        self,
        operation_name: str,
        *,
        success: bool = True,
        duration_ms: float | None = None,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record an operation with success/failure counts and optional timing."""
        base_labels = labels or {}

        # Record operation count
        operation_labels = {**base_labels, "operation": operation_name}
        self.increment_counter(
            "operations_total",
            labels=operation_labels,
            help_text="Total number of operations",
        )

        # Record success/failure
        result_labels = {
            **operation_labels,
            "result": "success" if success else "failure",
        }
        self.increment_counter(
            "operation_results_total",
            labels=result_labels,
            help_text="Total number of operation results by type",
        )

        # Record duration if provided
        if duration_ms is not None:
            self.record_duration_ms(
                f"operation_{operation_name}",
                duration_ms,
                labels=base_labels,
                help_text=f"Duration for {operation_name} operations",
            )

    def record_error(
        self,
        error_type: str,
        operation: str = "",
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record an error occurrence."""
        error_labels = labels or {}
        if operation:
            error_labels["operation"] = operation
        error_labels["error_type"] = error_type

        self.increment_counter(
            "errors_total",
            labels=error_labels,
            help_text="Total number of errors by type",
        )

    def update_status(
        self,
        component: str,
        status: str,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Update a component status gauge (0 or 1 for binary status)."""
        status_labels = {**(labels or {}), "component": component}
        status_value = (
            1.0 if status.lower() in ("up", "connected", "healthy", "true") else 0.0
        )

        self.set_gauge(
            "component_status",
            status_value,
            labels=status_labels,
            help_text="Component status (1=up/healthy, 0=down/unhealthy)",
        )

    def get_metric_value(
        self,
        name: str,
        labels: dict[str, str] | None = None,
    ) -> float | int | None:
        """Get the current value of a metric."""
        metric_name = self._metric_name(name)
        return self.registry.get_metric_value(metric_name, labels)


class TimingContext:
    """Context manager for timing operations."""

    def __init__(
        self,
        collector: MetricsCollector,
        operation_name: str,
        labels: dict[str, str] | None = None,
        *,
        record_success: bool = True,
    ) -> None:
        """Initialize timing context.

        Args:
            collector: The metrics collector to use
            operation_name: Name of the operation being timed
            labels: Optional labels for the metrics
            record_success: Whether to record operation success/failure

        """
        self.collector = collector
        self.operation_name = operation_name
        self.labels = labels
        self.record_success = record_success
        self.start_time: float = 0.0
        self.success = True

    def __enter__(self) -> Self:
        """Start timing the operation."""
        self.start_time = time.time()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """End timing and record metrics."""
        duration_ms = (time.time() - self.start_time) * 1000.0

        if exc_type is not None:
            self.success = False

        if self.record_success:
            self.collector.record_operation(
                self.operation_name,
                success=self.success,
                duration_ms=duration_ms,
                labels=self.labels,
            )
        else:
            self.collector.record_duration_ms(
                self.operation_name,
                duration_ms,
                labels=self.labels,
            )

    def mark_failure(self) -> None:
        """Mark the operation as failed."""
        self.success = False
