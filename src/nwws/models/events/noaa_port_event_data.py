"""Base event data for pipeline events in the NWWs (National Weather Warning System)."""

from dataclasses import dataclass
from datetime import datetime

from nwws.pipeline import PipelineEvent


@dataclass
class NoaaPortEventData(PipelineEvent):
    """Pipeline event wrapper for NWWS events."""

    awipsid: str
    """AWIPS ID of the product, starts with 'CAP'."""
    cccc: str
    """CCCC code representing the issuing office or center."""
    id: str
    """Unique identifier for the product."""
    issue: datetime
    """Issue time of the product as a datetime object."""
    subject: str
    """Subject of the message, typically the product type or title."""
    ttaaii: str
    """TTAAII code representing the product type and time."""
    delay_stamp: datetime | None
    """Delay stamp if the message was delayed, otherwise None."""

    noaaport: str
    """Raw NOAA Port message content as a string."""

    content_type: str
    """Content type of the message, e.g., 'text/plain'."""

    def __str__(self) -> str:
        """Return a string representation of the event."""
        return self.noaaport
