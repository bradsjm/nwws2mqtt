"""Transforms NoaaPort raw text to product."""

from loguru import logger
from pyiem.nws.products import parser

from nwws.models.events import NoaaPortEventData, TextProductEventData
from nwws.pipeline import PipelineEvent, PipelineEventMetadata, PipelineStage, Transformer
from nwws.utils import convert_text_product_to_model


class NoaaPortTransformer(Transformer):
    """Transforms NOAA Port text messages into structured products."""

    def __init__(self, transformer_id: str = "noaaport") -> None:
        """Initialize the console output."""
        super().__init__(transformer_id)

    def transform(self, event: PipelineEvent) -> PipelineEvent:
        """Handle incoming NOAA Port event and convert to a product."""
        if isinstance(event, NoaaPortEventData):
            product = convert_text_product_to_model(parser(text=event.noaaport, ugc_provider={}))

            logger.debug(
                "Transformed Raw Content to Text Product Model",
                event_id=event.metadata.event_id,
                product_id=event.id,
                subject=event.subject,
            )

            # Update metadata
            new_metadata = PipelineEventMetadata(
                event_id=event.metadata.event_id,
                source=self.transformer_id,
                stage=PipelineStage.TRANSFORM,
                trace_id=event.metadata.trace_id,
                custom=event.metadata.custom.copy(),
            )

            # Create new event data
            return TextProductEventData(
                metadata=new_metadata,
                awipsid=event.awipsid,
                cccc=event.cccc,
                id=event.id,
                issue=event.issue,
                product=product,
                subject=event.subject,
                ttaaii=event.ttaaii,
                delay_stamp=event.delay_stamp,
            )

        """Pass through event if not NoaaPortEventData"""
        return event
