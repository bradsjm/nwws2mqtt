# pyright: strict
"""Weather Wire receiver statistics collection."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nwws.pipeline.stats import PipelineStats


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

    def __init__(self, stats: PipelineStats, receiver_id: str = "weather-wire") -> None:
        """Initialize with a stats instance and receiver identifier."""
        self.stats = stats
        self.receiver_id = receiver_id

    def record_connection_attempt(self) -> ReceiverStatsEvent:
        """Record a connection attempt."""
        metric_name = f"{self.receiver_id}.connection.attempts"
        self.stats.increment(metric_name)

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=self.stats.get_counter(metric_name),
        )

    def record_connection_success(self, duration_ms: float) -> ReceiverStatsEvent:
        """Record a successful connection."""
        metric_name = f"{self.receiver_id}.connection.success"
        self.stats.increment(metric_name)
        self.stats.record_time(f"{self.receiver_id}.connection.time", duration_ms)

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=self.stats.get_counter(metric_name),
            duration_ms=duration_ms,
        )

    def record_connection_failure(self, reason: str) -> ReceiverStatsEvent:
        """Record a connection failure."""
        metric_name = f"{self.receiver_id}.connection.failures"
        self.stats.increment(metric_name)
        self.stats.record_error(f"{self.receiver_id}.connection")

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=self.stats.get_counter(metric_name),
            success=False,
            details={"reason": reason},
        )

    def record_authentication_failure(self) -> ReceiverStatsEvent:
        """Record an authentication failure."""
        metric_name = f"{self.receiver_id}.auth.failures"
        self.stats.increment(metric_name)
        self.stats.record_error(f"{self.receiver_id}.auth")

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=self.stats.get_counter(metric_name),
            success=False,
        )

    def record_disconnection(self, reason: str) -> ReceiverStatsEvent:
        """Record a disconnection event."""
        metric_name = f"{self.receiver_id}.disconnections"
        self.stats.increment(metric_name)

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=self.stats.get_counter(metric_name),
            details={"reason": reason},
        )

    def record_message_received(self, duration_ms: float) -> ReceiverStatsEvent:
        """Record a message received and processed."""
        metric_name = f"{self.receiver_id}.messages.received"
        self.stats.increment(metric_name)
        self.stats.record_time(
            f"{self.receiver_id}.messages.processing_time",
            duration_ms,
        )

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=self.stats.get_counter(metric_name),
            duration_ms=duration_ms,
        )

    def record_message_error(self, error_type: str) -> ReceiverStatsEvent:
        """Record a message processing error."""
        metric_name = f"{self.receiver_id}.messages.errors.{error_type}"
        self.stats.increment(metric_name)
        self.stats.record_error(f"{self.receiver_id}.messages")

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=self.stats.get_counter(metric_name),
            success=False,
            details={"error_type": error_type},
        )

    def record_idle_timeout(self, idle_duration_sec: float) -> ReceiverStatsEvent:
        """Record an idle timeout event."""
        metric_name = f"{self.receiver_id}.idle_timeouts"
        self.stats.increment(metric_name)

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=self.stats.get_counter(metric_name),
            details={"idle_duration_sec": idle_duration_sec},
        )

    def record_reconnection(self) -> ReceiverStatsEvent:
        """Record a forced reconnection."""
        metric_name = f"{self.receiver_id}.reconnections"
        self.stats.increment(metric_name)

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=self.stats.get_counter(metric_name),
        )

    def update_connection_status(self, *, is_connected: bool) -> ReceiverStatsEvent:
        """Update the connection status gauge."""
        metric_name = f"{self.receiver_id}.connection.status"
        status_value = 1.0 if is_connected else 0.0
        self.stats.set_gauge(metric_name, status_value)

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=status_value,
        )

    def update_last_message_age(self, age_seconds: float) -> ReceiverStatsEvent:
        """Update the age of the last received message."""
        metric_name = f"{self.receiver_id}.last_message_age_seconds"
        self.stats.set_gauge(metric_name, age_seconds)

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=metric_name,
            metric_value=age_seconds,
        )

    def record_delayed_message(self, delay_ms: float) -> ReceiverStatsEvent:
        """Record a delayed message and its delay duration."""
        # Record count of delayed messages
        delay_count_metric = f"{self.receiver_id}.messages.delayed"
        self.stats.increment(delay_count_metric)

        # Record delay timing
        delay_time_metric = f"{self.receiver_id}.messages.delay_time"
        self.stats.record_time(delay_time_metric, delay_ms)

        return ReceiverStatsEvent(
            receiver_id=self.receiver_id,
            metric_name=delay_count_metric,
            metric_value=self.stats.get_counter(delay_count_metric),
            duration_ms=delay_ms,
            details={"delay_ms": delay_ms},
        )

    def get_delay_stats(self) -> dict[str, float | int]:
        """Get delay statistics summary."""
        delay_count_metric = f"{self.receiver_id}.messages.delayed"
        delay_time_metric = f"{self.receiver_id}.messages.delay_time"

        delay_count = self.stats.get_counter(delay_count_metric)
        avg_delay = self.stats.get_average_time(delay_time_metric)

        # Get min/max from summary data instead of accessing private members
        summary = self.stats.get_summary()
        timer_data = summary["timers"].get(delay_time_metric, {})
        min_delay = timer_data.get("min", 0.0)
        max_delay = timer_data.get("max", 0.0)

        return {
            "delayed_message_count": delay_count,
            "avg_delay_ms": avg_delay or 0.0,
            "min_delay_ms": min_delay,
            "max_delay_ms": max_delay,
        }
