# pyright: strict
"""Pipeline statistics and metrics collection using the new metrics system."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from nwws.metrics import MetricsCollector

if TYPE_CHECKING:
    from nwws.metrics import MetricRegistry

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


class PipelineStatsCollector:
    """Pipeline statistics collector using the new metrics system."""

    def __init__(self, registry: MetricRegistry, pipeline_id: str = "pipeline") -> None:
        """Initialize the pipeline stats collector."""
        self.registry = registry
        self.collector = MetricsCollector(registry, prefix=pipeline_id)
        self.pipeline_id = pipeline_id

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
        labels = {"stage": stage.value, "stage_id": stage_id}

        self.collector.record_operation(
            f"{stage.value}_{stage_id}",
            success=success,
            duration_ms=duration_ms,
            labels=labels,
        )

        return PipelineStatsEvent(
            event_id=event_id,
            stage=stage,
            stage_id=stage_id,
            metric_name=f"{stage.value}_{stage_id}_processing_time",
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
        labels = {"stage": stage.value, "stage_id": stage_id}

        self.collector.increment_counter(
            "throughput_total",
            labels=labels,
            help_text="Total number of events processed",
        )

        current_value = self.collector.get_metric_value("throughput_total", labels) or 0

        return PipelineStatsEvent(
            event_id=event_id,
            stage=stage,
            stage_id=stage_id,
            metric_name=f"{stage.value}_{stage_id}_throughput",
            metric_value=current_value,
        )

    def record_queue_size(
        self,
        stage: PipelineStage,
        stage_id: StageId,
        size: int,
    ) -> PipelineStatsEvent:
        """Record queue size gauge metric."""
        labels = {"stage": stage.value, "stage_id": stage_id}

        self.collector.set_gauge(
            "queue_size",
            size,
            labels=labels,
            help_text="Current queue size for stage",
        )

        return PipelineStatsEvent(
            event_id="",  # Queue size is not tied to a specific event
            stage=stage,
            stage_id=stage_id,
            metric_name=f"{stage.value}_{stage_id}_queue_size",
            metric_value=size,
        )

    def record_error(
        self,
        stage: PipelineStage,
        stage_id: StageId,
        error_type: str,
        operation: str = "",
    ) -> None:
        """Record an error for a specific stage."""
        labels = {"stage": stage.value, "stage_id": stage_id}

        self.collector.record_error(
            error_type,
            operation=operation or f"{stage.value}_{stage_id}",
            labels=labels,
        )

    def update_stage_status(
        self,
        stage: PipelineStage,
        stage_id: StageId,
        status: str,
    ) -> None:
        """Update the status of a pipeline stage."""
        labels = {"stage": stage.value, "stage_id": stage_id}

        self.collector.update_status(
            f"{stage.value}_{stage_id}",
            status,
            labels=labels,
        )

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all pipeline statistics."""
        return self.registry.get_registry_summary()
