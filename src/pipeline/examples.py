# pyright: strict
"""Pipeline examples demonstrating integration with NWWS2MQTT application."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from loguru import logger

from messaging import MessageBus, WeatherWireEvent

from .config import PipelineBuilder, PipelineConfig, create_simple_pipeline
from .core import PipelineManager
from .filters import FilterConfig
from .outputs import OutputConfig
from .transformers import Transformer, TransformerConfig
from .types import PipelineEvent, PipelineEventMetadata, PipelineStage

if TYPE_CHECKING:
    from models.product import TextProductModel


@dataclass
class WeatherWirePipelineEvent(PipelineEvent):
    """Pipeline event for WeatherWire data."""

    subject: str
    """Subject of the message, typically the product type or title."""

    noaaport: str
    """NOAAPort formatted text of the product message."""

    id: str
    """Unique identifier for the product."""

    issue: str
    """Issue time of the product in ISO 8601 format."""

    ttaaii: str
    """TTAAII code representing the product type and time."""

    cccc: str
    """CCCC code representing the issuing office or center."""

    awipsid: str
    """AWIPS ID of the product, if available; otherwise 'NONE'."""


@dataclass
class TextProductPipelineEvent(PipelineEvent):
    """Pipeline event for processed text products."""

    subject: str
    """Subject of the message, typically the product type or title."""

    product: TextProductModel
    """Body of the text product message."""

    id: str
    """Unique identifier for the product."""

    issue: str
    """Issue time of the product in ISO 8601 format."""

    ttaaii: str
    """TTAAII code representing the product type and time."""

    cccc: str
    """CCCC code representing the issuing office or center."""

    awipsid: str
    """AWIPS ID of the product, if available; otherwise 'NONE'."""


def create_weather_wire_event_from_message_bus(event: WeatherWireEvent) -> WeatherWirePipelineEvent:
    """Convert MessageBus WeatherWireEvent to Pipeline event."""
    metadata = PipelineEventMetadata(
        event_id=event.id,
        source="weatherwire",
        stage=PipelineStage.INGEST,
        custom={"message_bus_event": True},
    )

    return WeatherWirePipelineEvent(
        metadata=metadata,
        subject=event.subject,
        noaaport=event.noaaport,
        id=event.id,
        issue=event.issue,
        ttaaii=event.ttaaii,
        cccc=event.cccc,
        awipsid=event.awipsid,
    )


class WeatherWireToTextProductTransformer(Transformer):
    """Transformer that converts WeatherWire events to TextProduct events."""

    def __init__(self, transformer_id: str, noaaport_transformer: Any) -> None:
        """Initialize with NOAAPort transformer."""
        super().__init__(transformer_id)
        self.noaaport_transformer = noaaport_transformer

    def transform(self, event: PipelineEvent) -> PipelineEvent:
        """Transform WeatherWire event to TextProduct event."""
        if not isinstance(event, WeatherWirePipelineEvent):
            raise ValueError(f"Expected WeatherWirePipelineEvent, got {type(event)}")

        # Use existing NOAAPort transformer
        text_product = self.noaaport_transformer.transform(event.noaaport)

        # Update metadata
        new_metadata = PipelineEventMetadata(
            event_id=event.metadata.event_id,
            source=self.transformer_id,
            stage=PipelineStage.TRANSFORM,
            trace_id=event.metadata.trace_id,
            custom=event.metadata.custom.copy(),
        )

        return TextProductPipelineEvent(
            metadata=new_metadata,
            subject=event.subject,
            product=text_product,
            id=event.id,
            issue=event.issue,
            ttaaii=event.ttaaii,
            cccc=event.cccc,
            awipsid=event.awipsid,
        )


def create_basic_weather_pipeline() -> PipelineManager:
    """Create a basic weather data processing pipeline."""
    # Create simple pipeline with log output
    pipeline = create_simple_pipeline(
        pipeline_id="basic_weather",
        filter_configs=[
            {
                "type": "attribute",
                "id": "awips_filter",
                "config": {
                    "attribute_name": "awipsid",
                    "allowed_values": {"KOUN", "KTLX", "KFDR"},
                    "case_sensitive": False,
                },
            },
        ],
        output_configs=[
            {
                "type": "log",
                "id": "console_log",
                "config": {"log_level": "info"},
            },
        ],
    )

    manager = PipelineManager()
    manager.add_pipeline(pipeline)
    return manager


def create_advanced_weather_pipeline(message_bus: Any, noaaport_transformer: Any) -> PipelineManager:
    """Create an advanced weather data processing pipeline with filtering and transformation."""
    # Register custom transformer
    from .transformers import transformer_registry

    transformer_registry.register(
        "weatherwire_to_textproduct",
        lambda transformer_id, **_kwargs: WeatherWireToTextProductTransformer(
            transformer_id,
            noaaport_transformer,
        ),
    )

    # Create pipeline configuration
    config = PipelineConfig(
        pipeline_id="advanced_weather",
        filters=[
            # Filter by AWIPS ID
            FilterConfig(
                filter_type="attribute",
                filter_id="awips_filter",
                config={
                    "attribute_name": "awipsid",
                    "allowed_values": {"KOUN", "KTLX", "KFDR", "KWOU"},
                    "case_sensitive": False,
                },
            ),
            # Filter by product type using TTAAII
            FilterConfig(
                filter_type="regex",
                filter_id="product_type_filter",
                config={
                    "attribute_name": "ttaaii",
                    "pattern": r"^(NOUS|FOUS|WOUS)",
                    "match_mode": "search",
                },
            ),
        ],
        transformer=TransformerConfig(
            transformer_type="weatherwire_to_textproduct",
            transformer_id="noaaport_transformer",
            config={},
        ),
        outputs=[
            # Log output for debugging
            OutputConfig(
                output_type="log",
                output_id="debug_log",
                config={"log_level": "debug"},
            ),
            # Message bus output for downstream processing
            OutputConfig(
                output_type="messagebus",
                output_id="message_bus_out",
                config={
                    "message_bus": message_bus,
                    "event_type": "TextProductEvent",
                },
            ),
        ],
        enable_stats=True,
        enable_error_handling=True,
    )

    # Build pipeline
    builder = PipelineBuilder()
    pipeline = builder.build_pipeline(config)

    # Create manager and add pipeline
    manager = PipelineManager()
    manager.add_pipeline(pipeline)

    return manager


def create_multi_stage_pipeline(message_bus: Any) -> PipelineManager:
    """Create a multi-stage pipeline with different processing paths."""
    # High priority pipeline for urgent weather alerts
    urgent_config = PipelineConfig(
        pipeline_id="urgent_weather",
        filters=[
            FilterConfig(
                filter_type="regex",
                filter_id="urgent_filter",
                config={
                    "attribute_name": "subject",
                    "pattern": r"(TORNADO|WARNING|WATCH|EMERGENCY)",
                    "match_mode": "search",
                },
            ),
        ],
        outputs=[
            OutputConfig(
                output_type="log",
                output_id="urgent_log",
                config={"log_level": "warning"},
            ),
            OutputConfig(
                output_type="messagebus",
                output_id="urgent_bus",
                config={"message_bus": message_bus},
            ),
        ],
    )

    # Regular processing pipeline for routine weather data
    routine_config = PipelineConfig(
        pipeline_id="routine_weather",
        filters=[
            FilterConfig(
                filter_type="regex",
                filter_id="routine_filter",
                config={
                    "attribute_name": "subject",
                    "pattern": r"(TORNADO|WARNING|WATCH|EMERGENCY)",
                    "match_mode": "search",
                },
            ),
        ],
        outputs=[
            OutputConfig(
                output_type="log",
                output_id="routine_log",
                config={"log_level": "info"},
            ),
        ],
    )

    # Build pipelines
    builder = PipelineBuilder()
    urgent_pipeline = builder.build_pipeline(urgent_config)
    routine_pipeline = builder.build_pipeline(routine_config)

    # Create manager and add pipelines
    manager = PipelineManager()
    manager.add_pipeline(urgent_pipeline)
    manager.add_pipeline(routine_pipeline)

    return manager


class WeatherWirePipelineIntegration:
    """Integration class for connecting WeatherWire events to the pipeline system."""

    def __init__(self, pipeline_manager: PipelineManager) -> None:
        """Initialize the integration."""
        self.pipeline_manager = pipeline_manager

    async def start(self) -> None:
        """Start the pipeline integration."""
        # Start the pipeline manager
        await self.pipeline_manager.start()

        # Subscribe to WeatherWire events from the message bus
        MessageBus.subscribe(
            WeatherWireEvent,
            event_callback=self._handle_weather_wire_event,
            force_async=True,
        )

        logger.info("WeatherWire pipeline integration started")

    async def stop(self) -> None:
        """Stop the pipeline integration."""
        await self.pipeline_manager.stop()
        logger.info("WeatherWire pipeline integration stopped")

    async def _handle_weather_wire_event(self, event: WeatherWireEvent) -> None:
        """Handle incoming WeatherWire events."""
        try:
            # Convert to pipeline event
            pipeline_event = create_weather_wire_event_from_message_bus(event)

            # Submit to pipeline manager
            await self.pipeline_manager.submit_event(pipeline_event)

            logger.debug(
                "WeatherWire event submitted to pipeline",
                event_id=event.id,
                subject=event.subject,
                awipsid=event.awipsid,
            )

        except Exception as e:
            logger.error(
                "Error processing WeatherWire event in pipeline",
                event_id=event.id,
                error=str(e),
            )


async def example_usage() -> None:
    """Demonstrate example usage of the pipeline system."""
    logger.info("Starting pipeline example")

    # Create a basic pipeline
    manager = create_basic_weather_pipeline()

    # Start the manager
    await manager.start()

    try:
        # Create a sample event
        sample_event = WeatherWirePipelineEvent(
            metadata=PipelineEventMetadata(
                event_id=str(uuid.uuid4()),
                source="example",
                stage=PipelineStage.INGEST,
            ),
            subject="Test Weather Alert",
            noaaport="Sample NOAAPort data",
            id="TEST001",
            issue="2024-01-01T12:00:00Z",
            ttaaii="NOUS42",
            cccc="KOUN",
            awipsid="KOUN",
        )

        # Process the event
        await manager.submit_event(sample_event)

        # Wait a bit for processing
        await asyncio.sleep(1.0)

        # Get stats
        stats = manager.get_manager_stats()
        logger.info("Pipeline stats", stats=stats)

    finally:
        # Stop the manager
        await manager.stop()

    logger.info("Pipeline example completed")


if __name__ == "__main__":
    asyncio.run(example_usage())
