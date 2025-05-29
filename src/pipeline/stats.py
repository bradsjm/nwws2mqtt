# pyright: strict
"""Pipeline statistics and metrics collection."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .types import EventId, PipelineStage, StageId, Timestamp


@dataclass(frozen=True)
class PipelineStatsEvent:
    """Event representing pipeline statistics and metrics."""

    event_id: EventId
    """Unique identifier for the original event being tracked."""

    stage: PipelineStage
    """Pipeline stage that generated this stat."""

    stage_id: StageId
    """Specific component ID within the stage."""

    metric_name: str
    """Name of the metric being reported."""

    metric_value: float | int | str
    """Value of the metric."""

    timestamp: Timestamp = field(default_factory=time.time)
    """When this stat was recorded."""

    duration_ms: float | None = None
    """Processing duration in milliseconds."""

    success: bool = True
    """Whether the operation was successful."""

    details: dict[str, Any] = field(default_factory=dict)
    """Additional metric details."""


class PipelineStats:
    """Pipeline statistics collector and aggregator."""

    def __init__(self) -> None:
        """Initialize the stats collector."""
        self._counters: dict[str, int] = {}
        self._timers: dict[str, list[float]] = {}
        self._gauges: dict[str, float] = {}
        self._errors: dict[str, int] = {}

    def increment(self, metric: str, value: int = 1) -> None:
        """Increment a counter metric."""
        self._counters[metric] = self._counters.get(metric, 0) + value

    def record_time(self, metric: str, duration_ms: float) -> None:
        """Record a timing metric."""
        if metric not in self._timers:
            self._timers[metric] = []
        self._timers[metric].append(duration_ms)

    def set_gauge(self, metric: str, value: float) -> None:
        """Set a gauge metric value."""
        self._gauges[metric] = value

    def record_error(self, metric: str) -> None:
        """Record an error for the given metric."""
        self._errors[metric] = self._errors.get(metric, 0) + 1

    def get_counter(self, metric: str) -> int:
        """Get the current value of a counter."""
        return self._counters.get(metric, 0)

    def get_average_time(self, metric: str) -> float | None:
        """Get the average time for a timing metric."""
        times = self._timers.get(metric, [])
        return sum(times) / len(times) if times else None

    def get_gauge(self, metric: str) -> float | None:
        """Get the current value of a gauge."""
        return self._gauges.get(metric)

    def get_error_count(self, metric: str) -> int:
        """Get the error count for a metric."""
        return self._errors.get(metric, 0)

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all collected statistics."""
        return {
            "counters": self._counters.copy(),
            "timers": {
                metric: {
                    "count": len(times),
                    "avg": sum(times) / len(times) if times else 0,
                    "min": min(times) if times else 0,
                    "max": max(times) if times else 0,
                }
                for metric, times in self._timers.items()
            },
            "gauges": self._gauges.copy(),
            "errors": self._errors.copy(),
        }

    def reset(self) -> None:
        """Reset all statistics."""
        self._counters.clear()
        self._timers.clear()
        self._gauges.clear()
        self._errors.clear()


class StatsCollector:
    """Utility class for collecting and emitting pipeline statistics."""

    def __init__(self, stats: PipelineStats) -> None:
        """Initialize with a stats instance."""
        self.stats = stats

    def record_processing_time(
        self,
        event_id: EventId,
        stage: PipelineStage,
        stage_id: StageId,
        duration_ms: float,
        *,
        success: bool = True,
    ) -> PipelineStatsEvent:
        """Record processing time for a stage."""
        metric_name = f"{stage.value}.{stage_id}.processing_time"
        self.stats.record_time(metric_name, duration_ms)

        if success:
            self.stats.increment(f"{stage.value}.{stage_id}.success")
        else:
            self.stats.record_error(f"{stage.value}.{stage_id}")

        return PipelineStatsEvent(
            event_id=event_id,
            stage=stage,
            stage_id=stage_id,
            metric_name=metric_name,
            metric_value=duration_ms,
            duration_ms=duration_ms,
            success=success,
        )

    def record_throughput(
        self,
        event_id: EventId,
        stage: PipelineStage,
        stage_id: StageId,
    ) -> PipelineStatsEvent:
        """Record throughput metric for a stage."""
        metric_name = f"{stage.value}.{stage_id}.throughput"
        self.stats.increment(metric_name)

        return PipelineStatsEvent(
            event_id=event_id,
            stage=stage,
            stage_id=stage_id,
            metric_name=metric_name,
            metric_value=self.stats.get_counter(metric_name),
        )

    def record_queue_size(
        self,
        stage: PipelineStage,
        stage_id: StageId,
        size: int,
    ) -> PipelineStatsEvent:
        """Record queue size gauge metric."""
        metric_name = f"{stage.value}.{stage_id}.queue_size"
        self.stats.set_gauge(metric_name, float(size))

        return PipelineStatsEvent(
            event_id="",  # Queue size is not tied to a specific event
            stage=stage,
            stage_id=stage_id,
            metric_name=metric_name,
            metric_value=size,
        )
