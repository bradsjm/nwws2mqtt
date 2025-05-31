"""Pipeline event data for WMO Products."""

from dataclasses import dataclass
from datetime import datetime

from nwws.models.weather.product import TextProductModel
from nwws.pipeline import PipelineEvent


@dataclass
class TextProductEventData(PipelineEvent):
    """Pipeline event wrapper for WeatherWire events."""

    awipsid: str
    """AWIPS ID of the product, if available; otherwise 'NONE'."""
    cccc: str
    """CCCC code representing the issuing office or center."""
    id: str
    """Unique identifier for the product."""
    issue: datetime
    """Issue time of the product as a datetime object."""
    product: TextProductModel
    """WeatherWire text product model converted from raw data."""
    subject: str
    """Subject of the message, typically the product type or title."""
    ttaaii: str
    """TTAAII code representing the product type and time."""
    delay_stamp: datetime | None
    """Delay stamp if the message was delayed, otherwise None."""
