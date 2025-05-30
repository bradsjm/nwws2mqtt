"""NWWS2MQTT - National Weather Service NWWS-OI to MQTT Bridge."""

import asyncio
import signal
import sys
import time
from asyncio import CancelledError
from collections.abc import Callable
from types import FrameType, TracebackType
from typing import Any

from dotenv import load_dotenv
from loguru import logger

from nwws.filters import TestMessageFilter
from nwws.models import Config, XMPPConfig
from nwws.models.events import NoaaPortEventData
from nwws.outputs.mqtt import mqtt_factory_create
from nwws.pipeline import Pipeline
from nwws.pipeline.errors import ErrorHandler
from nwws.pipeline.stats import PipelineStats, StatsCollector
from nwws.pipeline.types import PipelineEventMetadata, PipelineStage
from nwws.receiver import WeatherWire, WeatherWireMessage
from nwws.receiver.stats import WeatherWireStatsCollector
from nwws.transformers import NoaaPortTransformer
from nwws.utils import LoggingConfig

# Load environment variables from .env file
load_dotenv(override=True)

# Type alias for signal handlers
type SignalHandler = Callable[[int, FrameType | None], None]


class WeatherWireApp:
    """NWWS Weather Wire Application."""

    def __init__(self, config: Config) -> None:
        """Initialize the application with configuration."""
        self._validate_config(config)
        self.config = config
        self.is_shutting_down = False
        self._shutdown_event = asyncio.Event()
        self._start_time = time.time()

        # Setup enhanced logging
        LoggingConfig.configure(config.log_level, config.log_file)

        # Setup signal handlers for graceful shutdown
        signal_handler: SignalHandler = self._signal_handler
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Create pipeline first to get shared stats
        self._setup_pipeline()

        # Create Weather Wire receiver with XMPP configuration and stats
        xmpp_config = XMPPConfig(
            username=config.username,
            password=config.password,
            server=config.server,
            port=config.port,
        )

        # Create receiver stats collector using the same stats instance as pipeline
        self.receiver_stats_collector = WeatherWireStatsCollector(
            self.stats,
            "weather-wire",
        )

        self.receiver = WeatherWire(
            config=xmpp_config,
            callback=self._receive_weather_message_feed,
            stats_collector=self.receiver_stats_collector,
        )

    def _validate_config(self, config: Config) -> None:
        """Validate critical configuration parameters."""
        if not config.username or not config.password:
            credentials_error = "XMPP credentials (username and password) are required"
            raise ValueError(credentials_error)
        if not config.server:
            server_error = "XMPP server is required"
            raise ValueError(server_error)
        if config.port <= 0 or config.port > 65535:
            port_error = (
                f"Invalid port number: {config.port}. Must be between 1 and 65535"
            )
            raise ValueError(port_error)

    def _setup_pipeline(self) -> None:
        """Configure and initialize the pipeline system."""
        self.stats: PipelineStats = PipelineStats()
        stats_collector = StatsCollector(self.stats)
        error_handler = ErrorHandler()
        self.pipeline: Pipeline = Pipeline(
            pipeline_id="weather-wire-pipeline",
            filters=[TestMessageFilter(filter_id="test-msg-filter")],
            transformer=NoaaPortTransformer(transformer_id="noaaport1"),
            outputs=[mqtt_factory_create(output_id="mqtt-server")],
            stats_collector=stats_collector,
            error_handler=error_handler,
        )

        logger.info("Pipeline configured", pipeline_id=self.pipeline.pipeline_id)

    async def _receive_weather_message_feed(self, event: WeatherWireMessage) -> None:
        """Handle Weather Wire content by feeding to the pipeline."""
        try:
            pipeline_event = NoaaPortEventData(
                awipsid=event.awipsid,
                cccc=event.cccc,
                id=event.id,
                issue=event.issue,
                noaaport=event.noaaport,
                subject=event.subject,
                ttaaii=event.ttaaii,
                delay_stamp=event.delay_stamp,
                metadata=PipelineEventMetadata(
                    source="weather-wire-receiver",
                    stage=PipelineStage.INGEST,
                    trace_id=event.id,
                ),
            )
            await self.pipeline.process(pipeline_event)
            logger.debug(
                "Weather wire event submitted to pipeline",
                event_id=pipeline_event.metadata.event_id,
                product_id=pipeline_event.id,
                subject=pipeline_event.subject,
            )
        except (ValueError, TypeError, AttributeError) as e:
            self._log_processing_error(e, event, "Failed to process weather wire event")
        except Exception as e:  # noqa: BLE001 - Catch-all for unexpected errors
            self._log_processing_error(
                e,
                event,
                "Unexpected error processing weather wire event",
            )

    def _log_processing_error(
        self,
        error: Exception,
        event: WeatherWireMessage,
        message: str,
    ) -> None:
        """Log processing errors with consistent format."""
        event_id = event.id if hasattr(event, "id") else "unknown"
        subject = event.subject if hasattr(event, "subject") else "unknown"

        logger.error(
            message,
            error=str(error),
            error_type=type(error).__name__,
            product_id=event_id,
            subject=subject,
        )

    async def run(self) -> None:
        """Run the application event loop until shutdown.

        This method assumes services are already started (via context manager).
        """
        logger.info("Running NWWS-OI application event loop")
        await self._shutdown_event.wait()
        logger.info("Stopped NWWS-OI application event loop")

    async def __aenter__(self) -> "WeatherWireApp":
        """Async context manager entry.

        Returns:
            Self for use in async with statement

        """
        logger.info("Starting NWWS-OI application services")
        await self._start_services()
        logger.info("Started NWWS-OI application services")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit with cleanup.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred

        """
        logger.info("Application shutdown initiated, cleaning up services")
        await self._cleanup_services()
        logger.info("Cleaned up application services")

    async def _start_services(self) -> None:
        """Start all application services in the correct order.

        Starts the pipeline first, then the weather wire receiver.
        """
        # Start pipeline first
        await self.pipeline.start()

        # Start weather wire receiver
        self.receiver.start()

    def _signal_handler(self, signum: int, _frame: FrameType | None) -> None:
        """Handle shutdown signals gracefully.

        Args:
            signum: Signal number received
            _frame: Frame object (unused)

        """
        logger.info(
            "Received shutdown signal, initiating graceful shutdown",
            signal=signum,
        )
        self.shutdown()

    def shutdown(self) -> None:
        """Gracefully shutdown the application.

        Sets the shutdown flag and triggers the shutdown event to stop the main loop.
        """
        if self.is_shutting_down:
            return

        logger.info("Shutting down NWWS-OI application")
        self.is_shutting_down = True
        self._shutdown_event.set()

    async def _cleanup_services(self) -> None:
        """Stop all application services."""
        await asyncio.gather(
            self.receiver.stop(),
            self.pipeline.stop(),
        )

    def get_comprehensive_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics including pipeline and receiver metrics."""
        pipeline_stats = self.pipeline.get_stats_summary()

        # Add application-level metrics
        uptime_seconds = time.time() - self._start_time

        return {
            "application": {
                "uptime_seconds": uptime_seconds,
                "is_running": not self.is_shutting_down,
                "receiver_connected": self.receiver.is_client_connected(),
                "pipeline_started": self.pipeline.is_started,
            },
            "pipeline": pipeline_stats,
            "summary": {
                "total_messages_received": self.stats.get_counter(
                    "weather-wire.messages.received",
                ),
                "total_delayed_messages": self.stats.get_counter(
                    "weather-wire.messages.delayed",
                ),
                "total_connection_attempts": self.stats.get_counter(
                    "weather-wire.connection.attempts",
                ),
                "total_connection_failures": self.stats.get_counter(
                    "weather-wire.connection.failures",
                ),
                "total_pipeline_processed": self.stats.get_counter(
                    "weather-wire-pipeline.processed",
                ),
                "last_message_age_seconds": self.stats.get_gauge(
                    "weather-wire.last_message_age_seconds",
                ),
                "connection_status": self.stats.get_gauge(
                    "weather-wire.connection.status",
                ),
            },
        }


async def main() -> None:
    """Start the application.

    Loads configuration from environment and starts the WeatherWire application.
    Handles configuration errors and unexpected runtime errors gracefully.
    """
    try:
        config = Config.from_env()
        async with WeatherWireApp(config) as app:
            await app.run()

    except ValueError as e:
        logger.error("Configuration error", error=str(e))
        sys.exit(1)
    except (TimeoutError, OSError, ConnectionError, RuntimeError, CancelledError) as e:
        logger.error("Unexpected error", error=str(e))
        sys.exit(1)
    finally:
        logger.info("NWWS-OI application stopped")


if __name__ == "__main__":
    asyncio.run(main())
