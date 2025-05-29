"""XMPP client package for NWWS-OI."""

from .weather_wire import WeatherWire, WeatherWireEvent

__all__ = [
    "WeatherWire",
    "WeatherWireEvent",
]
