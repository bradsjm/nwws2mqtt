# pyright: strict
"""Pipeline statistics collector following receiver stats pattern."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from loguru import logger

from nwws.metrics import MetricsCollector

if TYPE_CHECKING:
    from collections.abc import Callable

    from nwws.metrics import MetricRegistry


@dataclass
class PipelineStatsEvent:
    """Statistics event for pipeline operations."""

    pipeline_id: str
    """Pipeline identifier."""

    metric_name: str
    """Name of the metric that was recorded."""

    metric_value: float
    """Current value of the metric."""

    labels: dict[str, str]
    """Labels associated with this metric."""

    success: bool | None = None
    """Whether the operation was successful (if applicable)."""

    duration_seconds: float | None = None
    """Duration of the operation in seconds (if applicable)."""


class PipelineStatsCollector:
    """Statistics collector for pipeline operations following receiver pattern."""

    def __init__(
        self,
        registry: MetricRegistry,
        pipeline_id: str = "pipeline",
        metric_prefix: str = "pipeline",
    ) -> None:
        """Initialize with a registry instance and pipeline identifier.

        Args:
            registry: MetricRegistry instance for recording metrics
            pipeline_id: Identifier for the pipeline instance
            metric_prefix: Prefix for all metric names (default: "pipeline")

        """
        self.pipeline_id = pipeline_id
        self.metric_prefix = metric_prefix
        self.registry = registry
        self.collector = MetricsCollector(registry)

    def _make_metric_name(self, name: str) -> str:
        """Create a full metric name with prefix."""
        return f"{self.metric_prefix}_{name}"

    def _make_labels(
        self, additional_labels: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Create labels dict with pipeline_id and any additional labels."""
        base_labels: dict[str, str] = {"pipeline": self.pipeline_id}
        if additional_labels:
            # Sanitize label values
            sanitized_labels = {
                key: self._sanitize_label_value(str(value))
                for key, value in additional_labels.items()
            }
            base_labels.update(sanitized_labels)
        return base_labels

    def _sanitize_label_value(self, value: str, max_length: int = 64) -> str:
        """Sanitize label values for Prometheus compatibility."""
        # Remove/replace problematic characters, truncate if needed
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", value)
        return sanitized[:max_length] if len(sanitized) > max_length else sanitized

    def _safe_metric_operation(
        self,
        operation_name: str,
        operation_func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        """Safely execute a metric operation with error handling."""
        try:
            operation_func(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to {operation_name}: {e}")
            return False

        return True

    def record_event_received(
        self, *, source: str, event_type: str
    ) -> PipelineStatsEvent | None:
        """Record an event entering the pipeline."""
        metric_name = self._make_metric_name("events_received_total")
        op_labels = {"source": source, "event_type": event_type}
        labels = self._make_labels(op_labels)

        success = self._safe_metric_operation(
            "record event received",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total number of events received by the pipeline.",
        )

        if not success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return PipelineStatsEvent(
            pipeline_id=self.pipeline_id,
            metric_name=metric_name,
            metric_value=current_value,
            labels=labels,
        )

    def record_event_processed(
        self,
        *,
        processing_duration_seconds: float,
        event_type: str,
        source: str,
        event_age_seconds: float | None = None,
    ) -> PipelineStatsEvent | None:
        """Record an event that was successfully processed through the pipeline."""
        # Validate inputs
        if processing_duration_seconds < 0:
            error_msg = "processing_duration_seconds must be non-negative"
            raise ValueError(error_msg)
        if not event_type.strip():
            error_msg = "event_type cannot be empty"
            raise ValueError(error_msg)
        if not source.strip():
            error_msg = "source cannot be empty"
            raise ValueError(error_msg)

        base_op_labels = {"event_type": event_type, "source": source}
        labels = self._make_labels(base_op_labels)

        # Update all metrics
        operations_successful = 0

        # 1. Total processed counter
        total_metric_name = self._make_metric_name("events_processed_total")
        if self._safe_metric_operation(
            "record events processed total",
            self.collector.increment_counter,
            total_metric_name,
            labels=labels,
            help_text="Total number of events successfully processed by the pipeline.",
        ):
            operations_successful += 1

        # 2. Processing duration histogram
        duration_metric_name = self._make_metric_name("processing_duration_seconds")
        duration_labels = self._make_labels({"event_type": event_type})
        if self._safe_metric_operation(
            "record processing duration",
            self.collector.observe_histogram,
            duration_metric_name,
            processing_duration_seconds,
            labels=duration_labels,
            help_text="Pipeline processing duration in seconds.",
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 10],
        ):
            operations_successful += 1

        # 3. Event age histogram (if provided)
        if event_age_seconds is not None:
            if event_age_seconds < 0:
                error_msg = "event_age_seconds must be non-negative"
                raise ValueError(error_msg)

            age_metric_name = self._make_metric_name("event_age_seconds")
            age_labels = self._make_labels({"event_type": event_type})
            if self._safe_metric_operation(
                "record event age",
                self.collector.observe_histogram,
                age_metric_name,
                event_age_seconds,
                labels=age_labels,
                help_text="Age of events when processed in seconds.",
                buckets=[0.1, 0.5, 1, 5, 10, 30, 60, 300, 1800, 3600],
            ):
                operations_successful += 1

        # Return event for the main processed counter
        if operations_successful == 0:
            return None

        current_value = (
            self.collector.get_metric_value(total_metric_name, labels=labels) or 1
        )

        event = PipelineStatsEvent(
            pipeline_id=self.pipeline_id,
            metric_name=total_metric_name,
            metric_value=current_value,
            success=True,
            labels=labels,
        )
        event.duration_seconds = processing_duration_seconds
        return event

    def update_pipeline_status(self, *, is_healthy: bool) -> PipelineStatsEvent | None:
        """Update the pipeline health status gauge."""
        metric_name = self._make_metric_name("status")
        status_value = 1.0 if is_healthy else 0.0
        labels = self._make_labels()

        operation_success = self._safe_metric_operation(
            "update pipeline status",
            self.collector.set_gauge,
            metric_name,
            value=status_value,
            labels=labels,
            help_text="Current pipeline health status (1 for healthy, 0 for unhealthy).",
        )

        if not operation_success:
            return None

        return PipelineStatsEvent(
            pipeline_id=self.pipeline_id,
            metric_name=metric_name,
            metric_value=status_value,
            labels=labels,
        )

    def record_stage_attempt(
        self, *, stage: str, stage_id: str
    ) -> PipelineStatsEvent | None:
        """Record a stage processing attempt."""
        metric_name = self._make_metric_name("stage_attempts_total")
        op_labels = {"stage": stage, "stage_id": stage_id}
        labels = self._make_labels(op_labels)

        success = self._safe_metric_operation(
            "record stage attempt",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total number of pipeline stage processing attempts.",
        )

        if not success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return PipelineStatsEvent(
            pipeline_id=self.pipeline_id,
            metric_name=metric_name,
            metric_value=current_value,
            labels=labels,
        )

    def record_stage_result(
        self,
        *,
        stage: str,
        stage_id: str,
        success: bool,
        reason: str | None = None,
    ) -> PipelineStatsEvent | None:
        """Record a stage processing result (success or failure)."""
        metric_name = self._make_metric_name("stage_results_total")
        result_str = "success" if success else "failure"
        op_labels = {"stage": stage, "stage_id": stage_id, "result": result_str}

        if not success and reason:
            op_labels["reason"] = reason

        labels = self._make_labels(op_labels)

        operation_success = self._safe_metric_operation(
            "record stage result",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total pipeline stage processing results.",
        )

        if not operation_success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return PipelineStatsEvent(
            pipeline_id=self.pipeline_id,
            metric_name=metric_name,
            metric_value=current_value,
            success=success,
            labels=labels,
        )

    def record_stage_error(
        self, *, stage: str, stage_id: str, error_type: str
    ) -> PipelineStatsEvent | None:
        """Record a stage error."""
        metric_name = self._make_metric_name("stage_errors_total")
        op_labels = {"stage": stage, "stage_id": stage_id, "error_type": error_type}
        labels = self._make_labels(op_labels)

        success = self._safe_metric_operation(
            "record stage error",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total number of pipeline stage errors.",
        )

        if not success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return PipelineStatsEvent(
            pipeline_id=self.pipeline_id,
            metric_name=metric_name,
            metric_value=current_value,
            success=False,
            labels=labels,
        )

    def record_filter_decision(
        self, *, filter_id: str, passed: bool, event_type: str
    ) -> PipelineStatsEvent | None:
        """Record a filter decision."""
        metric_name = self._make_metric_name("filter_decisions_total")
        decision_str = "passed" if passed else "filtered"
        op_labels = {
            "filter_id": filter_id,
            "decision": decision_str,
            "event_type": event_type,
        }
        labels = self._make_labels(op_labels)

        success = self._safe_metric_operation(
            "record filter decision",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total number of filter decisions made.",
        )

        if not success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return PipelineStatsEvent(
            pipeline_id=self.pipeline_id,
            metric_name=metric_name,
            metric_value=current_value,
            success=passed,
            labels=labels,
        )

    def record_filter_processed(
        self,
        *,
        filter_id: str,
        processing_duration_seconds: float,
        passed: bool,
        event_type: str,
    ) -> PipelineStatsEvent | None:
        """Record a filter processing with duration."""
        # Validate inputs
        if processing_duration_seconds < 0:
            error_msg = "processing_duration_seconds must be non-negative"
            raise ValueError(error_msg)
        if not filter_id.strip():
            error_msg = "filter_id cannot be empty"
            raise ValueError(error_msg)
        if not event_type.strip():
            error_msg = "event_type cannot be empty"
            raise ValueError(error_msg)

        # Record decision first
        decision_event = self.record_filter_decision(
            filter_id=filter_id, passed=passed, event_type=event_type
        )

        # Record processing duration
        duration_metric_name = self._make_metric_name(
            "filter_processing_duration_seconds"
        )
        duration_labels = self._make_labels({"filter_id": filter_id})

        duration_success = self._safe_metric_operation(
            "record filter processing duration",
            self.collector.observe_histogram,
            duration_metric_name,
            processing_duration_seconds,
            labels=duration_labels,
            help_text="Filter processing duration in seconds.",
            buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5],
        )

        if not duration_success:
            return decision_event

        # Return the decision event with duration info
        if decision_event:
            decision_event.duration_seconds = processing_duration_seconds

        return decision_event

    def record_transformation_result(
        self,
        *,
        transformer_id: str,
        success: bool,
        input_type: str,
        output_type: str,
        reason: str | None = None,
    ) -> PipelineStatsEvent | None:
        """Record a transformation result (success or failure)."""
        metric_name = self._make_metric_name("transformations_total")
        result_str = "success" if success else "failure"
        op_labels = {
            "transformer_id": transformer_id,
            "result": result_str,
            "input_type": input_type,
            "output_type": output_type,
        }

        if not success and reason:
            op_labels["reason"] = reason

        labels = self._make_labels(op_labels)

        operation_success = self._safe_metric_operation(
            "record transformation result",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total transformation attempts and results.",
        )

        if not operation_success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return PipelineStatsEvent(
            pipeline_id=self.pipeline_id,
            metric_name=metric_name,
            metric_value=current_value,
            success=success,
            labels=labels,
        )

    def record_transformation_processed(
        self,
        *,
        transformer_id: str,
        processing_duration_seconds: float,
        input_type: str,
        output_type: str,
    ) -> PipelineStatsEvent | None:
        """Record a transformation processing with duration."""
        # Validate inputs
        if processing_duration_seconds < 0:
            error_msg = "processing_duration_seconds must be non-negative"
            raise ValueError(error_msg)
        if not transformer_id.strip():
            error_msg = "transformer_id cannot be empty"
            raise ValueError(error_msg)
        if not input_type.strip():
            error_msg = "input_type cannot be empty"
            raise ValueError(error_msg)
        if not output_type.strip():
            error_msg = "output_type cannot be empty"
            raise ValueError(error_msg)

        # Record successful transformation
        result_event = self.record_transformation_result(
            transformer_id=transformer_id,
            success=True,
            input_type=input_type,
            output_type=output_type,
        )

        # Record processing duration
        duration_metric_name = self._make_metric_name(
            "transformation_processing_duration_seconds"
        )
        duration_labels = self._make_labels(
            {
                "transformer_id": transformer_id,
                "input_type": input_type,
            }
        )

        duration_success = self._safe_metric_operation(
            "record transformation processing duration",
            self.collector.observe_histogram,
            duration_metric_name,
            processing_duration_seconds,
            labels=duration_labels,
            help_text="Transformation processing duration in seconds.",
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5],
        )

        if not duration_success:
            return result_event

        # Return the result event with duration info
        if result_event:
            result_event.duration_seconds = processing_duration_seconds

        return result_event

    def record_output_delivery_result(
        self,
        *,
        output_id: str,
        success: bool,
        destination: str,
        reason: str | None = None,
    ) -> PipelineStatsEvent | None:
        """Record an output delivery result (success or failure)."""
        metric_name = self._make_metric_name("output_deliveries_total")
        result_str = "success" if success else "failure"
        op_labels = {
            "output_id": output_id,
            "result": result_str,
            "destination": destination,
        }

        if not success and reason:
            op_labels["reason"] = reason

        labels = self._make_labels(op_labels)

        operation_success = self._safe_metric_operation(
            "record output delivery result",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total output delivery attempts and results.",
        )

        if not operation_success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return PipelineStatsEvent(
            pipeline_id=self.pipeline_id,
            metric_name=metric_name,
            metric_value=current_value,
            success=success,
            labels=labels,
        )

    def record_output_delivered(
        self,
        *,
        output_id: str,
        processing_duration_seconds: float,
        payload_size_bytes: int,
        destination: str,
    ) -> PipelineStatsEvent | None:
        """Record a successful output delivery with metrics."""
        # Validate inputs
        if processing_duration_seconds < 0:
            error_msg = "processing_duration_seconds must be non-negative"
            raise ValueError(error_msg)
        if payload_size_bytes < 0:
            error_msg = "payload_size_bytes must be non-negative"
            raise ValueError(error_msg)
        if not output_id.strip():
            error_msg = "output_id cannot be empty"
            raise ValueError(error_msg)
        if not destination.strip():
            error_msg = "destination cannot be empty"
            raise ValueError(error_msg)

        # Update all metrics
        operations_successful = 0

        # 1. Record successful delivery
        delivery_event = self.record_output_delivery_result(
            output_id=output_id, success=True, destination=destination
        )
        if delivery_event:
            operations_successful += 1

        # 2. Delivery duration histogram
        duration_metric_name = self._make_metric_name(
            "output_delivery_duration_seconds"
        )
        duration_labels = self._make_labels(
            {"output_id": output_id, "destination": destination}
        )
        if self._safe_metric_operation(
            "record output delivery duration",
            self.collector.observe_histogram,
            duration_metric_name,
            processing_duration_seconds,
            labels=duration_labels,
            help_text="Output delivery duration in seconds.",
            buckets=[0.01, 0.05, 0.1, 0.5, 1, 5, 10, 30, 60],
        ):
            operations_successful += 1

        # 3. Payload size histogram
        size_metric_name = self._make_metric_name("output_payload_size_bytes")
        size_labels = self._make_labels(
            {"output_id": output_id, "destination": destination}
        )
        if self._safe_metric_operation(
            "record output payload size",
            self.collector.observe_histogram,
            size_metric_name,
            payload_size_bytes,
            labels=size_labels,
            help_text="Output payload size in bytes.",
            buckets=[256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536],
        ):
            operations_successful += 1

        if operations_successful == 0:
            return None

        # Return delivery event with additional metrics
        if delivery_event:
            delivery_event.duration_seconds = processing_duration_seconds

        return delivery_event

    def update_queue_size(self, *, stage: str, size: int) -> PipelineStatsEvent | None:
        """Update the queue size gauge for a stage."""
        metric_name = self._make_metric_name("queue_size")
        op_labels = {"stage": stage}
        labels = self._make_labels(op_labels)

        operation_success = self._safe_metric_operation(
            "update queue size",
            self.collector.set_gauge,
            metric_name,
            value=float(size),
            labels=labels,
            help_text="Current queue size for pipeline stage.",
        )

        if not operation_success:
            return None

        return PipelineStatsEvent(
            pipeline_id=self.pipeline_id,
            metric_name=metric_name,
            metric_value=float(size),
            labels=labels,
        )

    def update_last_event_processed_timestamp(
        self, *, timestamp: float, stage: str
    ) -> PipelineStatsEvent | None:
        """Update the timestamp of the last successfully processed event."""
        # Validate inputs
        if timestamp < 0:
            error_msg = "timestamp must be non-negative"
            raise ValueError(error_msg)
        if not stage.strip():
            error_msg = "stage cannot be empty"
            raise ValueError(error_msg)

        metric_name = self._make_metric_name("last_event_processed_timestamp_seconds")
        op_labels = {"stage": stage}
        labels = self._make_labels(op_labels)

        operation_success = self._safe_metric_operation(
            "update last event processed timestamp",
            self.collector.set_gauge,
            metric_name,
            value=timestamp,
            labels=labels,
            help_text="Timestamp of the last successfully processed event.",
        )

        if not operation_success:
            return None

        return PipelineStatsEvent(
            pipeline_id=self.pipeline_id,
            metric_name=metric_name,
            metric_value=timestamp,
            labels=labels,
        )

    def record_backpressure_event(
        self, *, stage: str, reason: str
    ) -> PipelineStatsEvent | None:
        """Record a backpressure event."""
        metric_name = self._make_metric_name("backpressure_events_total")
        op_labels = {"stage": stage, "reason": reason}
        labels = self._make_labels(op_labels)

        success = self._safe_metric_operation(
            "record backpressure event",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total number of backpressure events.",
        )

        if not success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return PipelineStatsEvent(
            pipeline_id=self.pipeline_id,
            metric_name=metric_name,
            metric_value=current_value,
            labels=labels,
        )

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all pipeline statistics."""
        return self.registry.get_registry_summary()
