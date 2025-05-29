"""NWWS2MQTT - National Weather Service NWWS-OI to MQTT Bridge."""

import asyncio
import signal
import sys
import time
import uuid
from asyncio import CancelledError
from collections.abc import Callable
from dataclasses import dataclass
from types import FrameType

from dotenv import load_dotenv
from loguru import logger

from models import Config, XMPPConfig
from pipeline import PipelineBuilder, PipelineConfig, PipelineManager
from pipeline.types import PipelineEvent, PipelineEventMetadata, PipelineStage
from receiver import WeatherWire, WeatherWireEvent
from utils import LoggingConfig

# Load environment variables from .env file
load_dotenv(override=True)

# Type alias for signal handlers
type SignalHandler = Callable[[int, FrameType | None], None]


@dataclass
class WeatherWireEventData(PipelineEvent):
    """Pipeline event wrapper for WeatherWire events."""

    weather_event: WeatherWireEvent
    """The original weather wire event."""


class WeatherWireApp:
    """NWWS Weather Wire Application.

    Supports async context manager for automatic resource management.
    """

    def __init__(self, config: Config) -> None:
        """Initialize the application with configuration.

        Args:
            config: Application configuration object

        Raises:
            ValueError: If configuration is invalid

        """
        self._validate_config(config)
        self.config = config
        self.is_shutting_down = False
        self._shutdown_event = asyncio.Event()

        # Setup enhanced logging
        LoggingConfig.configure(config.log_level, config.log_file)

        # Setup signal handlers for graceful shutdown
        signal_handler: SignalHandler = self._signal_handler
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Create pipeline manager and initialize it
        self.pipeline_manager = PipelineManager()
        self._setup_pipeline()

        # Create XMPP client
        xmpp_config = XMPPConfig(
            username=config.username,
            password=config.password,
            server=config.server,
            port=config.port,
        )

        # Create the Weather Wire receiver
        self.receiver = WeatherWire(config=xmpp_config, callback=self._receive_weather_wire_event)

    def _validate_config(self, config: Config) -> None:
        """Validate critical configuration parameters.

        Args:
            config: Configuration object to validate

        Raises:
            ValueError: If configuration is invalid

        """
        if not config.username or not config.password:
            credentials_error = "XMPP credentials (username and password) are required"
            raise ValueError(credentials_error)
        if not config.server:
            server_error = "XMPP server is required"
            raise ValueError(server_error)
        if config.port <= 0 or config.port > 65535:
            port_error = f"Invalid port number: {config.port}. Must be between 1 and 65535"
            raise ValueError(port_error)

    def _setup_pipeline(self) -> None:
        """Configure and initialize the pipeline system.

        Creates an empty pipeline configuration and initializes the pipeline manager.
        """
        # Create an empty pipeline configuration
        pipeline_config = PipelineConfig(
            pipeline_id="weather-wire-pipeline",
            filters=[],  # No filters initially
            transformer=None,  # No transformer initially
            outputs=[],  # No outputs initially - empty pipeline
            enable_stats=True,
            enable_error_handling=True,
        )

        # Build the pipeline
        builder = PipelineBuilder()
        pipeline = builder.build_pipeline(pipeline_config)

        # Add the pipeline to the manager
        self.pipeline_manager.add_pipeline(pipeline)

        logger.info("Pipeline configured", pipeline_id=pipeline_config.pipeline_id)

    async def _receive_weather_wire_event(self, event: WeatherWireEvent) -> None:
        """Handle Weather Wire events by feeding them to the pipeline.

        Args:
            event: Weather wire event to process

        """
        try:
            pipeline_event = WeatherWireEventData(
                metadata=PipelineEventMetadata(
                    event_id=str(uuid.uuid4()),
                    timestamp=time.time(),
                    source="weather-wire-receiver",
                    stage=PipelineStage.INGEST,
                    trace_id=event.id,
                    custom={"product_id": event.id, "subject": event.subject},
                ),
                weather_event=event,
            )
            await self.pipeline_manager.submit_event(pipeline_event)
            logger.debug(
                "Weather wire event submitted to pipeline",
                event_id=pipeline_event.metadata.event_id,
                product_id=event.id,
                subject=event.subject,
            )
        except (ValueError, TypeError, AttributeError) as e:
            self._log_processing_error(e, event, "Failed to process weather wire event")
        except Exception as e:  # noqa: BLE001 - Catch-all for unexpected errors
            self._log_processing_error(e, event, "Unexpected error processing weather wire event")

    def _log_processing_error(self, error: Exception, event: WeatherWireEvent, message: str) -> None:
        """Log processing errors with consistent format.

        Args:
            error: Exception that occurred
            event: Weather wire event being processed
            message: Error message to log

        """
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

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
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

        Starts the pipeline manager first, then the weather wire receiver.
        """
        # Start pipeline manager first
        await self.pipeline_manager.start()

        # Start weather wire receiver
        self.receiver.start()

    def _signal_handler(self, signum: int, _frame: FrameType | None) -> None:
        """Handle shutdown signals gracefully.

        Args:
            signum: Signal number received
            _frame: Frame object (unused)

        """
        logger.info("Received shutdown signal, initiating graceful shutdown", signal=signum)
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
        """Stop all application services in reverse order.

        Stops the receiver first, then the pipeline manager to ensure
        proper cleanup and no data loss.
        """
        # Stop receiver first
        await self.receiver.stop()

        # Stop pipeline manager
        await self.pipeline_manager.stop()


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
