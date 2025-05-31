"""Pipeline event data for CAP (Common Alerting Protocol) messages."""

from dataclasses import dataclass

from .noaa_port_event_data import NoaaPortEventData


@dataclass
class XmlEventData(NoaaPortEventData):
    """Pipeline event wrapper for XML events."""

    # Extracted XML content of the event
    xml: str

    def __str__(self) -> str:
        """Return a string representation of the XML event."""
        return self.xml
