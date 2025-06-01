# pyright: strict
"""Weather Wire receiver statistics collection using the new metrics system."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from nwws.metrics import MetricRegistry, MetricsCollector


@dataclass(frozen=True)
class ReceiverStatsEvent:
    """Event representing receiver statistics and metrics."""

    receiver_id: str
    """Identifier for the receiver instance."""

    metric_name: str
    """Name of the metric being reported."""

    metric_value: float | int | str
    """Value of the metric."""

    timestamp: float = field(default_factory=time.time)
    """When this stat was recorded."""

    duration_ms: float | None = None
    """Operation duration in milliseconds."""

    success: bool = True
    """Whether the operation was successful."""

    details: dict[str, str | int | float] = field(default_factory=dict)
    """Additional metric details."""


class WeatherWireStatsCollector:
    """Statistics collector specifically for WeatherWire receiver operations."""

    def __init__(
        self,
        registry: MetricRegistry,
        receiver_id: str = "weather_wire",
    ) -> None:
        """Initialize with a registry instance and receiver identifier."""
        self.receiver_id = receiver_id
        self.registry = registry
        self.collector = MetricsCollector(registry, prefix=receiver_id)

    def record_connection_attempt(self) -> ReceiverStatsEvent:
        """Record a connection attempt."""
        metric_name = "connection_attempts_total"

        self.collector.increment_counter(
            metric_name,
            labels={"receiver": self.receiver_id},
            help_text="Total number of connection attempts",
        )

        current_value = (
            self.collector.get_metric_value(
                metric_name,
                labels={"receiver": self.receiver_id},
            )
            or 0
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=current_value,
        )

    def record_connection_success(self, duration_ms: float) -> ReceiverStatsEvent:
        """Record a successful connection."""
        labels = {"receiver": self.receiver_id}

        # Record successful connection
        self.collector.record_operation(
            "connection",
            success=True,
            duration_ms=duration_ms,
            labels=labels,
        )

        # Update connection status
        self.collector.update_status("connection", "connected", labels=labels)

        current_value = (
            self.collector.get_metric_value(
                "operation_results_total",
                labels={**labels, "operation": "connection", "result": "success"},
            )
            or 0
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name="connection_success_total",
            metric_value=current_value,
            duration_ms=duration_ms,
        )

    def record_connection_failure(self, reason: str) -> ReceiverStatsEvent:
        """Record a connection failure."""
        labels = {"receiver": self.receiver_id, "reason": reason}

        # Record failed connection
        self.collector.record_operation(
            "connection",
            success=False,
            labels=labels,
        )

        # Update connection status
        self.collector.update_status(
            "connection", "disconnected", labels={"receiver": self.receiver_id}
        )

        # Record specific error
        self.collector.record_error(
            "connection_failure", operation="connection", labels=labels
        )

        current_value = (
            self.collector.get_metric_value(
                "operation_results_total",
                labels={
                    "receiver": self.receiver_id,
                    "operation": "connection",
                    "result": "failure",
                },
            )
            or 0
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name="connection_failures_total",
            metric_value=current_value,
            success=False,
            details={"reason": reason},
        )

    def record_authentication_failure(self) -> ReceiverStatsEvent:
        """Record an authentication failure."""
        labels = {"receiver": self.receiver_id}

        # Record auth failure
        self.collector.record_operation(
            "authentication",
            success=False,
            labels=labels,
        )

        # Record specific error
        self.collector.record_error(
            "auth_failure", operation="authentication", labels=labels
        )

        current_value = (
            self.collector.get_metric_value(
                "operation_results_total",
                labels={**labels, "operation": "authentication", "result": "failure"},
            )
            or 0
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name="auth_failures_total",
            metric_value=current_value,
            success=False,
        )

    def record_disconnection(self, reason: str) -> ReceiverStatsEvent:
        """Record a disconnection event."""
        labels = {"receiver": self.receiver_id, "reason": reason}

        self.collector.increment_counter(
            "disconnections_total",
            labels=labels,
            help_text="Total number of disconnections",
        )

        # Update connection status
        self.collector.update_status(
            "connection", "disconnected", labels={"receiver": self.receiver_id}
        )

        current_value = (
            self.collector.get_metric_value("disconnections_total", labels=labels) or 0
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name="disconnections_total",
            metric_value=current_value,
            details={"reason": reason},
        )

    def record_message_received(self, duration_ms: float) -> ReceiverStatsEvent:
        """Record a message received and processed."""
        labels = {"receiver": self.receiver_id}

        # Record message processing
        self.collector.record_operation(
            "message_processing",
            success=True,
            duration_ms=duration_ms,
            labels=labels,
        )

        current_value = (
            self.collector.get_metric_value(
                "operation_results_total",
                labels={
                    **labels,
                    "operation": "message_processing",
                    "result": "success",
                },
            )
            or 0
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name="messages_received_total",
            metric_value=current_value,
            duration_ms=duration_ms,
        )

    def record_message_error(self, error_type: str) -> ReceiverStatsEvent:
        """Record a message processing error."""
        labels = {"receiver": self.receiver_id, "error_type": error_type}

        # Record message processing failure
        self.collector.record_operation(
            "message_processing",
            success=False,
            labels=labels,
        )

        # Record specific error
        self.collector.record_error(
            "message_error", operation="message_processing", labels=labels
        )

        current_value = (
            self.collector.get_metric_value(
                "errors_total",
                labels={**labels, "operation": "message_processing"},
            )
            or 0
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name="message_errors_total",
            metric_value=current_value,
            success=False,
            details={"error_type": error_type},
        )

    def record_idle_timeout(self, idle_duration_sec: float) -> ReceiverStatsEvent:
        """Record an idle timeout event."""
        labels = {"receiver": self.receiver_id}

        self.collector.increment_counter(
            "idle_timeouts_total",
            labels=labels,
            help_text="Total number of idle timeouts",
        )

        # Record the idle duration
        self.collector.observe_histogram(
            "idle_duration_seconds",
            idle_duration_sec,
            labels=labels,
            help_text="Duration of idle periods in seconds",
        )

        current_value = (
            self.collector.get_metric_value("idle_timeouts_total", labels=labels) or 0
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name="idle_timeouts_total",
            metric_value=current_value,
            details={"idle_duration_sec": idle_duration_sec},
        )

    def record_reconnection(self) -> ReceiverStatsEvent:
        """Record a forced reconnection."""
        labels = {"receiver": self.receiver_id}

        self.collector.increment_counter(
            "reconnections_total",
            labels=labels,
            help_text="Total number of forced reconnections",
        )

        current_value = (
            self.collector.get_metric_value("reconnections_total", labels=labels) or 0
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name="reconnections_total",
            metric_value=current_value,
        )

    def update_connection_status(self, *, is_connected: bool) -> ReceiverStatsEvent:
        """Update the connection status gauge."""
        labels = {"receiver": self.receiver_id}
        status = "connected" if is_connected else "disconnected"

        self.collector.update_status("connection", status, labels=labels)

        status_value = 1.0 if is_connected else 0.0

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name="connection_status",
            metric_value=status_value,
        )

    def update_last_message_age(self, age_seconds: float) -> ReceiverStatsEvent:
        """Update the age of the last received message."""
        labels = {"receiver": self.receiver_id}

        self.collector.set_gauge(
            "last_message_age_seconds",
            age_seconds,
            labels=labels,
            help_text="Age of the last received message in seconds",
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name="last_message_age_seconds",
            metric_value=age_seconds,
        )

    def record_delayed_message(self, delay_ms: float) -> ReceiverStatsEvent:
        """Record a delayed message and its delay duration."""
        labels = {"receiver": self.receiver_id}

        # Record count of delayed messages
        self.collector.increment_counter(
            "delayed_messages_total",
            labels=labels,
            help_text="Total number of delayed messages",
        )

        # Record delay timing
        self.collector.observe_histogram(
            "message_delay_ms",
            delay_ms,
            labels=labels,
            help_text="Message delay in milliseconds",
        )

        current_value = (
            self.collector.get_metric_value("delayed_messages_total", labels=labels)
            or 0
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name="delayed_messages_total",
            metric_value=current_value,
            duration_ms=delay_ms,
            details={"delay_ms": delay_ms},
        )

    def record_muc_join_success(self, duration_ms: float) -> ReceiverStatsEvent:
        """Record a successful MUC room join."""
        labels = {"receiver": self.receiver_id}

        self.collector.record_operation(
            "muc_join",
            success=True,
            duration_ms=duration_ms,
            labels=labels,
        )

        current_value = (
            self.collector.get_metric_value(
                "operation_results_total",
                labels={**labels, "operation": "muc_join", "result": "success"},
            )
            or 0
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name="muc_join_success_total",
            metric_value=current_value,
            duration_ms=duration_ms,
        )

    def record_tls_success(self) -> ReceiverStatsEvent:
        """Record successful TLS handshake."""
        labels = {"receiver": self.receiver_id}

        self.collector.increment_counter(
            "tls_success_total",
            labels=labels,
            help_text="Total number of successful TLS handshakes",
        )

        current_value = (
            self.collector.get_metric_value("tls_success_total", labels=labels) or 0
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name="tls_success_total",
            metric_value=current_value,
        )

    def record_ssl_invalid_chain(self, error: str) -> ReceiverStatsEvent:
        """Record SSL certificate chain validation failure."""
        labels = {"receiver": self.receiver_id, "error": error}

        self.collector.record_error(
            "ssl_invalid_chain",
            operation="tls_handshake",
            labels=labels,
        )

        current_value = (
            self.collector.get_metric_value(
                "errors_total",
                labels={**labels, "operation": "tls_handshake"},
            )
            or 0
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name="ssl_invalid_chain_total",
            metric_value=current_value,
            success=False,
            details={"error": error},
        )

    def record_stanza_not_sent(self, stanza_type: str) -> ReceiverStatsEvent:
        """Record stanza send failure."""
        labels = {"receiver": self.receiver_id, "stanza_type": stanza_type}

        self.collector.increment_counter(
            "stanzas_not_sent_total",
            labels=labels,
            help_text="Total number of stanzas that failed to send",
        )

        current_value = (
            self.collector.get_metric_value("stanzas_not_sent_total", labels=labels)
            or 0
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name="stanzas_not_sent_total",
            metric_value=current_value,
            success=False,
            details={"stanza_type": stanza_type},
        )
