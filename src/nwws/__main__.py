"""NWWS2MQTT - National Weather Service NWWS-OI to MQTT Bridge."""

import asyncio
import signal
import sys
import time
from asyncio import CancelledError
from collections.abc import Callable
from types import FrameType, TracebackType

from dotenv import load_dotenv
from loguru import logger

from nwws.filters import TestMessageFilter
from nwws.metrics import MetricRegistry
from nwws.metrics.api_server import MetricApiServer
from nwws.models import Config
from nwws.models.events import NoaaPortEventData
from nwws.outputs.mqtt import mqtt_factory_create
from nwws.pipeline import Pipeline
from nwws.pipeline.errors import PipelineErrorHandler
from nwws.pipeline.stats import PipelineStatsCollector
from nwws.pipeline.types import PipelineEventMetadata, PipelineStage
from nwws.receiver import WeatherWire, WeatherWireConfig, WeatherWireMessage
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

        # Initialize metric registry for application metrics
        self.metric_registry = MetricRegistry()
        self.metric_api = MetricApiServer(self.metric_registry)

        # Setup signal handlers for graceful shutdown
        signal_handler: SignalHandler = self._signal_handler
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Create processing pipeline
        self._setup_pipeline()

        # Create Weather Wire receiver
        self._setup_receiver()

    def _setup_receiver(self) -> None:
        """Initialize the Weather Wire receiver with XMPP configuration."""
        xmpp_config = WeatherWireConfig(
            username=self.config.nwws_username,
            password=self.config.nwws_password,
            server=self.config.nwws_server,
            port=self.config.nwws_port,
        )

        # Create receiver stats collector
        self.receiver_stats_collector = WeatherWireStatsCollector(
            self.metric_registry,
            "weather_wire",
        )

        self.receiver = WeatherWire(
            config=xmpp_config,
            callback=self._handle_weather_wire_message,
            stats_collector=self.receiver_stats_collector,
        )

        logger.info("Weather Wire receiver initialized", xmpp_config=xmpp_config)

    def _setup_pipeline(self) -> None:
        """Configure and initialize the pipeline system."""
        # Create shared metric registry for both pipeline and receiver
        self.pipeline_stats_collector = PipelineStatsCollector(
            self.metric_registry, "pipeline"
        )
        error_handler = PipelineErrorHandler()
        self.pipeline: Pipeline = Pipeline(
            pipeline_id="pipeline",
            filters=[TestMessageFilter(filter_id="test-messages")],
            transformer=NoaaPortTransformer(transformer_id="noaaport"),
            outputs=[mqtt_factory_create(output_id="mqtt-server")],
            stats_collector=self.pipeline_stats_collector,
            error_handler=error_handler,
        )

        logger.info("Pipeline configured", pipeline_id=self.pipeline.pipeline_id)

    async def _start_services(self) -> None:
        """Start all application services in the correct order."""
        # Start pipeline first
        await self.pipeline.start()

        # Start weather wire receiver
        await self.receiver.start()

        # Start metrics API server if enabled
        await (
            self.metric_api.start_server(
                host=self.config.metric_host,
                port=self.config.metric_port,
                log_level=self.config.log_level,
            )
            if self.config.metric_server
            else asyncio.sleep(0)
        )

    async def _cleanup_services(self) -> None:
        """Stop all application services."""
        await asyncio.gather(
            self.receiver.stop(),
            self.pipeline.stop(),
            (
                self.metric_api.stop_server()
                if self.config.metric_server
                else asyncio.sleep(0)
            ),
        )

    async def _handle_weather_wire_message(self, event: WeatherWireMessage) -> None:
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

    def _validate_config(self, config: Config) -> None:
        """Validate critical configuration parameters."""
        if not config.nwws_username or not config.nwws_password:
            credentials_error = "XMPP credentials (username and password) are required"
            raise ValueError(credentials_error)
        if not config.nwws_server:
            server_error = "XMPP server is required"
            raise ValueError(server_error)
        if config.nwws_port <= 0 or config.nwws_port > 65535:
            port_error = (
                f"Invalid port number: {config.nwws_port}. Must be between 1 and 65535"
            )
            raise ValueError(port_error)

        # Validate metrics server configuration
        if config.metric_server and (
            config.metric_port <= 0 or config.metric_port > 65535
        ):
            metrics_port_error = (
                f"Invalid metrics port: {config.metric_port}. "
                f"Must be between 1 and 65535"
            )
            raise ValueError(metrics_port_error)

    async def run(self) -> None:
        """Run the application event loop until shutdown.

        This method assumes services are already started (via context manager).
        """
        logger.info("Running NWWS-OI application event loop")
        await self._shutdown_event.wait()
        logger.info("Stopped NWWS-OI application event loop")

    def shutdown(self) -> None:
        """Gracefully shutdown the application.

        Sets the shutdown flag and triggers the shutdown event to stop the main loop.
        """
        if self.is_shutting_down:
            return

        logger.info("Shutting down NWWS-OI application")
        self.is_shutting_down = True
        self._shutdown_event.set()


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
