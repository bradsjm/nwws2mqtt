"""NWWS2MQTT - National Weather Service NWWS-OI to MQTT Bridge."""

import asyncio
import signal
import sys
import time
from collections.abc import Callable
from pathlib import Path
from types import FrameType, TracebackType
from typing import Any

from dotenv import load_dotenv
from loguru import logger

from nwws.filters import DuplicateFilter, TestMessageFilter
from nwws.metrics import MetricRegistry
from nwws.models import Config
from nwws.models.events import NoaaPortEventData
from nwws.outputs import ConsoleOutput, DatabaseOutput, MQTTOutput
from nwws.pipeline import (
    ErrorHandlingStrategy,
    FilterConfig,
    OutputConfig,
    PipelineBuilder,
    PipelineConfig,
    PipelineEventMetadata,
    PipelineStage,
    PipelineStatsCollector,
    TransformerConfig,
)
from nwws.pipeline.errors import PipelineError, PipelineErrorHandler
from nwws.receiver import (
    WeatherWire,
    WeatherWireConfig,
    WeatherWireMessage,
    WeatherWireStatsCollector,
)
from nwws.transformers import NoaaPortTransformer, XmlTransformer
from nwws.utils import LoggingConfig, WeatherGeoDataProvider
from nwws.webserver import WebServer

# Load environment variables from .env file
load_dotenv(override=True)

# Type alias for signal handlers
type SignalHandler = Callable[[int, FrameType | None], None]

# Type alias for output configuration factories
type OutputConfigFactory = Callable[[], dict[str, Any] | None]


