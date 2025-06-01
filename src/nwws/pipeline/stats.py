# pyright: strict
"""Pipeline statistics and metrics collection using the new metrics system."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from nwws.metrics import MetricsCollector

from .types import PipelineStage

if TYPE_CHECKING:
    from nwws.metrics import MetricRegistry

    from .types import EventId, StageId, Timestamp


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

    details: dict[str, str | int | float | bool] = field(default_factory=dict)
    """Additional metric details with simple values only."""


@dataclass(frozen=True)
class ProcessingTimeParams:
    """Parameters for recording processing time to reduce function complexity."""

    event_id: EventId
    stage: PipelineStage
    stage_id: StageId
    duration_ms: float
    success: bool = True
    event_metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ErrorParams:
    """Parameters for recording errors to reduce function complexity."""

    stage: PipelineStage
    stage_id: StageId
    error_type: str
    operation: str = ""
    event_metadata: dict[str, Any] | None = None
    error_context: dict[str, Any] | None = None


@dataclass(frozen=True)
class FilterDecisionParams:
    """Parameters for recording filter decisions to reduce function complexity."""

    event_id: EventId
    filter_id: StageId
    decision: str
    reason: str | None = None
    duration_ms: float | None = None
    event_metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class TransformationParams:
    """Parameters for recording transformations to reduce function complexity."""

    event_id: EventId
    transformer_id: StageId
    input_type: str
    output_type: str
    duration_ms: float
    event_metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class OutputDeliveryParams:
    """Parameters for recording output delivery to reduce function complexity."""

    event_id: EventId
    output_id: StageId
    destination: str
    success: bool
    duration_ms: float
    payload_size: int | None = None
    event_metadata: dict[str, Any] | None = None


class PipelineStatsCollector:
    """Pipeline statistics collector using the new metrics system."""

    def __init__(self, registry: MetricRegistry, pipeline_id: str = "pipeline") -> None:
        """Initialize the pipeline stats collector."""
        self.registry = registry
        self.collector = MetricsCollector(registry, prefix=pipeline_id)
        self.pipeline_id = pipeline_id

    def _extract_simple_details(
        self, event_metadata: dict[str, Any] | None
    ) -> dict[str, str | int | float | bool]:
        """Extract simple values from metadata for logging."""
        if not event_metadata:
            return {}

        details: dict[str, str | int | float | bool] = {}
        for key, value in event_metadata.items():
            if isinstance(value, (str, int, float, bool)):
                details[key] = value
            elif hasattr(value, "__str__"):
                details[key] = str(value)

        return details

    def record_processing_time(
        self, params: ProcessingTimeParams
    ) -> PipelineStatsEvent:
        """Record processing time for a stage with enhanced metadata context."""
        labels = {"stage": params.stage.value, "stage_id": params.stage_id}

        # Add metadata-based labels if available
        if params.event_metadata:
            if "event_type" in params.event_metadata:
                event_type = params.event_metadata["event_type"]
                if isinstance(event_type, str):
                    labels["event_type"] = event_type
            if "source" in params.event_metadata:
                source = params.event_metadata["source"]
                if isinstance(source, str):
                    labels["source"] = source
            if "trace_id" in params.event_metadata:
                trace_id = params.event_metadata["trace_id"]
                if isinstance(trace_id, str):
                    labels["trace_id"] = trace_id[:8]  # Truncate for cardinality

        self.collector.record_operation(
            f"{params.stage.value}_{params.stage_id}",
            success=params.success,
            duration_ms=params.duration_ms,
            labels=labels,
        )

        # Extract simple details from metadata
        details = self._extract_simple_details(params.event_metadata)

        return PipelineStatsEvent(
            event_id=params.event_id,
            stage=params.stage,
            stage_id=params.stage_id,
            metric_name=f"{params.stage.value}_{params.stage_id}_processing_time",
            metric_value=params.duration_ms,
            duration_ms=params.duration_ms,
            success=params.success,
            details=details,
        )

    def record_throughput(
        self,
        event_id: EventId,
        stage: PipelineStage,
        stage_id: StageId,
        event_metadata: dict[str, Any] | None = None,
    ) -> PipelineStatsEvent:
        """Record throughput metric for a stage with metadata context."""
        labels = {"stage": stage.value, "stage_id": stage_id}

        # Add metadata-based labels for better metrics segmentation
        if event_metadata:
            if "event_type" in event_metadata:
                event_type = event_metadata["event_type"]
                if isinstance(event_type, str):
                    labels["event_type"] = event_type
            if "source" in event_metadata:
                source = event_metadata["source"]
                if isinstance(source, str):
                    labels["source"] = source

        self.collector.increment_counter(
            "throughput_total",
            labels=labels,
            help_text="Total number of events processed",
        )

        current_value = self.collector.get_metric_value("throughput_total", labels) or 0

        # Extract simple details from metadata
        details = self._extract_simple_details(event_metadata)

        return PipelineStatsEvent(
            event_id=event_id,
            stage=stage,
            stage_id=stage_id,
            metric_name=f"{stage.value}_{stage_id}_throughput",
            metric_value=current_value,
            details=details,
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

    def _add_metadata_labels(
        self, labels: dict[str, str], metadata: dict[str, Any] | None
    ) -> None:
        """Add metadata-based labels to the provided labels dict."""
        if not metadata:
            return

        event_type = metadata.get("event_type")
        if isinstance(event_type, str):
            labels["event_type"] = event_type

        source = metadata.get("source")
        if isinstance(source, str):
            labels["source"] = source

        trace_id = metadata.get("trace_id")
        if isinstance(trace_id, str):
            labels["trace_id"] = trace_id[:8]  # Truncate for cardinality

    def _add_error_context_labels(
        self, labels: dict[str, str], context: dict[str, Any] | None
    ) -> None:
        """Add error context labels to the provided labels dict."""
        if not context:
            return

        recoverable = context.get("recoverable")
        if isinstance(recoverable, bool):
            labels["recoverable"] = str(recoverable)

        event_age_seconds = context.get("event_age_seconds")
        if isinstance(event_age_seconds, (int, float)):
            # Bucket event age for better aggregation
            labels["age_bucket"] = self._get_age_bucket(event_age_seconds)

    def _get_age_bucket(self, age_seconds: float) -> str:
        """Get age bucket label for event age."""
        if age_seconds < 1:
            return "0-1s"
        if age_seconds < 10:
            return "1-10s"
        if age_seconds < 60:
            return "10-60s"
        return "60s+"

    def record_error(self, params: ErrorParams) -> None:
        """Record an error for a specific stage with enhanced context."""
        labels = {
            "stage": params.stage.value,
            "stage_id": params.stage_id,
            "error_type": params.error_type,
        }

        self._add_metadata_labels(labels, params.event_metadata)
        self._add_error_context_labels(labels, params.error_context)

        self.collector.record_error(
            params.error_type,
            operation=params.operation or f"{params.stage.value}_{params.stage_id}",
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

    def record_filter_decision(
        self, params: FilterDecisionParams
    ) -> PipelineStatsEvent:
        """Record filter decision metrics with enhanced context."""
        labels = {
            "stage": "filter",
            "filter_id": params.filter_id,
            "decision": params.decision,
        }

        if params.reason:
            labels["reason"] = params.reason

        # Add metadata-based labels
        if params.event_metadata and "event_type" in params.event_metadata:
            event_type = params.event_metadata["event_type"]
            if isinstance(event_type, str):
                labels["event_type"] = event_type

        self.collector.increment_counter(
            "filter_decisions_total",
            labels=labels,
            help_text="Total number of filter decisions made",
        )

        # Track filter performance if duration available
        if params.duration_ms is not None:
            self.collector.observe_histogram(
                "filter_processing_duration_ms",
                params.duration_ms,
                labels={"filter_id": params.filter_id},
                help_text="Filter processing duration in milliseconds",
            )

        details: dict[str, str | int | float | bool] = {"decision": params.decision}
        if params.reason:
            details["reason"] = params.reason

        # Add simple metadata details
        simple_metadata = self._extract_simple_details(params.event_metadata)
        details.update(simple_metadata)

        return PipelineStatsEvent(
            event_id=params.event_id,
            stage=PipelineStage.FILTER,
            stage_id=params.filter_id,
            metric_name=f"filter_{params.filter_id}_decision",
            metric_value=params.decision,
            duration_ms=params.duration_ms,
            details=details,
        )

    def record_transformation_success(
        self, params: TransformationParams
    ) -> PipelineStatsEvent:
        """Record successful transformation metrics."""
        labels = {
            "stage": "transform",
            "transformer_id": params.transformer_id,
            "input_type": params.input_type,
            "output_type": params.output_type,
        }

        # Add metadata-based labels
        if params.event_metadata and "source" in params.event_metadata:
            source = params.event_metadata["source"]
            if isinstance(source, str):
                labels["source"] = source

        self.collector.increment_counter(
            "transformations_total",
            labels=labels,
            help_text="Total number of transformations completed",
        )

        self.collector.observe_histogram(
            "transformation_duration_ms",
            params.duration_ms,
            labels={
                "transformer_id": params.transformer_id,
                "input_type": params.input_type,
            },
            help_text="Transformation processing duration in milliseconds",
        )

        details: dict[str, str | int | float | bool] = {
            "input_type": params.input_type,
            "output_type": params.output_type,
            "transformation_successful": True,
        }

        # Add simple metadata details
        simple_metadata = self._extract_simple_details(params.event_metadata)
        details.update(simple_metadata)

        return PipelineStatsEvent(
            event_id=params.event_id,
            stage=PipelineStage.TRANSFORM,
            stage_id=params.transformer_id,
            metric_name=f"transformer_{params.transformer_id}_success",
            metric_value=1,
            duration_ms=params.duration_ms,
            details=details,
        )

    def record_output_delivery(
        self, params: OutputDeliveryParams
    ) -> PipelineStatsEvent:
        """Record output delivery metrics."""
        labels = {
            "stage": "output",
            "output_id": params.output_id,
            "destination": params.destination,
            "success": str(params.success),
        }

        # Add metadata-based labels
        if params.event_metadata and "event_type" in params.event_metadata:
            event_type = params.event_metadata["event_type"]
            if isinstance(event_type, str):
                labels["event_type"] = event_type

        self.collector.increment_counter(
            "output_deliveries_total",
            labels=labels,
            help_text="Total number of output deliveries attempted",
        )

        if params.success:
            self.collector.observe_histogram(
                "output_delivery_duration_ms",
                params.duration_ms,
                labels={
                    "output_id": params.output_id,
                    "destination": params.destination,
                },
                help_text="Output delivery duration in milliseconds",
            )

            if params.payload_size is not None:
                self.collector.observe_histogram(
                    "output_payload_size_bytes",
                    params.payload_size,
                    labels={
                        "output_id": params.output_id,
                        "destination": params.destination,
                    },
                    help_text="Output payload size in bytes",
                )

        details: dict[str, str | int | float | bool] = {
            "destination": params.destination,
            "success": params.success,
        }
        if params.payload_size is not None:
            details["payload_size_bytes"] = params.payload_size

        # Add simple metadata details
        simple_metadata = self._extract_simple_details(params.event_metadata)
        details.update(simple_metadata)

        return PipelineStatsEvent(
            event_id=params.event_id,
            stage=PipelineStage.OUTPUT,
            stage_id=params.output_id,
            metric_name=f"output_{params.output_id}_delivery",
            metric_value=1 if params.success else 0,
            duration_ms=params.duration_ms,
            success=params.success,
            details=details,
        )

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all pipeline statistics."""
        return self.registry.get_registry_summary()
