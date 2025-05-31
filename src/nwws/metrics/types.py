# pyright: strict
"""Core metric types and data structures."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class MetricType(Enum):
    """Types of metrics supported by the metrics system."""

    COUNTER = auto()
    """Monotonically increasing counter."""

    GAUGE = auto()
    """Current value that can go up or down."""

    HISTOGRAM = auto()
    """Distribution of values with configurable buckets."""


@dataclass(frozen=True)
class MetricKey:
    """Unique identifier for a metric with name and labels."""

    name: str
    """Metric name in snake_case format."""

    labels: frozenset[tuple[str, str]] = field(default_factory=frozenset)
    """Immutable set of label key-value pairs."""

    @classmethod
    def create(cls, name: str, labels: dict[str, str] | None = None) -> MetricKey:
        """Create a metric key from name and optional labels dict."""
        label_items: frozenset[tuple[str, str]] = (
            frozenset(labels.items()) if labels else frozenset()
        )
        return cls(name=name, labels=label_items)

    def labels_dict(self) -> dict[str, str]:
        """Convert labels back to a dictionary."""
        return dict(self.labels)


@dataclass
class Histogram:
    """Histogram for tracking distributions of values."""

    buckets: list[float]
    """Bucket upper bounds for the histogram."""

    counts: list[int] = field(init=False)
    """Count of observations in each bucket."""

    sum: float = field(default=0.0, init=False)
    """Sum of all observed values."""

    count: int = field(default=0, init=False)
    """Total number of observations."""

    def __post_init__(self) -> None:
        """Initialize bucket counts."""
        self.counts = [0] * len(self.buckets)

    def observe(self, value: float) -> None:
        """Record an observation in the histogram."""
        self.sum += value
        self.count += 1

        # Find the appropriate bucket
        for i, bucket_upper_bound in enumerate(self.buckets):
            if value <= bucket_upper_bound:
                self.counts[i] += 1
                return

    def get_buckets_with_counts(self) -> list[tuple[float, int]]:
        """Get bucket upper bounds paired with their counts."""
        return list(zip(self.buckets, self.counts, strict=True))

    @classmethod
    def create_default_timing_histogram(cls) -> Histogram:
        """Create a histogram with default buckets for timing metrics (milliseconds)."""
        # Default buckets for timing
        buckets = [
            1.0,
            5.0,
            10.0,
            25.0,
            50.0,
            100.0,
            250.0,
            500.0,
            1000.0,
            2500.0,
            5000.0,
            10000.0,
        ]
        return cls(buckets=buckets)


@dataclass
class Metric:
    """A metric with its type, value, and metadata."""

    key: MetricKey
    """Unique identifier for this metric."""

    metric_type: MetricType
    """Type of the metric."""

    value: float | int | Histogram = field(default=0)
    """Current value of the metric."""

    help_text: str = ""
    """Description of what this metric measures."""

    timestamp: float = field(default_factory=time.time)
    """When this metric was last updated."""

    def increment(self, amount: float = 1) -> None:
        """Increment a counter metric."""
        if self.metric_type != MetricType.COUNTER:
            error_msg = f"Cannot increment non-counter metric: {self.key.name}"
            raise ValueError(error_msg)
        if not isinstance(self.value, (int, float)):
            error_msg = f"Counter value must be numeric, got {type(self.value)}"
            raise TypeError(error_msg)
        self.value = float(self.value) + float(amount)
        self.timestamp = time.time()

    def set_value(self, value: float) -> None:
        """Set the value of a gauge metric."""
        if self.metric_type != MetricType.GAUGE:
            error_msg = f"Cannot set value on non-gauge metric: {self.key.name}"
            raise ValueError(error_msg)
        self.value = float(value)
        self.timestamp = time.time()

    def observe(self, value: float) -> None:
        """Record an observation in a histogram metric."""
        if self.metric_type != MetricType.HISTOGRAM:
            error_msg = f"Cannot observe on non-histogram metric: {self.key.name}"
            raise ValueError(error_msg)
        if not isinstance(self.value, Histogram):
            error_msg = (
                f"Histogram metric must have Histogram value, got {type(self.value)}"
            )
            raise TypeError(error_msg)
        self.value.observe(value)
        self.timestamp = time.time()

    def get_numeric_value(self) -> float:
        """Get the numeric representation of the metric value."""
        if isinstance(self.value, Histogram):
            return float(self.value.count)
        return float(self.value)

    def to_dict(self) -> dict[str, Any]:
        """Convert metric to dictionary representation."""
        result: dict[str, Any] = {
            "name": self.key.name,
            "type": self.metric_type.name.lower(),
            "help": self.help_text,
            "timestamp": self.timestamp,
        }

        if self.key.labels:
            result["labels"] = self.key.labels_dict()

        if isinstance(self.value, Histogram):
            result["histogram"] = {
                "buckets": self.value.get_buckets_with_counts(),
                "sum": self.value.sum,
                "count": self.value.count,
            }
        else:
            result["value"] = self.value

        return result
