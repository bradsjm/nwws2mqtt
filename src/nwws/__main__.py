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

from nwws.filters.duplicate_filter import DuplicateFilter
from nwws.filters.test_msg_filter import TestMessageFilter
from nwws.metrics import MetricRegistry
from nwws.metrics.api_server import MetricApiServer
from nwws.models import Config
from nwws.models.events import NoaaPortEventData
from nwws.outputs.console import ConsoleOutput
from nwws.outputs.mqtt import MQTTOutput
from nwws.pipeline.config import PipelineBuilder, PipelineConfig
from nwws.pipeline.errors import ErrorHandlingStrategy
from nwws.pipeline.filters import FilterConfig
from nwws.pipeline.outputs import OutputConfig
from nwws.pipeline.stats import PipelineStatsCollector
from nwws.pipeline.transformers import TransformerConfig
from nwws.pipeline.types import PipelineEventMetadata, PipelineStage
from nwws.receiver import WeatherWire, WeatherWireConfig, WeatherWireMessage
from nwws.receiver.stats import WeatherWireStatsCollector
from nwws.transformers import NoaaPortTransformer, XmlTransformer
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

        logger.info("Weather Wire receiver initialized")

    def _setup_pipeline(self) -> None:
        """Configure and initialize the pipeline system."""
        # Create pipeline builder and register application-specific outputs
        builder = PipelineBuilder()

        # Register application-specific filters at runtime
        builder.filter_registry.register("duplicate", self._create_duplicate_filter)
        builder.filter_registry.register("test_msg", self._create_test_msg_filter)

        # Register application-specific transformers at runtime
        builder.transformer_registry.register(
            "noaaport", self._create_noaaport_transformer
        )
        builder.transformer_registry.register("xml", self._create_xml_transformer)

        # Register console and mqtt outputs at runtime
        builder.output_registry.register("console", self._create_console_output)
        builder.output_registry.register("mqtt", self._create_mqtt_output)

        # Parse configured outputs from environment
        output_configs = self._create_output_configs()

        # Initialize pipeline stats collector
        self.pipeline_stats_collector = PipelineStatsCollector(
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
            stats_collector=self.pipeline_stats_collector,
            enable_error_handling=True,
            error_handling_strategy=ErrorHandlingStrategy.CIRCUIT_BREAKER,
        )

        # Build pipeline using configuration
        self.pipeline = builder.build_pipeline(pipeline_config)

        # Store stats collector for metrics
        self.pipeline_stats_collector = self.pipeline.stats_collector

        logger.info("Pipeline configured", pipeline_id=self.pipeline.pipeline_id)

    def _create_output_configs(self) -> list[OutputConfig]:
        """Create output configurations based on environment settings."""
        output_configs: list[OutputConfig] = []
        output_names = [name.strip().lower() for name in self.config.outputs.split(",")]

        for output_name in output_names:
            if output_name == "console":
                output_configs.append(
                    OutputConfig(
                        output_type="console",
                        output_id="console",
                        config={"pretty": True},
                    )
                )
            elif output_name == "mqtt":
                if self.config.mqtt_config:
                    output_configs.append(
                        OutputConfig(
                            output_type="mqtt",
                            output_id="mqtt",
                            config={"config": self.config.mqtt_config},
                        )
                    )
                else:
                    logger.warning("MQTT output requested but no MQTT config provided")
            else:
                logger.warning("Unknown output type", output_type=output_name)

        return output_configs

    def _create_mqtt_output(self, output_id: str, **kwargs: object) -> MQTTOutput:
        """Create MQTT output instances."""
        from nwws.models.mqtt_config import MqttConfig

        config = kwargs.get("config")
        if not isinstance(config, MqttConfig):
            error_msg = "MQTT output requires valid MqttConfig"
            raise TypeError(error_msg)
        return MQTTOutput(output_id=output_id, config=config)

    def _create_duplicate_filter(
        self, filter_id: str, **_kwargs: object
    ) -> DuplicateFilter:
        """Create duplicate filter instances."""
        return DuplicateFilter(filter_id=filter_id)

    def _create_test_msg_filter(
        self, filter_id: str, **_kwargs: object
    ) -> TestMessageFilter:
        """Create test message filter instances."""
        return TestMessageFilter(filter_id=filter_id)

    def _create_noaaport_transformer(
        self, transformer_id: str, **_kwargs: object
    ) -> NoaaPortTransformer:
        """Create NOAA Port transformer instances."""
        return NoaaPortTransformer(transformer_id=transformer_id)

    def _create_xml_transformer(
        self, transformer_id: str, **_kwargs: object
    ) -> XmlTransformer:
        """Create XML transformer instances."""
        return XmlTransformer(transformer_id=transformer_id)

    def _create_console_output(self, output_id: str, **kwargs: object) -> ConsoleOutput:
        """Create console output instances."""
        pretty = kwargs.get("pretty", True)
        return ConsoleOutput(output_id=output_id, pretty=bool(pretty))

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
            # Create enhanced initial metadata with rich context
            pipeline_event = NoaaPortEventData(
                awipsid=event.awipsid,
                cccc=event.cccc,
                id=event.id,
                issue=event.issue,
                noaaport=event.noaaport,
                subject=event.subject,
                ttaaii=event.ttaaii,
                delay_stamp=event.delay_stamp,
                content_type="application/octet-stream",
                metadata=PipelineEventMetadata(
                    source="weather-wire-receiver",
                    stage=PipelineStage.INGEST,
                    trace_id=f"wr-{event.id}-{int(time.time())}",
                    custom={
                        "original_source": "weather_wire",
                        "message_size_bytes": len(event.noaaport),
                        "has_delay_stamp": event.delay_stamp is not None,
                        "ingest_timestamp": time.time(),
                        "awipsid": event.awipsid,
                        "cccc": event.cccc,
                        "ttaaii": event.ttaaii,
                        "subject": event.subject,
                    },
                ),
            )

            await self.pipeline.process(pipeline_event)

            # Enhanced logging with metadata context
            logger.info(
                "Weather wire message ingested to pipeline",
                event_id=pipeline_event.metadata.event_id,
                trace_id=pipeline_event.metadata.trace_id,
                product_id=pipeline_event.id,
                subject=pipeline_event.subject,
                awipsid=pipeline_event.awipsid,
                cccc=pipeline_event.cccc,
                message_size_bytes=len(event.noaaport),
                has_delay_stamp=event.delay_stamp is not None,
                content_type=pipeline_event.content_type,
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
        logger.info(
            "Running NWWS-OI application event loop",
            pipeline_id=self.pipeline.pipeline_id,
            uptime_seconds=time.time() - self._start_time,
            filters_count=len(self.pipeline.filters),
            has_transformer=self.pipeline.transformer is not None,
            outputs_count=len(self.pipeline.outputs),
        )
        await self._shutdown_event.wait()

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
        sys.exit(1)
    except (TimeoutError, OSError, ConnectionError, RuntimeError, CancelledError) as e:
        logger.error(
            "Runtime error - application failed",
            error=str(e),
            error_type=type(e).__name__,
            stage="runtime",
        )
        sys.exit(1)
    finally:
        logger.info("NWWS-OI application shutdown completed")


if __name__ == "__main__":
    asyncio.run(main())
