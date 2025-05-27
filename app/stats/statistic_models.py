"""Statistics data models."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class ConnectionStats:
    """Statistics for XMPP connection."""

    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    connected_at: datetime | None = None
    disconnected_at: datetime | None = None
    total_connections: int = 0
    total_disconnections: int = 0
    reconnect_attempts: int = 0
    auth_failures: int = 0
    connection_errors: int = 0
    is_connected: bool = False
    last_ping_sent: datetime | None = None
    last_pong_received: datetime | None = None
    outstanding_pings: int = 0

    @property
    def uptime_seconds(self) -> float:
        """Calculate current uptime in seconds."""
        if not self.connected_at:
            return 0.0

        end_time = self.disconnected_at if self.disconnected_at else datetime.now(UTC)
        return (end_time - self.connected_at).total_seconds()

    @property
    def total_uptime_seconds(self) -> float:
        """Calculate total uptime since start."""
        if not self.start_time:
            return 0.0
        return (datetime.now(UTC) - self.start_time).total_seconds()


@dataclass
class MessageStats:
    """Statistics for message processing."""

    total_received: int = 0
    total_processed: int = 0
    total_failed: int = 0
    total_published: int = 0
    last_message_time: datetime | None = None
    last_groupchat_message_time: datetime | None = None
    wmo_codes: Counter[str] = field(default_factory=Counter[str])
    sources: Counter[str] = field(default_factory=Counter[str])
    afos_codes: Counter[str] = field(default_factory=Counter[str])
    processing_errors: Counter[str] = field(default_factory=Counter[str])

    @property
    def success_rate(self) -> float:
        """Calculate message processing success rate."""
        if self.total_received == 0:
            return 0.0
        return (self.total_processed / self.total_received) * 100

    @property
    def error_rate(self) -> float:
        """Calculate message processing error rate."""
        if self.total_received == 0:
            return 0.0
        return (self.total_failed / self.total_received) * 100


@dataclass
class OutputHandlerStats:
    """Statistics for individual output handlers."""

    handler_type: str
    total_published: int = 0
    total_failed: int = 0
    is_connected: bool = False
    connected_at: datetime | None = None
    disconnected_at: datetime | None = None
    connection_errors: int = 0
    last_publish_time: datetime | None = None

    @property
    def success_rate(self) -> float:
        """Calculate publishing success rate."""
        total_attempts = self.total_published + self.total_failed
        if total_attempts == 0:
            return 0.0
        return (self.total_published / total_attempts) * 100


@dataclass
class ApplicationStats:
    """Overall application statistics."""

    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    connection: ConnectionStats = field(default_factory=ConnectionStats)
    messages: MessageStats = field(default_factory=MessageStats)
    output_handlers: dict[str, OutputHandlerStats] = field(
        default_factory=dict[str, OutputHandlerStats],
    )

    @property
    def running_time_seconds(self) -> float:
        """Calculate total running time in seconds."""
        return (datetime.now(UTC) - self.start_time).total_seconds()


@dataclass
class StatsSnapshot:
    """Snapshot of statistics at a point in time."""

    timestamp: datetime
    stats: ApplicationStats

    def __post_init__(self):
        """Ensure timestamp is set."""
        if not self.timestamp:
            self.timestamp = datetime.now(UTC)
