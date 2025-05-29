"""Pipeline event data for WeatherWire events."""

from dataclasses import dataclass

from pipeline import PipelineEvent


@dataclass
class NoaaPortEventData(PipelineEvent):
    """Pipeline event wrapper for NOAAPort events from WeatherWire."""

    awipsid: str
    """AWIPS ID of the product, if available; otherwise 'NONE'."""
    cccc: str
    """CCCC code representing the issuing office or center."""
    id: str
    """Unique identifier for the product."""
    issue: str
    """Issue time of the product in ISO 8601 format."""
    noaaport: str
    """NOAAPort formatted text of the product message."""
    subject: str
    """Subject of the message, typically the product type or title."""
    ttaaii: str
    """TTAAII code representing the product type and time."""
