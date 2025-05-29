"""Pipeline event data for WMO Products."""

from dataclasses import dataclass

from models.weather.product import TextProductModel
from pipeline import PipelineEvent


@dataclass
class TextProductEventData(PipelineEvent):
    """Pipeline event wrapper for WeatherWire events."""

    awipsid: str
    """AWIPS ID of the product, if available; otherwise 'NONE'."""
    cccc: str
    """CCCC code representing the issuing office or center."""
    id: str
    """Unique identifier for the product."""
    issue: str
    """Issue time of the product in ISO 8601 format."""
    product: TextProductModel
    """WeatherWire text product model converted from raw data."""
    subject: str
    """Subject of the message, typically the product type or title."""
    ttaaii: str
    """TTAAII code representing the product type and time."""
    delay_stamp: str | None
    """Delay stamp if the message was delayed, otherwise None."""
