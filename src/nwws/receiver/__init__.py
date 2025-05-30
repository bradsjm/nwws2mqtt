"""XMPP client package for NWWS-OI."""

from .weather_wire import WeatherWire, WeatherWireMessage

__all__ = [
    "WeatherWire",
    "WeatherWireMessage",
]