class WeatherWireApp:
    """NWWS Weather Wire Application."""

    def __init__(self, config: Config) -> None:
        """Initialize the application with configuration."""
        self._validate_config(config)
        self.config = config
        self.is_shutting_down = False
        self._shutdown_event = asyncio.Event()
        self._start_time = time.time()

        self.message_error_handler = PipelineErrorHandler(
            strategy=ErrorHandlingStrategy.CIRCUIT_BREAKER,
            circuit_breaker_threshold=10,  # Open after 10 consecutive failures
        )

        # Setup enhanced logging
        LoggingConfig.configure(config.log_level, config.log_file)

        # Initialize metric registry for application metrics
        self.metric_registry = MetricRegistry()

        # Initialize web server with dashboard capabilities
        self.web_server = WebServer(
            registry=self.metric_registry,
            geo_provider=WeatherGeoDataProvider(),
            templates_dir=str(Path(__file__).parent / "webserver" / "dashboard" / "templates"),
            static_dir=str(Path(__file__).parent / "webserver" / "dashboard" / "static"),
        )

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
            stats_collector=self.receiver_stats_collector,
        )

        logger.info("Weather Wire receiver initialized")

    def _setup_pipeline(self) -> None:
        """Configure and initialize the pipeline system."""
        # Create pipeline builder and register application-specific outputs
        builder = PipelineBuilder()

        # Register application-specific filters at runtime
        builder.filter_registry.register(filter_type="duplicate", factory=DuplicateFilter)
        builder.filter_registry.register(filter_type="test_msg", factory=TestMessageFilter)

        # Register application-specific transformers at runtime
        builder.transformer_registry.register(
            transformer_type="noaaport",
            factory=NoaaPortTransformer,
        )
        builder.transformer_registry.register(
            transformer_type="xml",
            factory=XmlTransformer,
        )

        # Register application-specific outputs at runtime
        builder.output_registry.register(
            output_type="console",
            factory=ConsoleOutput,
        )
        builder.output_registry.register(
            "mqtt",
            factory=MQTTOutput,
        )
        builder.output_registry.register(
            "database",
            factory=DatabaseOutput,
        )

        # Parse configured outputs from environment
        output_configs = self._create_output_configs()

        # Initialize pipeline stats collector
        pipeline_stats_collector = PipelineStatsCollector(
            self.metric_registry,
            "pipeline",
        )

        # Create pipeline configuration
        pipeline_config = PipelineConfig(
            pipeline_id="pipeline",
            filters=[
                FilterConfig(
                    filter_type="duplicate",
                    filter_id="duplicate-filter",
                ),
                FilterConfig(
                    filter_type="test_msg",
                    filter_id="test-msg-filter",
                ),
            ],
            transformer=TransformerConfig(
                transformer_type="chain",
                transformer_id="chain",
                config={
                    "transformers": [
                        {"transformer_type": "noaaport", "transformer_id": "noaaport"},
                        {"transformer_type": "xml", "transformer_id": "xml"},
                    ]
                },
            ),
            outputs=output_configs,
            stats_collector=pipeline_stats_collector,
            enable_error_handling=True,
            error_handling_strategy=ErrorHandlingStrategy.CIRCUIT_BREAKER,
        )

        # Build pipeline using configuration
        self.pipeline = builder.build_pipeline(pipeline_config)

        logger.info("Pipeline configured", pipeline_id=self.pipeline.pipeline_id)

    def _create_output_configs(self) -> list[OutputConfig]:
        """Create output configurations based on environment settings."""
        output_names = [name.strip().lower() for name in self.config.outputs.split(",")]
        return [
            OutputConfig(
                output_type=output_name,
                output_id=output_name,
            )
            for output_name in output_names
        ]

    async def _start_services(self) -> None:
        """Start all application services in the correct order."""
        # Start pipeline first
        await self.pipeline.start()

        # Start weather wire receiver
        await self.receiver.start()

        # Start web server if enabled
        if self.config.metric_server:
            await self.web_server.start(
                host=self.config.metric_host,
                port=self.config.metric_port,
                log_level=self.config.log_level,
            )

    async def _cleanup_services(self) -> None:
        """Stop all application services individually to handle errors gracefully."""
        # Stop receiver first
        try:
            await self.receiver.stop()
            logger.debug("Weather wire receiver stopped successfully")
        except Exception as e:  # noqa: BLE001
            logger.error(
                "Error stopping weather wire receiver",
                error=str(e),
                error_type=type(e).__name__,
            )

        # Stop pipeline
        try:
            await self.pipeline.stop()
            logger.debug("Pipeline stopped successfully")
        except Exception as e:  # noqa: BLE001
            logger.error(
                "Error stopping pipeline",
                error=str(e),
                error_type=type(e).__name__,
            )

        # Stop web server if enabled
        if self.config.metric_server:
            try:
                await self.web_server.stop()
                logger.debug("Web server stopped successfully")
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "Error stopping web server",
                    error=str(e),
                    error_type=type(e).__name__,
                )

    async def _handle_weather_wire_message(self, weather_message: WeatherWireMessage) -> None:
        """Handle Weather Wire content by feeding to the pipeline."""
        try:
            # Create enhanced initial metadata with rich context
            pipeline_event = NoaaPortEventData(
                awipsid=weather_message.awipsid,
                cccc=weather_message.cccc,
                id=weather_message.id,
                issue=weather_message.issue,
                noaaport=weather_message.noaaport,
                subject=weather_message.subject,
                ttaaii=weather_message.ttaaii,
                delay_stamp=weather_message.delay_stamp,
                content_type="application/octet-stream",
                metadata=PipelineEventMetadata(
                    source="weather-wire-receiver",
                    stage=PipelineStage.INGEST,
                    trace_id=f"wr-{weather_message.id}-{int(time.time())}",
                    custom={
                        "original_source": "weather_wire",
                        "message_size_bytes": len(weather_message.noaaport),
                        "has_delay_stamp": weather_message.delay_stamp is not None,
                        "ingest_timestamp": time.time(),
                        "awipsid": weather_message.awipsid,
                        "cccc": weather_message.cccc,
                        "ttaaii": weather_message.ttaaii,
                        "subject": weather_message.subject,
                    },
                ),
            )

            # Process the event through the pipeline with circuit breaker error handling
            await self.message_error_handler.execute_with_retry(
                stage=PipelineStage.INGEST,
                stage_id="runtime",
                event=pipeline_event,
                operation=self.pipeline.process,
            )

            # Enhanced logging with metadata context
            logger.info(
                "Weather wire message ingested to pipeline",
                event_id=pipeline_event.metadata.event_id,
                trace_id=pipeline_event.metadata.trace_id,
                product_id=pipeline_event.id,
                subject=pipeline_event.subject,
                awipsid=pipeline_event.awipsid,
                cccc=pipeline_event.cccc,
                message_size_bytes=len(weather_message.noaaport),
                has_delay_stamp=weather_message.delay_stamp is not None,
                content_type=pipeline_event.content_type,
            )

        except PipelineError as e:
            # Log pipeline-specific errors but don't crash
            self._log_processing_error(e, weather_message, "Pipeline processing failed")
        except (ValueError, TypeError, AttributeError) as e:
            # Data validation errors - log and continue
            self._log_processing_error(e, weather_message, "Message validation failed")
        except (ConnectionError, OSError) as e:
            # Infrastructure errors
            self._log_processing_error(
                e, weather_message, "Infrastructure error processing message"
            )
        except Exception as e:  # noqa: BLE001
            # Log unexpected errors
            self._log_processing_error(e, weather_message, "Unexpected error processing message")

    def _log_processing_error(
        self,
        error: Exception,
        event: WeatherWireMessage,
        message: str,
    ) -> None:
        """Log processing errors with enhanced context and metadata."""
        event_id = event.id if hasattr(event, "id") else "unknown"
        subject = event.subject if hasattr(event, "subject") else "unknown"
        awipsid = event.awipsid if hasattr(event, "awipsid") else "unknown"
        cccc = event.cccc if hasattr(event, "cccc") else "unknown"

        # Enhanced error logging with additional context
        error_context = {
            "error": str(error),
            "error_type": type(error).__name__,
            "product_id": event_id,
            "subject": subject,
            "awipsid": awipsid,
            "cccc": cccc,
            "processing_stage": "ingestion",
            "source": "weather-wire-receiver",
        }

        logger.error(message, **error_context)

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
        try:
            await self._cleanup_services()
            logger.info("Cleaned up application services")
        except Exception as cleanup_error:  # noqa: BLE001
            logger.error(
                "Error during service cleanup",
                error=str(cleanup_error),
                error_type=type(cleanup_error).__name__,
            )
            # Don't re-raise cleanup errors to avoid masking original exception

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
            port_error = f"Invalid port number: {config.nwws_port}. Must be between 1 and 65535"
            raise ValueError(port_error)

        # Validate metrics server configuration
        if config.metric_server and (config.metric_port <= 0 or config.metric_port > 65535):
            metrics_port_error = (
                f"Invalid metrics port: {config.metric_port}. Must be between 1 and 65535"
            )
            raise ValueError(metrics_port_error)

    async def run(self) -> None:
        """Run the application event loop until shutdown.

        This method assumes services are already started (via context manager).
        """
        logger.info(
            "Running NWWS-OI application event loop",
            pipeline_id=self.pipeline.pipeline_id,
            uptime_seconds=time.time() - self._start_time,
            filters_count=len(self.pipeline.filters),
            has_transformer=self.pipeline.transformer is not None,
            outputs_count=len(self.pipeline.outputs),
        )

        try:
            # Use async iterator to process messages
            async for weather_message in self.receiver:
                try:
                    await self._handle_weather_wire_message(weather_message)

                    # Log queue size for monitoring
                    queue_size = self.receiver.queue_size
                    if queue_size > 10:  # Log when queue starts building up
                        logger.warning(f"Message queue building up: {queue_size} messages pending")
                    elif queue_size > 0:
                        logger.debug(f"Queue size: {queue_size} messages")

                except (
                    PipelineError,
                    ValueError,
                    TypeError,
                    AttributeError,
                    ConnectionError,
                    OSError,
                ) as e:
                    self._log_processing_error(
                        e, weather_message, "Error processing weather message"
                    )
                except Exception as e:  # noqa: BLE001
                    self._log_processing_error(
                        e, weather_message, "Unexpected error processing weather message"
                    )
        except asyncio.CancelledError:
            logger.info("Application cancelled")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            raise

        logger.info(
            "NWWS-OI application event loop stopped",
            uptime_seconds=time.time() - self._start_time,
        )

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
    exit_code = 0

    try:
        config = Config.from_env()
        logger.info(
            "Starting NWWS-OI application with configuration",
            nwws_server=config.nwws_server,
            nwws_port=config.nwws_port,
            outputs=config.outputs,
            log_level=config.log_level,
            metric_server_enabled=config.metric_server,
        )

        async with WeatherWireApp(config) as app:
            await app.run()

    except ValueError as e:
        logger.error(
            "Configuration error - application startup failed",
            error=str(e),
            error_type=type(e).__name__,
            stage="startup",
        )
        exit_code = 1
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:  # noqa: BLE001
        logger.error(
            "Runtime error - application failed",
            error=str(e),
            error_type=type(e).__name__,
            stage="runtime",
        )
        exit_code = 1
    finally:
        logger.info("NWWS-OI application shutdown completed")
        if exit_code != 0:
            sys.exit(exit_code)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        logger.error(
            "Fatal error running application",
            error=str(e),
            error_type=type(e).__name__,
        )
        sys.exit(1)
