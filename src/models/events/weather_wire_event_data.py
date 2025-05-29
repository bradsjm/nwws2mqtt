"""Pipeline event data for WeatherWire events."""

from dataclasses import dataclass

from pipeline import PipelineEvent
from receiver import WeatherWireEvent


@dataclass
class WeatherWireEventData(PipelineEvent):
    """Pipeline event wrapper for WeatherWire events."""

    weather_event: WeatherWireEvent
    """The original weather wire event."""
