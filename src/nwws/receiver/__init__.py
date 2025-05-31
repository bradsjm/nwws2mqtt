"""XMPP client package for NWWS-OI."""

from .config import WeatherWireConfig
from .stats import ReceiverStatsEvent, WeatherWireStatsCollector
from .weather_wire import WeatherWire, WeatherWireMessage

__all__ = [
    "ReceiverStatsEvent",
    "WeatherWire",
    "WeatherWireConfig",
    "WeatherWireMessage",
    "WeatherWireStatsCollector",
]
