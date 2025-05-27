"""NWWS-OI application."""

import asyncio
import signal
import sys
import threading
from asyncio import CancelledError
from pathlib import Path
from types import FrameType

# Add app directory to Python path for imports
sys.path.insert(0, str((Path(__file__).parent.parent).resolve()))


from dotenv import load_dotenv
from loguru import logger
from twisted.internet import reactor

from app.handlers import HandlerRegistry
from app.messaging import MessageBus, Topics
from app.models import Config, OutputConfig, XMPPConfig
from app.receiver import NWWSXMPPClient
from app.stats import (
    PrometheusMetricsExporter,
    StatsCollector,
    StatsConsumer,
    StatsLogger,
    WebDashboardServer,
)
from app.utils import LoggingConfig

load_dotenv(override=True)  # Load environment variables from .env file


class NWWSApplication:
    """NWWS-OI Application."""

    def __init__(self, config: Config) -> None:
        """Initialize the application with configuration."""
        self.config = config
        self.is_shutting_down = False

        # Setup enhanced logging
        LoggingConfig.configure(config.log_level, config.log_file)

        # Initialize statistics collection
        self.stats_collector = StatsCollector()
        self.stats_consumer = StatsConsumer(self.stats_collector)
        self.stats_logger = StatsLogger(self.stats_collector, config.stats_interval)

        # Initialize Prometheus metrics exporter if enabled
        self.metrics_exporter = None
        if config.metrics_enabled:
            self.metrics_exporter = PrometheusMetricsExporter(
                self.stats_collector,
                port=config.metrics_port,
                update_interval=config.metrics_update_interval,
            )

        # Initialize web dashboard server if enabled
        self.dashboard_server = None
        if config.dashboard_enabled:
            self.dashboard_server = WebDashboardServer(
                self.stats_collector,
                port=config.dashboard_port,
                host=config.dashboard_host,
                update_interval=5.0,
            )

        # Initialize handler registry (replaces OutputManager)
        if config.output_config:
            self.handler_registry = HandlerRegistry(config.output_config)
        else:
            # Fallback to console output
            fallback_config = OutputConfig(enabled_handlers=["console"])
            self.handler_registry = HandlerRegistry(fallback_config)

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Create XMPP client
        xmpp_config = XMPPConfig(
            username=config.username,
            password=config.password,
            server=config.server,
            port=config.port,
        )
        self.xmpp_client = NWWSXMPPClient(xmpp_config)

        # Subscribe to XMPP error events for shutdown logic
        MessageBus.subscribe(Topics.XMPP_ERROR, self._on_xmpp_error)

        logger.info("Starting NWWS-OI application", username=config.username, server=config.server)

        # Start statistics logging
        self.stats_logger.start()

        # Start statistics consumer to listen to message bus events
        self.stats_consumer.start()

        # Start Prometheus metrics exporter if enabled
        if self.metrics_exporter:
            self.metrics_exporter.start()
            logger.info("Prometheus metrics available", url=self.metrics_exporter.metrics_url)

        # Start web dashboard server if enabled
        if self.dashboard_server:
            self.dashboard_server.start()
            logger.info("Web dashboard available", url=self.dashboard_server.dashboard_url)

        # Start handlers
        self._start_handlers()

        # Connect to XMPP server
        self.xmpp_client.connect()

    def _start_handlers(self) -> None:
        """Start handlers in the reactor context."""

        def start_handlers():
            # Ensure logging is configured in this thread
            LoggingConfig.reconfigure_for_thread()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.handler_registry.start())
                logger.info("handlers started successfully")
            except (TimeoutError, OSError, ConnectionError, RuntimeError) as e:
                logger.error("Failed to start handlers", error=str(e))
            finally:
                loop.close()

        # Run in a separate thread to avoid blocking the reactor
        handler_thread = threading.Thread(target=start_handlers, daemon=True)
        handler_thread.start()

    def _signal_handler(self, signum: int, _frame: FrameType | None) -> None:
        """Handle shutdown signals gracefully."""
        logger.info("Received shutdown signal, initiating graceful shutdown", signal=signum)
        reactor.callFromThread(self.shutdown)  # type: ignore  # noqa: PGH003

    def _on_xmpp_error(self, error_msg: str) -> None:
        """Handle XMPP client errors."""
        logger.error("XMPP client error", error_msg=error_msg)
        if (
            "Maximum reconnection attempts reached" in error_msg
            or "authentication failure" in error_msg
        ):
            if "authentication failure" in error_msg:
                # Publish auth failure event to stats
                MessageBus.publish(Topics.STATS_AUTH_FAILURE)
            logger.error("Fatal XMPP error, shutting down application")
            self.shutdown()

    def shutdown(self) -> None:
        """Gracefully shutdown the application."""
        if self.is_shutting_down:
            return

        logger.info("Shutting down NWWS-OI application")
        self.is_shutting_down = True

        self._cleanup_services()
        self._stop_handlers()

        # Give time for cleanup before stopping reactor
        reactor.callLater(1.0, self._final_shutdown)  # type: ignore  # noqa: PGH003

    def _cleanup_services(self) -> None:
        """Stop all application services."""
        # Unsubscribe from XMPP error events
        MessageBus.unsubscribe(Topics.XMPP_ERROR, self._on_xmpp_error)

        self._stop_stats_services()
        self._stop_monitoring_services()
        self._stop_xmpp_client()

    def _stop_stats_services(self) -> None:
        """Stop statistics-related services."""
        # Stop statistics logging
        try:
            self.stats_logger.stop()
        except (TimeoutError, OSError, ConnectionError, RuntimeError, CancelledError) as e:
            logger.error("Error stopping stats logger", error=str(e))

        # Stop statistics consumer
        try:
            self.stats_consumer.stop()
        except (TimeoutError, OSError, ConnectionError, RuntimeError, CancelledError) as e:
            logger.error("Error stopping stats consumer", error=str(e))

        # Log final statistics
        try:
            self.stats_logger.log_current_stats()
        except (TimeoutError, OSError, ConnectionError, RuntimeError, CancelledError) as e:
            logger.error("Error logging final stats", error=str(e))

    def _stop_monitoring_services(self) -> None:
        """Stop monitoring and dashboard services."""
        # Stop Prometheus metrics exporter
        if self.metrics_exporter:
            try:
                self.metrics_exporter.stop()
            except (TimeoutError, OSError, ConnectionError, RuntimeError, CancelledError) as e:
                logger.error("Error stopping metrics exporter", error=str(e))

        # Stop web dashboard server
        if self.dashboard_server:
            try:
                self.dashboard_server.stop()
            except (TimeoutError, OSError, ConnectionError, RuntimeError, CancelledError) as e:
                logger.error("Error stopping dashboard server", error=str(e))

    def _stop_xmpp_client(self) -> None:
        """Stop the XMPP client."""
        try:
            self.xmpp_client.shutdown()
        except (TimeoutError, OSError, ConnectionError, RuntimeError, CancelledError) as e:
            logger.error("Error shutting down XMPP client", error=str(e))

    def _stop_handlers(self) -> None:
        """Stop message handlers."""
        try:

            def stop_handlers():
                # Ensure logging is configured in this thread
                LoggingConfig.reconfigure_for_thread()

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.handler_registry.stop())
                    logger.info("handlers stopped")
                except (TimeoutError, OSError, ConnectionError, RuntimeError, CancelledError) as e:
                    logger.error("Error stopping handlers", error=str(e))
                finally:
                    loop.close()

            stop_thread = threading.Thread(target=stop_handlers, daemon=True)
            stop_thread.start()
            stop_thread.join(timeout=5.0)  # Wait up to 5 seconds
        except (RuntimeError, OSError) as e:
            logger.error("Error during handler shutdown", error=str(e))

    def _final_shutdown(self) -> None:
        """Stop the reactor."""
        logger.info("Stopping reactor")
        reactor.stop()  # type: ignore  # noqa: PGH003


def main() -> None:
    """Start the application."""
    try:
        config = Config.from_env()
        _app = NWWSApplication(config)
        reactor.run()  # type: ignore  # noqa: PGH003

    except ValueError as e:
        logger.error("Configuration error", error=str(e))
        sys.exit(1)
    except (TimeoutError, OSError, ConnectionError, RuntimeError, CancelledError) as e:
        logger.error("Unexpected error", error=str(e))
        sys.exit(1)
    finally:
        logger.info("NWWS-OI application stopped")


if __name__ == "__main__":
    main()
