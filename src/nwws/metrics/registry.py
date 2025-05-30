# pyright: strict
"""Metric registry for storing and managing all application metrics."""

from __future__ import annotations

import threading
from typing import Any

from .types import Histogram, Metric, MetricKey, MetricType


class MetricRegistry:
    """Thread-safe registry for storing and managing metrics."""

    def __init__(self) -> None:
        """Initialize the metric registry."""
        self._metrics: dict[MetricKey, Metric] = {}
        self._lock = threading.RLock()

    def get_or_create_counter(
        self,
        name: str,
        help_text: str = "",
        labels: dict[str, str] | None = None,
    ) -> Metric:
        """Get or create a counter metric."""
        key = MetricKey.create(name, labels)
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = Metric(
                    key=key,
                    metric_type=MetricType.COUNTER,
                    value=0.0,
                    help_text=help_text,
                )
            metric = self._metrics[key]
            if metric.metric_type != MetricType.COUNTER:
                error_msg = (
                    f"Metric {name} already exists with type {metric.metric_type.name}"
                )
                raise ValueError(error_msg)
            return metric

    def get_or_create_gauge(
        self,
        name: str,
        help_text: str = "",
        labels: dict[str, str] | None = None,
    ) -> Metric:
        """Get or create a gauge metric."""
        key = MetricKey.create(name, labels)
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = Metric(
                    key=key,
                    metric_type=MetricType.GAUGE,
                    value=0.0,
                    help_text=help_text,
                )
            metric = self._metrics[key]
            if metric.metric_type != MetricType.GAUGE:
                error_msg = (
                    f"Metric {name} already exists with type {metric.metric_type.name}"
                )
                raise ValueError(error_msg)
            return metric

    def get_or_create_histogram(
        self,
        name: str,
        buckets: list[float] | None = None,
        help_text: str = "",
        labels: dict[str, str] | None = None,
    ) -> Metric:
        """Get or create a histogram metric."""
        key = MetricKey.create(name, labels)
        with self._lock:
            if key not in self._metrics:
                histogram_buckets = (
                    buckets or Histogram.create_default_timing_histogram().buckets
                )
                self._metrics[key] = Metric(
                    key=key,
                    metric_type=MetricType.HISTOGRAM,
                    value=Histogram(buckets=histogram_buckets),
                    help_text=help_text,
                )
            metric = self._metrics[key]
            if metric.metric_type != MetricType.HISTOGRAM:
                error_msg = (
                    f"Metric {name} already exists with type {metric.metric_type.name}"
                )
                raise ValueError(error_msg)
            return metric

    def increment_counter(
        self,
        name: str,
        amount: float = 1,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Increment a counter metric, creating it if it doesn't exist."""
        metric = self.get_or_create_counter(name, labels=labels)
        metric.increment(amount)

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Set a gauge metric value, creating it if it doesn't exist."""
        metric = self.get_or_create_gauge(name, labels=labels)
        metric.set_value(value)

    def observe_histogram(
        self,
        name: str,
        value: float,
        buckets: list[float] | None = None,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record an observation in a histogram, creating it if it doesn't exist."""
        metric = self.get_or_create_histogram(name, buckets=buckets, labels=labels)
        metric.observe(value)

    def get_metric(
        self, name: str, labels: dict[str, str] | None = None
    ) -> Metric | None:
        """Get a metric by name and labels."""
        key = MetricKey.create(name, labels)
        with self._lock:
            return self._metrics.get(key)

    def get_metric_value(
        self,
        name: str,
        labels: dict[str, str] | None = None,
    ) -> float | int | None:
        """Get the numeric value of a metric."""
        metric = self.get_metric(name, labels)
        return metric.get_numeric_value() if metric else None

    def list_metrics(self) -> list[Metric]:
        """Get a list of all registered metrics."""
        with self._lock:
            return list(self._metrics.values())

    def list_metrics_by_name(self, name: str) -> list[Metric]:
        """Get all metrics with the given name (different label combinations)."""
        with self._lock:
            return [
                metric for metric in self._metrics.values() if metric.key.name == name
            ]

    def list_metric_names(self) -> set[str]:
        """Get a set of all metric names."""
        with self._lock:
            return {metric.key.name for metric in self._metrics.values()}

    def get_registry_summary(self) -> dict[str, Any]:
        """Get a summary of all metrics in the registry."""
        with self._lock:
            summary: dict[str, Any] = {
                "total_metrics": len(self._metrics),
                "counters": {},
                "gauges": {},
                "histograms": {},
            }

            for metric in self._metrics.values():
                metric_dict = metric.to_dict()

                if metric.metric_type == MetricType.COUNTER:
                    summary["counters"][metric.key.name] = metric_dict
                elif metric.metric_type == MetricType.GAUGE:
                    summary["gauges"][metric.key.name] = metric_dict
                elif metric.metric_type == MetricType.HISTOGRAM:
                    summary["histograms"][metric.key.name] = metric_dict

            return summary

    def reset_all(self) -> None:
        """Reset all metrics to their initial values."""
        with self._lock:
            for metric in self._metrics.values():
                if metric.metric_type in (MetricType.COUNTER, MetricType.GAUGE):
                    metric.value = 0.0
                elif metric.metric_type == MetricType.HISTOGRAM and isinstance(
                    metric.value, Histogram
                ):
                    # Reset histogram by creating a new one with the same buckets
                    metric.value = Histogram(buckets=metric.value.buckets)

    def clear(self) -> None:
        """Remove all metrics from the registry."""
        with self._lock:
            self._metrics.clear()
