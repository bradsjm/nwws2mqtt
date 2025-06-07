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
        """Initialize the Weather Wire application with configuration.

        The application is configured with a weather wire receiver and a processing
        pipeline consisting of filters, transformers, and outputs. The application also
        sets up signal handlers for graceful shutdown and initializes a web server with
        dashboard capabilities.

        Args:
            config: The application configuration.

        """
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
        """Initialize the Weather Wire receiver with configuration.

        The receiver is configured with a weather wire client and a stats collector for
        monitoring receiver metrics. The receiver is initialized with the provided XMPP
        configuration and is ready to connect to the NWWS-OI service.

        """
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
        # Create pipeline builder and register application-specific outputs
        """Set up the processing pipeline with filters, transformers, and outputs.

        This function initializes a PipelineBuilder and registers application-specific
        filters, transformers, and outputs at runtime. It creates a pipeline configuration
        using the registered components, including a stats collector for monitoring and
        an error handling strategy. The pipeline is built using the configuration and
        is ready for processing events.

        """
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
        """Parse configured outputs from environment and return a list of OutputConfig objects.

        The configured outputs are parsed from the environment variable `OUTPUTS` and
        converted to a list of OutputConfig objects. The `OUTPUTS` variable is a comma-separated
        list of output names, which are used to create the OutputConfig objects.

        Returns:
            list[OutputConfig]: A list of OutputConfig objects, each representing an output handler.

        """
        output_names = [name.strip().lower() for name in self.config.outputs.split(",")]
        return [
            OutputConfig(
                output_type=output_name,
                output_id=output_name,
            )
            for output_name in output_names
        ]

    async def _start_services(self) -> None:
        """Start all application services concurrently using TaskGroup.

        This function initializes and starts the pipeline, weather wire receiver,
        and optionally the web server based on the provided configuration. Services
        are started concurrently using asyncio.TaskGroup for better performance and
        structured concurrency. If any service fails to start, all services are
        automatically cancelled.
        """
        async with asyncio.TaskGroup() as tg:
            # Start pipeline first - pipeline.start() is async
            tg.create_task(self.pipeline.start())

            # Start weather wire receiver - receiver.start() is now async
            tg.create_task(self.receiver.start())

            # Start web server if enabled - web_server.start() is async
            if self.config.metric_server:
                tg.create_task(
                    self.web_server.start(
                        host=self.config.metric_host,
                        port=self.config.metric_port,
                        log_level=self.config.log_level,
                    )
                )

    async def _cleanup_services(self) -> None:
        """Stop all application services concurrently using TaskGroup.

        This function stops the weather wire receiver, pipeline, and optionally the web
        server concurrently using asyncio.TaskGroup for faster shutdown. Individual
        service errors are logged but don't prevent other services from stopping.
        """
        from collections.abc import Awaitable

        shutdown_tasks: list[tuple[str, Awaitable[None]]] = []

        # Create shutdown tasks for active services
        shutdown_tasks.append(("receiver", self.receiver.stop()))
        shutdown_tasks.append(("pipeline", self.pipeline.stop()))

        if self.config.metric_server:
            shutdown_tasks.append(("web_server", self.web_server.stop()))

        # Execute all shutdown tasks concurrently with individual error handling
        async def _shutdown_service(service_name: str, shutdown_coro: Awaitable[None]) -> None:
            try:
                await shutdown_coro
                logger.debug("%s stopped successfully", service_name.replace("_", " ").title())
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "Error stopping %s",
                    service_name.replace("_", " "),
                    error=str(e),
                    error_type=type(e).__name__,
                )

        # Use TaskGroup for structured concurrency with individual error handling
        try:
            async with asyncio.TaskGroup() as tg:
                for service_name, shutdown_coro in shutdown_tasks:
                    tg.create_task(_shutdown_service(service_name, shutdown_coro))
        except* Exception as eg:  # noqa: BLE001
            # Log exception group but don't re-raise to prevent masking shutdown issues
            logger.warning(
                "Some services encountered errors during shutdown: %d errors", len(eg.exceptions)
            )

    async def _handle_weather_wire_message(self, weather_message: WeatherWireMessage) -> None:
        """Handle a single WeatherWireMessage.

        Convert the message to an enhanced event by creating an enhanced pipeline event with
        rich metadata context and processing it through the pipeline with circuit breaker
        error handling.

        The enhanced event includes the following metadata:
        - `awipsid`: The AWIPS ID of the message
        - `cccc`: The CCCC code of the message
        - `id`: The message ID
        - `issue`: The issue timestamp of the message
        - `noaaport`: The NOAAPORT content of the message
        - `subject`: The subject of the message
        - `ttaaii`: The TTAAII code of the message
        - `delay_stamp`: The delay stamp of the message
        - `content_type`: The content type of the message
        - `metadata`: A dictionary containing additional metadata:
            - `original_source`: The source of the message (weather_wire)
            - `message_size_bytes`: The size of the message in bytes
            - `has_delay_stamp`: A boolean indicating whether the message has a delay stamp
            - `ingest_timestamp`: The timestamp when the message was ingested

        The function logs any errors encountered during processing and does not crash.
        """
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
        """Async context manager entry point to start application services.

        This method is called when entering the async context. It initializes
        and starts the necessary services for the NWWS-OI application and
        logs the start process. It returns the instance of the application
        for further use in the context.

        Returns:
            WeatherWireApp: The current instance for use within the async context.

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
        """Exit the async context manager and perform cleanup.

        This method is called when exiting the async context. It logs the
        initiation of the application shutdown process and attempts to clean
        up application services. If an error occurs during the cleanup,
        it logs the error without re-raising it, ensuring that the original
        exception, if any, is not masked.

        Args:
            exc_type: The exception type, if an exception was raised.
            exc_val: The exception instance, if an exception was raised.
            exc_tb: The traceback object, if an exception was raised.

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
        """Handle shutdown signals (SIGINT, SIGTERM) gracefully.

        This function is the signal handler for the SIGINT and SIGTERM signals.
        When either of these signals is received, it logs a message indicating
        that a shutdown signal was received and initiates a graceful shutdown
        of the NWWS-OI application by calling the shutdown() method.

        Args:
            signum: The signal number received (SIGINT or SIGTERM).
            _frame: The current stack frame (not used).

        """
        logger.info(
            "Received shutdown signal, initiating graceful shutdown",
            signal=signum,
        )
        self.shutdown()

    def _validate_config(self, config: Config) -> None:
        """Validate the provided configuration.

        This method validates the provided configuration object by checking that
        required fields are present and have valid values. If any of the required
        fields are missing or have invalid values, a ValueError is raised.

        :param config: The configuration object to validate.
        :raises ValueError: If any of the required fields are invalid.
        """
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
        """Run the NWWS-OI application event loop.

        This method is the main entry point of the NWWS-OI application. It
        initializes the application services, logs the application start
        process, and starts the event loop to process NWWS-OI messages. The
        event loop is responsible for consuming messages from the weather wire
        receiver, processing them through the configured pipeline, and sending
        the processed messages to the configured outputs.

        The method logs the application start process, including the pipeline
        ID, uptime, number of filters, presence of a transformer, and number of
        outputs. It also logs the queue size periodically for monitoring
        purposes.

        If an error occurs during the processing of a message, it logs the
        error and continues processing the next message. If the application is
        cancelled (e.g., due to a shutdown signal), it logs the cancellation
        and raises an asyncio.CancelledError. If any other unexpected error
        occurs, it logs the error and raises it.

        Finally, it logs the application stop process, including the uptime.

        :raises asyncio.CancelledError: If the application is cancelled.
        :raises Exception: If any other unexpected error occurs.
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
                if self._shutdown_event.is_set():
                    logger.info("Shutdown event detected, exiting main loop")
                    break
                try:
                    await self._handle_weather_wire_message(weather_message)

                    # Log queue size for monitoring
                    queue_size = self.receiver.queue_size
                    if queue_size > 10:  # Log when queue starts building up
                        logger.warning("Message queue building up: %d messages pending", queue_size)
                    elif queue_size > 0:
                        logger.debug("Queue size: %d messages", queue_size)

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
            logger.error("Unexpected error in main loop: %s", str(e))
            raise

        logger.info(
            "NWWS-OI application event loop stopped",
            uptime_seconds=time.time() - self._start_time,
        )

    def shutdown(self) -> None:
        """Initiate the shutdown process for the NWWS-OI application.

        This method sets the shutdown flag and triggers the shutdown event,
        indicating that the application is in the process of shutting down.
        If the application is already shutting down, the method returns
        immediately without performing any actions.

        The method logs the initiation of the shutdown process and ensures
        that the shutdown event is set to unblock any waiting coroutines.
        """
        if self.is_shutting_down:
            return

        logger.info("Shutting down NWWS-OI application")
        self.is_shutting_down = True
        self._shutdown_event.set()


async def main() -> None:
    """Run the main entry point of the NWWS-OI application.

    This function initializes the logging system, reads the configuration from
    the environment, and starts the NWWS-OI application using the provided
    configuration. It logs the application start process, including the
    configuration used, and sets up error handling to catch any configuration
    errors, keyboard interrupts, and runtime errors.

    If a configuration error occurs, it logs the error and sets the exit code to
    1. If a keyboard interrupt occurs, it logs the interrupt and sets the exit
    code to 0. If a runtime error occurs, it logs the error and sets the exit
    code to 1.

    Finally, it logs the application shutdown process and exits the process with
    the set exit code.
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
