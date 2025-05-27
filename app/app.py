"""Refactored NWWS-OI application using autonomous handlers."""

import asyncio
import os
import signal
import sys
import threading
from types import FrameType

# Add app directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import Config, OutputConfig, XMPPConfig

from dotenv import load_dotenv
from loguru import logger
from twisted.internet import reactor

from handlers import HandlerRegistry
from messaging import MessageBus, Topics
from receiver import NWWSXMPPClient
from stats import StatsCollector, StatsConsumer, StatsLogger, PrometheusMetricsExporter

"""
Refactored NWWS-OI application that uses autonomous handlers instead of centralized
output management. Each handler subscribes directly to the pubsub system for better
isolation and reliability.
"""

load_dotenv(override=True)  # Load environment variables from .env file


class RefactoredNWWSApplication:
    """Refactored NWWS-OI Application with autonomous handlers."""

    def __init__(self, config: Config) -> None:
        """Initialize the application with configuration."""
        self.config = config
        self.is_shutting_down = False

        # Initialize statistics collection
        self.stats_collector = StatsCollector()
        self.stats_consumer = StatsConsumer(self.stats_collector)
        self.stats_logger = StatsLogger(self.stats_collector, config.stats_interval)

        # Initialize Prometheus metrics exporter if enabled
        self.metrics_exporter = None
        if config.metrics_enabled:
            self.metrics_exporter = PrometheusMetricsExporter(
                self.stats_collector, port=config.metrics_port, update_interval=config.metrics_update_interval
            )

        # Initialize handler registry (replaces OutputManager)
        if config.output_config:
            self.handler_registry = HandlerRegistry(config.output_config)
        else:
            # Fallback to console output
            fallback_config = OutputConfig(enabled_handlers=["console"])
            self.handler_registry = HandlerRegistry(fallback_config)

        # Setup enhanced logging
        self._setup_logging()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Create XMPP client
        xmpp_config = XMPPConfig(username=config.username, password=config.password, server=config.server, port=config.port)
        self.xmpp_client = NWWSXMPPClient(xmpp_config)

        # Subscribe to XMPP error events for shutdown logic
        MessageBus.subscribe(Topics.XMPP_ERROR, self._on_xmpp_error)

        logger.info("Starting refactored NWWS-OI application", username=config.username, server=config.server)

        # Start statistics logging
        self.stats_logger.start()

        # Start statistics consumer to listen to message bus events
        self.stats_consumer.start()

        # Start Prometheus metrics exporter if enabled
        if self.metrics_exporter:
            self.metrics_exporter.start()
            logger.info("Prometheus metrics available", url=self.metrics_exporter.metrics_url)

        # Start autonomous handlers
        self._start_handlers()

        # Connect to XMPP server
        self.xmpp_client.connect()

    def _start_handlers(self) -> None:
        """Start autonomous handlers in the reactor context."""

        def start_handlers():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.handler_registry.start())
                logger.info("Autonomous handlers started successfully")
            except Exception as e:
                logger.error("Failed to start autonomous handlers", error=str(e))
            finally:
                loop.close()

        # Run in a separate thread to avoid blocking the reactor
        handler_thread = threading.Thread(target=start_handlers, daemon=True)
        handler_thread.start()

    def _setup_logging(self) -> None:
        """Configure structured logging."""
        logger.remove()  # Remove default handler

        def format_record(record):
            """Custom formatter that handles structured data."""
            # Format the basic message first
            basic_format = (
                "<green>{time:MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            )

            # Use loguru's formatter to format the basic message
            formatted_message = basic_format.format_map(record)

            # Append extra data
            if record["extra"]:
                extra_str = " | ".join([f"<cyan>{k}</cyan>=<magenta>{v}</magenta>" for k, v in record["extra"].items()])
                formatted_message += f" | {extra_str}"

            return formatted_message + "\n"

        logger.add(
            sys.stdout,
            level=self.config.log_level,
            format=format_record,
            serialize=False,
        )

        # Only add file logging if log_file is specified
        if self.config.log_file:

            def format_file_record(record):
                """File formatter without color codes."""
                # Format the basic message first
                basic_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}"
                formatted_message = basic_format.format_map(record)

                # Append extra data
                if record["extra"]:
                    extra_str = " | ".join([f"{k}={v}" for k, v in record["extra"].items()])
                    formatted_message += f" | {extra_str}"

                return formatted_message + "\n"

            logger.add(
                self.config.log_file,
                level=self.config.log_level,
                rotation="10 MB",
                retention="7 days",
                format=format_file_record,
            )
            logger.info("File logging enabled", log_file=self.config.log_file)

    def _signal_handler(self, signum: int, _frame: FrameType | None) -> None:
        """Handle shutdown signals gracefully."""
        logger.info("Received shutdown signal, initiating graceful shutdown", signal=signum)
        reactor.callFromThread(self.shutdown)  # type: ignore

    def _on_xmpp_error(self, error_msg: str) -> None:
        """Handle XMPP client errors."""
        logger.error("XMPP client error", error_msg=error_msg)
        if "Maximum reconnection attempts reached" in error_msg or "authentication failure" in error_msg:
            if "authentication failure" in error_msg:
                # Publish auth failure event to stats
                MessageBus.publish(Topics.STATS_AUTH_FAILURE)
            logger.error("Fatal XMPP error, shutting down application")
            self.shutdown()

    def shutdown(self) -> None:
        """Gracefully shutdown the application."""
        if self.is_shutting_down:
            return

        logger.info("Shutting down refactored NWWS-OI application")
        self.is_shutting_down = True

        # Unsubscribe from XMPP error events
        MessageBus.unsubscribe(Topics.XMPP_ERROR, self._on_xmpp_error)

        # Stop statistics logging
        try:
            self.stats_logger.stop()
        except Exception as e:
            logger.error("Error stopping stats logger", error=str(e))

        # Stop statistics consumer
        try:
            self.stats_consumer.stop()
        except Exception as e:
            logger.error("Error stopping stats consumer", error=str(e))

        # Stop Prometheus metrics exporter
        if self.metrics_exporter:
            try:
                self.metrics_exporter.stop()
            except Exception as e:
                logger.error("Error stopping metrics exporter", error=str(e))

        # Log final statistics
        try:
            self.stats_logger.log_current_stats()
        except Exception as e:
            logger.error("Error logging final stats", error=str(e))

        # Shutdown XMPP client first
        try:
            self.xmpp_client.shutdown()
        except Exception as e:
            logger.error("Error shutting down XMPP client", error=str(e))

        # Stop autonomous handlers
        try:

            def stop_handlers():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.handler_registry.stop())
                    logger.info("Autonomous handlers stopped")
                except Exception as e:
                    logger.error("Error stopping autonomous handlers", error=str(e))
                finally:
                    loop.close()

            stop_thread = threading.Thread(target=stop_handlers, daemon=True)
            stop_thread.start()
            stop_thread.join(timeout=5.0)  # Wait up to 5 seconds
        except Exception as e:
            logger.error("Error during handler shutdown", error=str(e))

        # Give time for cleanup before stopping reactor
        reactor.callLater(1.0, self._final_shutdown)  # type: ignore

    def _final_shutdown(self) -> None:
        """Final shutdown step - stop the reactor."""
        logger.info("Stopping reactor")
        reactor.stop()  # type: ignore


def main() -> None:
    """Main entry point."""
    try:
        config = Config.from_env()
        _app = RefactoredNWWSApplication(config)
        reactor.run()  # type: ignore

    except ValueError as e:
        logger.error("Configuration error", error=str(e))
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        sys.exit(1)
    finally:
        logger.info("Refactored NWWS-OI application stopped")


if __name__ == "__main__":
    main()
