# pyright: strict
"""Weather Wire receiver statistics collection using the metrics system."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from loguru import logger

from nwws.metrics import MetricRegistry, MetricsCollector


@dataclass(frozen=True)
class ReceiverStatsEvent:
    """Event representing receiver statistics and metrics."""

    receiver_id: str
    """Identifier for the receiver instance."""

    metric_name: str
    """Prometheus-compliant name of the metric (e.g., 'nwws_xmpp_connection_attempts_total')."""

    metric_value: float | int | str
    """Value of the metric being reported or observed."""

    timestamp: float = field(default_factory=time.time)
    """When this stat was recorded."""

    duration_seconds: float | None = None
    """Operation duration in seconds, if applicable."""

    success: bool = True
    """Whether the underlying operation (if any) represented by the event was successful."""

    labels: dict[str, str] = field(default_factory=dict)
    """Metric labels (tags) for dimensional analysis, including receiver_id."""


class WeatherWireStatsCollector:
    """Statistics collector specifically for WeatherWire receiver operations."""

    def __init__(
        self,
        registry: MetricRegistry,
        receiver_id: str = "weather_wire",
        metric_prefix: str = "nwws",
    ) -> None:
        """Initialize with a registry instance and receiver identifier.

        Args:
            registry: MetricRegistry instance for recording metrics
            receiver_id: Identifier for the receiver instance
            metric_prefix: Prefix for all metric names (default: "nwws")

        """
        self.receiver_id = receiver_id
        self.metric_prefix = metric_prefix
        self.registry = registry
        self.collector = MetricsCollector(registry)

    def _make_metric_name(self, name: str) -> str:
        """Create a full metric name with prefix."""
        return f"{self.metric_prefix}_{name}"

    def _make_labels(
        self, additional_labels: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Create labels dict with receiver_id and any additional labels."""
        base_labels: dict[str, str] = {"receiver": self.receiver_id}
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

    def record_connection_attempt(self) -> ReceiverStatsEvent | None:
        """Record a connection attempt."""
        metric_name = self._make_metric_name("xmpp_connection_attempts_total")
        labels = self._make_labels()

        success = self._safe_metric_operation(
            "record connection attempt",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total number of XMPP connection attempts.",
        )

        if not success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=current_value,
            labels=labels,
        )

    def record_connection_result(
        self, *, success: bool, reason: str | None = None
    ) -> ReceiverStatsEvent | None:
        """Record a connection result (success or failure)."""
        metric_name = self._make_metric_name("xmpp_connections_total")
        result_str = "success" if success else "failure"
        op_labels = {"result": result_str}

        if not success and reason:
            op_labels["reason"] = reason

        labels = self._make_labels(op_labels)

        operation_success = self._safe_metric_operation(
            "record connection result",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total XMPP connections established or failed.",
        )

        if not operation_success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=current_value,
            success=success,
            labels=labels,
        )

    def update_connection_status(
        self, *, is_connected: bool
    ) -> ReceiverStatsEvent | None:
        """Update the connection status gauge."""
        metric_name = self._make_metric_name("xmpp_connection_status")
        status_value = 1.0 if is_connected else 0.0
        labels = self._make_labels()

        operation_success = self._safe_metric_operation(
            "update connection status",
            self.collector.set_gauge,
            metric_name,
            value=status_value,
            labels=labels,
            help_text="Current XMPP connection status (1 for connected, 0 for disconnected).",
        )

        if not operation_success:
            return None

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=status_value,
            labels=labels,
        )

    def record_authentication_failure(
        self, *, reason: str
    ) -> ReceiverStatsEvent | None:
        """Record an authentication failure."""
        if not reason.strip():
            error_msg = "reason cannot be empty"
            raise ValueError(error_msg)

        metric_name = self._make_metric_name("xmpp_auth_failures_total")
        labels = self._make_labels({"reason": reason})

        operation_success = self._safe_metric_operation(
            "record authentication failure",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total XMPP authentication failures.",
        )

        if not operation_success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=current_value,
            success=False,
            labels=labels,
        )

    def record_disconnection(self, *, reason: str) -> ReceiverStatsEvent | None:
        """Record a disconnection event."""
        if not reason.strip():
            error_msg = "reason cannot be empty"
            raise ValueError(error_msg)

        metric_name = self._make_metric_name("xmpp_disconnections_total")
        labels = self._make_labels({"reason": reason})

        operation_success = self._safe_metric_operation(
            "record disconnection",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total XMPP disconnections, categorized by reason.",
        )

        if not operation_success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=current_value,
            labels=labels,
        )

    def record_reconnect_attempt(self) -> ReceiverStatsEvent | None:
        """Record a reconnection attempt."""
        metric_name = self._make_metric_name("xmpp_reconnect_attempts_total")
        labels = self._make_labels()

        operation_success = self._safe_metric_operation(
            "record reconnect attempt",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total number of XMPP reconnection attempts initiated.",
        )

        if not operation_success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=current_value,
            labels=labels,
        )

    def record_message_processed(
        self,
        *,
        processing_duration_seconds: float,
        message_delay_seconds: float,
        message_size_bytes: int,
        office_id: str,
    ) -> ReceiverStatsEvent | None:
        """Record a message that was successfully processed."""
        # Validate inputs
        if processing_duration_seconds < 0:
            error_msg = "processing_duration_seconds must be non-negative"
            raise ValueError(error_msg)
        if message_delay_seconds < 0:
            error_msg = "message_delay_seconds must be non-negative"
            raise ValueError(error_msg)
        if message_size_bytes < 0:
            error_msg = "message_size_bytes must be non-negative"
            raise ValueError(error_msg)
        if not office_id.strip():
            error_msg = "office_id cannot be empty"
            raise ValueError(error_msg)

        base_op_labels = {"office_id": office_id}
        labels = self._make_labels(base_op_labels)

        # Update all metrics
        operations_successful = 0

        # 1. Total processed counter
        total_metric_name = self._make_metric_name("messages_processed_total")
        if self._safe_metric_operation(
            "increment messages processed counter",
            self.collector.increment_counter,
            total_metric_name,
            labels=labels,
            help_text="Total number of messages successfully processed.",
        ):
            operations_successful += 1

        # Do not record office label for following metrics
        labels = self._make_labels()

        # 2. Processing duration histogram
        proc_dur_metric_name = self._make_metric_name(
            "message_processing_duration_seconds"
        )
        if self._safe_metric_operation(
            "observe processing duration",
            self.collector.observe_histogram,
            proc_dur_metric_name,
            processing_duration_seconds,
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5],
            labels=labels,
            help_text="Time taken to process a message from receipt to pipeline",
        ):
            operations_successful += 1

        # 3. Reception delay histogram
        rec_delay_metric_name = self._make_metric_name(
            "message_reception_delay_seconds"
        )
        if self._safe_metric_operation(
            "observe reception delay",
            self.collector.observe_histogram,
            rec_delay_metric_name,
            message_delay_seconds,
            buckets=[0.1, 0.5, 1, 5, 10, 30, 60, 300, 1800, 3600],
            labels=labels,
            help_text="Delay between message issue timestamp and its reception",
        ):
            operations_successful += 1

        # 4. Message size histogram
        size_metric_name = self._make_metric_name("message_size_bytes")
        if self._safe_metric_operation(
            "observe message size",
            self.collector.observe_histogram,
            size_metric_name,
            float(message_size_bytes),
            buckets=[256, 512, 1024, 2048, 4096, 8192, 16384],
            labels=labels,
            help_text="Size of received messages",
        ):
            operations_successful += 1

        # Return None if all operations failed
        if operations_successful == 0:
            return None

        # Return event for the primary metric (processed count)
        current_total = (
            self.collector.get_metric_value(total_metric_name, labels=labels) or 1
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=total_metric_name,
            metric_value=current_total,
            duration_seconds=processing_duration_seconds,
            labels=labels,
        )

    def record_message_processing_error(
        self, *, error_type: str, office_id: str | None = None
    ) -> ReceiverStatsEvent | None:
        """Record a message processing error."""
        if not error_type.strip():
            error_msg = "error_type cannot be empty"
            raise ValueError(error_msg)

        metric_name = self._make_metric_name("message_processing_errors_total")
        op_labels = {"error_type": error_type}

        if office_id:
            op_labels["office_id"] = office_id
        else:
            op_labels["office_id"] = "unknown"

        labels = self._make_labels(op_labels)

        operation_success = self._safe_metric_operation(
            "record message processing error",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total errors encountered during message processing.",
        )

        if not operation_success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=current_value,
            success=False,
            labels=labels,
        )

    def update_last_message_received_timestamp(
        self, *, timestamp: float, office_id: str
    ) -> ReceiverStatsEvent | None:
        """Update the timestamp of the last successfully processed message."""
        if not office_id.strip():
            error_msg = "office_id cannot be empty"
            raise ValueError(error_msg)

        metric_name = self._make_metric_name("last_message_received_timestamp_seconds")
        labels = self._make_labels({"office_id": office_id})

        operation_success = self._safe_metric_operation(
            "update last message timestamp",
            self.collector.set_gauge,
            metric_name,
            value=timestamp,
            labels=labels,
            help_text="Unix timestamp of the last successfully processed message, by office.",
        )

        if not operation_success:
            return None

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=timestamp,
            labels=labels,
        )

    def record_idle_timeout(self) -> ReceiverStatsEvent | None:
        """Record an idle timeout event."""
        metric_name = self._make_metric_name("xmpp_idle_timeouts_total")
        labels = self._make_labels()

        operation_success = self._safe_metric_operation(
            "record idle timeout",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total number of XMPP idle timeouts detected.",
        )

        if not operation_success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=current_value,
            labels=labels,
        )

    def record_muc_join_result(
        self, *, muc_room: str, success: bool
    ) -> ReceiverStatsEvent | None:
        """Record a MUC room join result."""
        if not muc_room.strip():
            error_msg = "muc_room cannot be empty"
            raise ValueError(error_msg)

        metric_name = self._make_metric_name("xmpp_muc_joins_total")
        result_str = "success" if success else "failure"
        labels = self._make_labels({"muc_room": muc_room, "result": result_str})

        operation_success = self._safe_metric_operation(
            "record MUC join result",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total MUC room join attempts, categorized by room and result.",
        )

        if not operation_success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=current_value,
            success=success,
            labels=labels,
        )

    def record_stanza_not_sent(self, *, stanza_type: str) -> ReceiverStatsEvent | None:
        """Record a stanza that failed to send."""
        if not stanza_type.strip():
            error_msg = "stanza_type cannot be empty"
            raise ValueError(error_msg)

        metric_name = self._make_metric_name("xmpp_stanzas_dropped_total")
        labels = self._make_labels({"stanza_type": stanza_type})

        operation_success = self._safe_metric_operation(
            "record stanza not sent",
            self.collector.increment_counter,
            metric_name,
            labels=labels,
            help_text="Total number of XMPP stanzas that failed to send, by stanza type.",
        )

        if not operation_success:
            return None

        current_value = self.collector.get_metric_value(metric_name, labels=labels) or 1

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=current_value,
            success=False,
            labels=labels,
        )
