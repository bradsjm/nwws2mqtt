# pyright: strict
"""Transforms NoaaPort raw text to product."""

from typing import Any

from loguru import logger
from pyiem.exceptions import TextProductException, UGCParseException
from pyiem.nws.products import parser  # type: ignore[import]
from pyiem.nws.ugc import UGCProvider

from nwws.models.events import NoaaPortEventData, TextProductEventData
from nwws.pipeline import (
    PipelineEvent,
    Transformer,
)
from nwws.utils import convert_text_product_to_model
from nwws.utils.ugc_loader import create_ugc_provider


class NoaaPortTransformer(Transformer):
    """Transforms NOAA Port text messages into structured products."""

    def __init__(self, transformer_id: str = "noaaport") -> None:
        """Initialize the transformer with UGC provider."""
        super().__init__(transformer_id)
        # Initialize UGC provider once during startup
        self._ugc_provider: UGCProvider = create_ugc_provider()

    @property
    def ugc_provider(self) -> UGCProvider:
        """Get the UGC provider."""
        return self._ugc_provider

    def transform(self, event: PipelineEvent) -> PipelineEvent:
        """Handle incoming NOAA Port event and convert to a product."""
        if not isinstance(event, NoaaPortEventData):
            logger.debug(
                "Event is not NoaaPortEventData, passing through",
                event_type=type(event).__name__,
            )
            return event

        try:
            product = convert_text_product_to_model(
                parser(text=event.noaaport, ugc_provider=self.ugc_provider),  # type: ignore[arg-type]
            )
        except (TextProductException, UGCParseException) as err:
            logger.error(
                "Failed to parse NOAA Port message",
                error=str(err),
                event_id=event.metadata.event_id,
                product_id=event.id,
                subject=event.subject,
            )
            return event

        logger.debug(
            "Transformed Raw Content to Text Product Model",
            event_id=event.metadata.event_id,
            product_id=event.id,
            subject=event.subject,
        )

        # Create new event using simplified helper method
        return self.create_transformed_event(
            source_event=event,
            target_event_class=TextProductEventData,
            awipsid=event.awipsid,
            cccc=event.cccc,
            id=event.id,
            issue=event.issue,
            product=product,
            subject=event.subject,
            ttaaii=event.ttaaii,
            delay_stamp=event.delay_stamp,
            noaaport=event.noaaport,
            content_type="application/json",
        )

    def get_transformation_metadata(
        self, input_event: PipelineEvent, output_event: PipelineEvent
    ) -> dict[str, Any]:
        """Get metadata about the NOAA Port transformation."""
        metadata = super().get_transformation_metadata(input_event, output_event)

        # Add NOAA Port specific transformation metadata
        if isinstance(input_event, NoaaPortEventData):
            metadata[f"{self.transformer_id}_message_size_bytes"] = len(input_event.noaaport)
            metadata[f"{self.transformer_id}_has_delay_stamp"] = input_event.delay_stamp is not None

        if isinstance(output_event, TextProductEventData):
            metadata[f"{self.transformer_id}_parsing_success"] = True
            metadata[f"{self.transformer_id}_content_type"] = "application/json"

        return metadata
