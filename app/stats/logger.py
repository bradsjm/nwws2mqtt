"""Statistics logging and display functionality."""

from datetime import datetime, timedelta
from typing import Dict, Optional

from loguru import logger
from twisted.internet.task import LoopingCall

from .collector import StatsCollector
from .models import ApplicationStats, StatsSnapshot


class StatsLogger:
    """
    StatsLogger is responsible for periodically logging application statistics collected by a StatsCollector.
    It supports starting and stopping periodic logging, immediate logging on demand, and calculating rates
    such as messages processed per minute. The logger maintains a rolling window of recent statistics snapshots
    to compute these rates and formats the output for human readability.

    Attributes:
        stats_collector (StatsCollector): The statistics collector instance providing current stats.
        log_interval_seconds (int): Interval in seconds between periodic log outputs.
        _logging_task (Optional[LoopingCall]): Internal task for periodic logging.
        _is_running (bool): Indicates if the logger is currently running.
        _snapshots (list[StatsSnapshot]): Recent statistics snapshots for rate calculations.
        _max_snapshots (int): Maximum number of snapshots to retain for rate calculations.

    Methods:
        start(): Start periodic statistics logging.
        stop(): Stop periodic statistics logging.
        log_current_stats(): Log current statistics immediately.
        is_running: Property indicating if the logger is running.
    """

    def __init__(self, stats_collector: StatsCollector, log_interval_seconds: int = 60):
        """Initialize the stats logger.

        Args:
            stats_collector: The statistics collector instance
            log_interval_seconds: How often to log stats (default 60 seconds)
        """
        self.stats_collector = stats_collector
        self.log_interval_seconds = log_interval_seconds
        self._logging_task: Optional[LoopingCall] = None
        self._is_running = False

        # Store snapshots for rate calculations
        self._snapshots: list[StatsSnapshot] = []
        self._max_snapshots = 10  # Keep last 10 snapshots for rate calculations

        logger.debug("Statistics logger initialized", interval_seconds=log_interval_seconds)

    def start(self) -> None:
        """Start periodic statistics logging."""
        if self._is_running:
            logger.warning("Statistics logger is already running")
            return

        try:
            self._logging_task = LoopingCall(self._log_periodic_stats)
            self._logging_task.start(self.log_interval_seconds)
            self._is_running = True
            logger.info("Statistics logging started", interval_seconds=self.log_interval_seconds)
        except Exception as e:
            logger.error("Failed to start statistics logging", error=str(e))
            raise

    def stop(self) -> None:
        """Stop periodic statistics logging."""
        if not self._is_running:
            return

        try:
            if self._logging_task and self._logging_task.running:
                self._logging_task.stop()
            self._is_running = False
            logger.info("Statistics logging stopped")
        except Exception as e:
            logger.error("Error stopping statistics logging", error=str(e))

    def log_current_stats(self) -> None:
        """Log current statistics immediately."""
        try:
            stats = self.stats_collector.get_stats()
            self._log_stats(stats)
        except Exception as e:
            logger.error("Error logging current statistics", error=str(e))

    def _log_periodic_stats(self) -> None:
        """Internal method for periodic stats logging."""
        try:
            stats = self.stats_collector.get_stats()

            # Store snapshot for rate calculations
            snapshot = StatsSnapshot(timestamp=datetime.utcnow(), stats=stats)
            self._snapshots.append(snapshot)

            # Keep only recent snapshots
            if len(self._snapshots) > self._max_snapshots:
                self._snapshots = self._snapshots[-self._max_snapshots :]

            self._log_stats(stats)

        except Exception as e:
            logger.error("Error in periodic statistics logging", error=str(e))

    def _log_stats(self, stats: ApplicationStats) -> None:
        """Log formatted statistics."""
        # Calculate rates if we have previous snapshots
        rates = self._calculate_rates()

        # Format uptime
        uptime_str = self._format_duration(stats.running_time_seconds)
        connection_uptime_str = self._format_duration(stats.connection.uptime_seconds)

        # Log connection statistics
        logger.info(
            "=== NWWS2MQTT Statistics ===",
            app_uptime=uptime_str,
            connection_status="CONNECTED" if stats.connection.is_connected else "DISCONNECTED",
            connection_uptime=connection_uptime_str,
            total_connections=stats.connection.total_connections,
            reconnect_attempts=stats.connection.reconnect_attempts,
            outstanding_pings=stats.connection.outstanding_pings,
        )

        # Log message statistics
        success_rate = f"{stats.messages.success_rate:.1f}%" if stats.messages.total_received > 0 else "N/A"
        error_rate = f"{stats.messages.error_rate:.1f}%" if stats.messages.total_received > 0 else "N/A"

        logger.info(
            "Message Processing Stats",
            total_received=stats.messages.total_received,
            total_processed=stats.messages.total_processed,
            total_failed=stats.messages.total_failed,
            success_rate=success_rate,
            error_rate=error_rate,
            messages_per_minute=rates.get("messages_per_minute", 0),
            processing_per_minute=rates.get("processing_per_minute", 0),
        )

        # Log output handler statistics
        for handler_name, handler_stats in stats.output_handlers.items():
            handler_success_rate = (
                f"{handler_stats.success_rate:.1f}%" if (handler_stats.total_published + handler_stats.total_failed) > 0 else "N/A"
            )

            logger.info(
                "Output Handler Statistics",
                handler=handler_name,
                type=handler_stats.handler_type,
                status="CONNECTED" if handler_stats.is_connected else "DISCONNECTED",
                published=handler_stats.total_published,
                failed=handler_stats.total_failed,
                success_rate=handler_success_rate,
                connection_errors=handler_stats.connection_errors,
            )

    def _calculate_rates(self) -> Dict[str, float]:
        """Calculate per-minute rates from recent snapshots."""
        if len(self._snapshots) < 2:
            return {}

        # Get current and previous snapshot (1 minute ago if available)
        current = self._snapshots[-1]

        # Find snapshot from approximately 1 minute ago
        target_time = current.timestamp - timedelta(minutes=1)
        previous = None

        for snapshot in reversed(self._snapshots[:-1]):
            if snapshot.timestamp <= target_time:
                previous = snapshot
                break

        if not previous:
            # Use the oldest snapshot we have
            previous = self._snapshots[0]

        # Calculate time difference in minutes
        time_diff_minutes = (current.timestamp - previous.timestamp).total_seconds() / 60.0

        if time_diff_minutes <= 0:
            return {}

        # Calculate rates
        rates = {}

        message_diff = current.stats.messages.total_received - previous.stats.messages.total_received
        rates["messages_per_minute"] = round(message_diff / time_diff_minutes, 1)

        processing_diff = current.stats.messages.total_processed - previous.stats.messages.total_processed
        rates["processing_per_minute"] = round(processing_diff / time_diff_minutes, 1)

        return rates

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in seconds to human-readable string."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{hours:.1f}h"
        else:
            days = seconds / 86400
            return f"{days:.1f}d"

    @property
    def is_running(self) -> bool:
        """Check if the stats logger is currently running."""
        return self._is_running
