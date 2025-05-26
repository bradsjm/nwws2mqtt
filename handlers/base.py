"""Base output handler and configuration classes."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OutputConfig:
    """Configuration for output handlers."""
    enabled_handlers: list[str]
    mqtt_broker: str | None = None
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_topic_prefix: str = "nwws"
    mqtt_qos: int = 1
    mqtt_retain: bool = True
    mqtt_client_id: str = "nwws-oi-client"
    mqtt_message_expiry_minutes: int = 5

    @classmethod
    def from_env(cls) -> "OutputConfig":
        """Create output config from environment variables."""
        # Parse enabled handlers from comma-separated string
        handlers_str = os.getenv("OUTPUT_HANDLERS", "console")
        enabled_handlers = [h.strip() for h in handlers_str.split(",") if h.strip()]

        return cls(
            enabled_handlers=enabled_handlers,
            mqtt_broker=os.getenv("MQTT_BROKER"),
            mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
            mqtt_username=os.getenv("MQTT_USERNAME"),
            mqtt_password=os.getenv("MQTT_PASSWORD"),
            mqtt_topic_prefix=os.getenv("MQTT_TOPIC_PREFIX", "nwws"),
            mqtt_qos=int(os.getenv("MQTT_QOS", "1")),
            mqtt_retain=os.getenv("MQTT_RETAIN", "false").lower() == "true",
            mqtt_client_id=os.getenv("MQTT_CLIENT_ID", "nwws-oi-client"),
            mqtt_message_expiry_minutes=int(os.getenv("MQTT_MESSAGE_EXPIRY_MINUTES", "5")),
        )


class OutputHandler(ABC):
    """Abstract base class for output handlers."""

    def __init__(self, config: OutputConfig) -> None:
        """Initialize the output handler."""
        self.config = config

    @abstractmethod
    async def publish(self, source: str, afos: str,  product_id: str, structured_data: str, subject: str = "") -> None:
        """Publish structured data to the output destination."""

    @abstractmethod
    async def start(self) -> None:
        """Start the output handler (initialize connections, etc.)."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the output handler (cleanup connections, etc.)."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if the handler is connected and ready to publish."""
