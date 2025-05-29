"""Output modules for the NWWS2MQTT pipeline."""

from .console import ConsoleOutput
from .mqtt import MQTTOutput

__all__ = [
    "ConsoleOutput",
    "MQTTOutput",
]
