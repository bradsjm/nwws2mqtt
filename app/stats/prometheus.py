"""Prometheus metrics exporter for NWWS2MQTT."""

import threading

from loguru import logger
from prometheus_client import Counter, Gauge, Info, start_http_server
from prometheus_client.core import CollectorRegistry
from twisted.internet.task import LoopingCall

from app.utils.logging_config import LoggingConfig

from .collector import StatsCollector
from .statistic_models import ApplicationStats, OutputHandlerStats


def create_counter(
    name: str,
    documentation: str,
    labelnames: list[str] | None = None,
    registry: CollectorRegistry | None = None,
) -> Counter:
    """Create a Counter without _created series."""
    return Counter(name, documentation, labelnames=labelnames or [], registry=registry)


class PrometheusMetricsExporter:
    """PrometheusMetricsExporter is responsible for exporting statistics as Prometheus metrics.

    This class initializes and manages a Prometheus HTTP server that exposes various application,
    connection, message processing, and output handler metrics. It periodically updates these
    metrics based on the current statistics collected from the application.

    Attributes:
        stats_collector (StatsCollector): The statistics collector instance.
        port (int): The port on which the Prometheus metrics server is served.
        update_interval (int): Interval in seconds for updating metrics.
        registry (CollectorRegistry): Custom Prometheus registry for metrics.
        _is_running (bool): Indicates if the exporter is currently running.
        _update_task (Optional[LoopingCall]): Periodic task for updating metrics.
        _server_thread (Optional[threading.Thread]): Thread running the HTTP server.

    Methods:
        start(): Starts the Prometheus metrics server and begins periodic metric updates.
        stop(): Stops the metrics update loop and the exporter.
        is_running: Property indicating if the exporter is running.
        metrics_url: Property returning the URL of the metrics endpoint.

    Prometheus Metrics Exposed:
        - Application info and uptime
        - Connection status, uptime, and event counters
        - Message processing totals, error rates, and breakdowns by type/source/AFOS code
        - Output handler connection status, publish/failure counters, and success rates

    Usage:
        exporter = PrometheusMetricsExporter(stats_collector)
        exporter.start()
        # Metrics available at exporter.metrics_url

    """

    def __init__(
        self,
        stats_collector: StatsCollector,
        port: int = 8080,
        update_interval: int = 30,
    ):
        """Initialize the Prometheus metrics exporter.

        Args:
            stats_collector: The statistics collector instance
            port: Port to serve metrics on
            update_interval: How often to update metrics (seconds)

        """
        # Ensure logging is properly configured
        LoggingConfig.ensure_configured()

        self.stats_collector = stats_collector
        self.port = port
        self.update_interval = update_interval
        self._update_task: LoopingCall | None = None
        self._server_thread: threading.Thread | None = None
        self._last_connection_values: dict[str, int] = {
            "total_connections": 0,
            "total_disconnections": 0,
            "reconnect_attempts": 0,
            "auth_failures": 0,
            "connection_errors": 0,
        }
        self._last_message_values: dict[str, int] = {
            "total_received": 0,
            "total_processed": 0,
            "total_published": 0,
        }
        self._last_message_error_values: dict[str, int] = {}
        self._last_wmo_values: dict[str, int] = {}
        self._last_source_values: dict[str, int] = {}
        self._last_afos_values: dict[str, int] = {}
        self._last_handler_values: dict[str, dict[str, int]] = {}

        # Create custom registry to avoid conflicts
        self.registry = CollectorRegistry()
        self.registry = CollectorRegistry()

        # Initialize Prometheus metrics
        self._init_metrics()

        logger.info(
            "Prometheus metrics exporter initialized",
            port=port,
            update_interval=update_interval,
        )

    def _init_metrics(self) -> None:
        """Initialize all Prometheus metrics."""
        # Application info
        self.app_info = Info(
            "nwws2mqtt_application_info",
            "Application information",
            registry=self.registry,
        )

        # Application uptime
        self.app_uptime_seconds = Gauge(
            "nwws2mqtt_application_uptime_seconds",
            "Application uptime in seconds",
            registry=self.registry,
        )

        # Connection metrics
        self.connection_status = Gauge(
            "nwws2mqtt_connection_status",
            "XMPP connection status (1=connected, 0=disconnected)",
            registry=self.registry,
        )

        self.connection_uptime_seconds = Gauge(
            "nwws2mqtt_connection_uptime_seconds",
            "Current connection uptime in seconds",
            registry=self.registry,
        )

        self.connection_total_connections = create_counter(
            "nwws2mqtt_connection_total_connections",
            "Total number of connections made",
            registry=self.registry,
        )

        self.connection_total_disconnections = create_counter(
            "nwws2mqtt_connection_total_disconnections",
            "Total number of disconnections",
            registry=self.registry,
        )

        self.connection_reconnect_attempts = create_counter(
            "nwws2mqtt_connection_reconnect_attempts_total",
            "Total number of reconnection attempts",
            registry=self.registry,
        )

        self.connection_auth_failures = create_counter(
            "nwws2mqtt_connection_auth_failures_total",
            "Total number of authentication failures",
            registry=self.registry,
        )

        self.connection_errors = create_counter(
            "nwws2mqtt_connection_errors_total",
            "Total number of connection errors",
            registry=self.registry,
        )

        self.outstanding_pings = Gauge(
            "nwws2mqtt_connection_outstanding_pings",
            "Number of outstanding ping requests",
            registry=self.registry,
        )

        # Message processing metrics
        self.messages_received_total = create_counter(
            "nwws2mqtt_messages_received_total",
            "Total number of messages received",
            registry=self.registry,
        )

        self.messages_processed_total = create_counter(
            "nwws2mqtt_messages_processed_total",
            "Total number of messages successfully processed",
            registry=self.registry,
        )

        self.messages_failed_total = create_counter(
            "nwws2mqtt_messages_failed_total",
            "Total number of messages that failed processing",
            labelnames=["error_type"],
            registry=self.registry,
        )

        self.messages_published_total = create_counter(
            "nwws2mqtt_messages_published_total",
            "Total number of messages published to output handlers",
            registry=self.registry,
        )

        self.message_processing_success_rate = Gauge(
            "nwws2mqtt_message_processing_success_rate",
            "Message processing success rate as percentage",
            registry=self.registry,
        )

        self.message_processing_error_rate = Gauge(
            "nwws2mqtt_message_processing_error_rate",
            "Message processing error rate as percentage",
            registry=self.registry,
        )

        # WMO code metrics
        self.wmo_total = create_counter(
            "nwws2mqtt_wmo_total",
            "Total count by WMO code",
            labelnames=["wmo_code"],
            registry=self.registry,
        )

        # Source metrics
        self.sources_total = create_counter(
            "nwws2mqtt_sources_total",
            "Total count by source",
            labelnames=["source"],
            registry=self.registry,
        )

        # AFOS code metrics
        self.afos_codes_total = create_counter(
            "nwws2mqtt_afos_codes_total",
            "Total count by AFOS code",
            labelnames=["afos_code"],
            registry=self.registry,
        )

        # Output handler metrics
        self.output_handler_status = Gauge(
            "nwws2mqtt_output_handler_status",
            "Output handler connection status (1=connected, 0=disconnected)",
            ["handler_name", "handler_type"],
            registry=self.registry,
        )

        self.output_handler_published_total = create_counter(
            "nwws2mqtt_output_handler_published_total",
            "Total messages published by output handler",
            labelnames=["handler_name", "handler_type"],
            registry=self.registry,
        )

        self.output_handler_failed_total = create_counter(
            "nwws2mqtt_output_handler_failed_total",
            "Total failed publishes by output handler",
            labelnames=["handler_name", "handler_type"],
            registry=self.registry,
        )

        self.output_handler_connection_errors = create_counter(
            "nwws2mqtt_output_handler_connection_errors_total",
            "Total connection errors for output handler",
            labelnames=["handler_name", "handler_type"],
            registry=self.registry,
        )

        self.output_handler_success_rate = Gauge(
            "nwws2mqtt_output_handler_success_rate",
            "Output handler success rate as percentage",
            ["handler_name", "handler_type"],
            registry=self.registry,
        )

    def start(self) -> None:
        """Start the Prometheus metrics server and update loop."""
        if self._is_running:
            logger.warning("Prometheus metrics exporter is already running")
            return

        try:
            # Start HTTP server in a separate thread
            self._server_thread = threading.Thread(target=self._start_http_server, daemon=True)
            self._server_thread.start()

            # Start metrics update loop
            self._update_task = LoopingCall(self._update_metrics)
            self._update_task.start(self.update_interval)

            self._is_running = True
            logger.info("Prometheus metrics server started", port=self.port)

        except Exception as e:
            logger.error("Failed to start Prometheus metrics server", error=str(e))
            raise

    def stop(self) -> None:
        """Stop the metrics update loop."""
        if not self._is_running:
            return

        try:
            if self._update_task and self._update_task.running:
                self._update_task.stop()

            self._is_running = False
            logger.info("Prometheus metrics exporter stopped")

        except (TimeoutError, OSError, ConnectionError, RuntimeError) as e:
            logger.error("Error stopping Prometheus metrics exporter", error=str(e))

    def _start_http_server(self) -> None:
        """Start the HTTP server for metrics."""
        try:
            start_http_server(self.port, registry=self.registry)
            logger.info("Prometheus HTTP server started", port=self.port)
        except (TimeoutError, OSError, ConnectionError, RuntimeError) as e:
            logger.error("Failed to start Prometheus HTTP server", error=str(e))
            raise

    def _update_metrics(self) -> None:
        """Update all Prometheus metrics with current statistics."""
        try:
            stats = self.stats_collector.get_stats()
            self._update_application_metrics(stats)
            self._update_connection_metrics(stats)
            self._update_message_metrics(stats)
            self._update_output_handler_metrics()

        except (TimeoutError, OSError, ConnectionError, RuntimeError) as e:
            logger.error("Error updating Prometheus metrics", error=str(e))

    def _update_application_metrics(self, stats: ApplicationStats) -> None:
        """Update application-level metrics."""
        # For counters, we need to track the last values and increment by the difference

    def _update_connection_metrics(self, stats: ApplicationStats) -> None:
        """Update connection-related metrics."""
        self.connection_status.set(1 if stats.connection.is_connected else 0)
        self.connection_uptime_seconds.set(stats.connection.uptime_seconds)

        # For counters, we need to track the last values and increment by the difference
        if not hasattr(self, "_last_connection_values"):
            self._last_connection_values = {
                "total_connections": 0,
                "total_disconnections": 0,
                "reconnect_attempts": 0,
                "auth_failures": 0,
                "connection_errors": 0,
            }

        # Update counters with differences
        total_connections_diff = (
            stats.connection.total_connections - self._last_connection_values["total_connections"]
        )
        if total_connections_diff > 0:
            self.connection_total_connections.inc(total_connections_diff)
            self._last_connection_values["total_connections"] = stats.connection.total_connections

        total_disconnections_diff = (
            stats.connection.total_disconnections
            - self._last_connection_values["total_disconnections"]
        )
        if total_disconnections_diff > 0:
            self.connection_total_disconnections.inc(total_disconnections_diff)
            self._last_connection_values["total_disconnections"] = (
                stats.connection.total_disconnections
            )

        reconnect_attempts_diff = (
            stats.connection.reconnect_attempts - self._last_connection_values["reconnect_attempts"]
        )
        if reconnect_attempts_diff > 0:
            self.connection_reconnect_attempts.inc(reconnect_attempts_diff)
            self._last_connection_values["reconnect_attempts"] = stats.connection.reconnect_attempts

        auth_failures_diff = (
            stats.connection.auth_failures - self._last_connection_values["auth_failures"]
        )
        if auth_failures_diff > 0:
            self.connection_auth_failures.inc(auth_failures_diff)
            self._last_connection_values["auth_failures"] = stats.connection.auth_failures

        connection_errors_diff = (
            stats.connection.connection_errors - self._last_connection_values["connection_errors"]
        )
        if connection_errors_diff > 0:
            self.connection_errors.inc(connection_errors_diff)
            self._last_connection_values["connection_errors"] = stats.connection.connection_errors

        self.outstanding_pings.set(stats.connection.outstanding_pings)

    def _update_message_metrics(self, stats: ApplicationStats) -> None:
        """Update message processing metrics."""
        self._update_message_counters(stats)
        self._update_message_error_counters(stats)
        self._update_message_rates(stats)
        self._update_message_breakdown_counters(stats)

    def _update_message_counters(self, stats: ApplicationStats) -> None:
        """Update basic message counters."""
        received_diff = stats.messages.total_received - self._last_message_values["total_received"]
        if received_diff > 0:
            self.messages_received_total.inc(received_diff)
            self._last_message_values["total_received"] = stats.messages.total_received

        processed_diff = (
            stats.messages.total_processed - self._last_message_values["total_processed"]
        )
        if processed_diff > 0:
            self.messages_processed_total.inc(processed_diff)
            self._last_message_values["total_processed"] = stats.messages.total_processed

        published_diff = (
            stats.messages.total_published - self._last_message_values["total_published"]
        )
        if published_diff > 0:
            self.messages_published_total.inc(published_diff)
            self._last_message_values["total_published"] = stats.messages.total_published

    def _update_message_error_counters(self, stats: ApplicationStats) -> None:
        """Update error counters by type."""
        for error_type, count in stats.messages.processing_errors.items():
            last_count = self._last_message_error_values.get(error_type, 0)
            diff = count - last_count
            if diff > 0:
                self.messages_failed_total.labels(error_type=error_type).inc(diff)
                self._last_message_error_values[error_type] = count

    def _update_message_rates(self, stats: ApplicationStats) -> None:
        """Update message processing rates."""
        self.message_processing_success_rate.set(stats.messages.success_rate)
        self.message_processing_error_rate.set(stats.messages.error_rate)

    def _update_message_breakdown_counters(self, stats: ApplicationStats) -> None:
        """Update message breakdown counters (WMO codes, sources, AFOS codes)."""
        # Update WMO code counters
        for wmo_code, count in stats.messages.wmo_codes.items():
            last_count = self._last_wmo_values.get(wmo_code, 0)
            diff = count - last_count
            if diff > 0:
                self.wmo_total.labels(wmo_code=wmo_code).inc(diff)
                self._last_wmo_values[wmo_code] = count

        # Update source counters
        for source, count in stats.messages.sources.items():
            last_count = self._last_source_values.get(source, 0)
            diff = count - last_count
            if diff > 0:
                self.sources_total.labels(source=source).inc(diff)
                self._last_source_values[source] = count

        # Update AFOS code counters
        for afos_code, count in stats.messages.afos_codes.items():
            last_count = self._last_afos_values.get(afos_code, 0)
            diff = count - last_count
            if diff > 0:
                self.afos_codes_total.labels(afos_code=afos_code).inc(diff)
                self._last_afos_values[afos_code] = count

    def _update_output_handler_metrics(self) -> None:
        """Update output handler metrics."""
        # Initialize last values tracking if not exists
        if not hasattr(self, "_last_handler_values"):
            self._last_handler_values = {}

        # Get output handler statistics from stats collector
        stats = self.stats_collector.get_stats()
        output_handler_stats: dict[str, OutputHandlerStats] = stats.output_handlers

        for handler_name, handler_stats in output_handler_stats.items():
            # Create labels for this handler
            labels = {
                "handler_name": handler_name,
                "handler_type": handler_stats.handler_type,
            }

            self.output_handler_status.labels(**labels).set(1 if handler_stats.is_connected else 0)

            # Initialize tracking for this handler if not exists
            if handler_name not in self._last_handler_values:
                self._last_handler_values[handler_name] = {
                    "total_published": 0,
                    "total_failed": 0,
                    "connection_errors": 0,
                }

            # Update counters with differences
            published_diff = (
                handler_stats.total_published
                - self._last_handler_values[handler_name]["total_published"]
            )
            if published_diff > 0:
                self.output_handler_published_total.labels(**labels).inc(published_diff)
                self._last_handler_values[handler_name]["total_published"] = (
                    handler_stats.total_published
                )

            failed_diff = (
                handler_stats.total_failed - self._last_handler_values[handler_name]["total_failed"]
            )
            if failed_diff > 0:
                self.output_handler_failed_total.labels(**labels).inc(failed_diff)
                self._last_handler_values[handler_name]["total_failed"] = handler_stats.total_failed

            errors_diff = (
                handler_stats.connection_errors
                - self._last_handler_values[handler_name]["connection_errors"]
            )
            if errors_diff > 0:
                self.output_handler_connection_errors.labels(**labels).inc(errors_diff)
                self._last_handler_values[handler_name]["connection_errors"] = (
                    handler_stats.connection_errors
                )

            # Update success rate
            self.output_handler_success_rate.labels(**labels).set(handler_stats.success_rate)

    @property
    def is_running(self) -> bool:
        """Check if the metrics exporter is currently running."""
        return self._is_running

    @property
    def metrics_url(self) -> str:
        """Get the metrics endpoint URL."""
        return f"http://localhost:{self.port}/metrics"
