"""Converts NOAA port text to product."""

from loguru import logger
from pyiem.nws.product import TextProduct  # type: ignore[import]

from messaging import TextProductEvent, WeatherWireEvent
from messaging.message_bus import MessageBus
from utils import convert_text_product_to_model


class NoaaportTransformer:
    """Transforms NOAA Port text messages into structured products."""

    def __init__(self) -> None:
        """Initialize the transformer."""
        logger.info("NoaaportTransformer initialized")
        MessageBus.subscribe(WeatherWireEvent, event_callback=self.handle_weather_wire_event)

    def handle_weather_wire_event(self, event: WeatherWireEvent) -> None:
        """Handle incoming NOAA Port event and convert to a product."""
        logger.debug("Received WeatherWire Event", subject=event.subject, id=event.id)

        # Convert the NOAAPort text to a TextProduct instance
        text_product = convert_text_product_to_model(TextProduct(event.noaaport, ugc_provider={}))
        MessageBus.emit(
            TextProductEvent(
                subject=event.subject,
                product=text_product,
                id=event.id,
                issue=event.issue,
                ttaaii=event.ttaaii,
                cccc=event.cccc,
                awipsid=event.awipsid,
            ),
        )
        logger.debug("Publishing TextProduct event", id=event.id, subject=event.subject)
