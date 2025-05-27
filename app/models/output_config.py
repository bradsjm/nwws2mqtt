"""Output configuration dataclass for NWWS-OI handlers."""

import os
from dataclasses import dataclass


@dataclass
class OutputConfig:
    """Configuration class for output handlers."""

    enabled_handlers: list[str]

    # MQTT Configuration
    mqtt_broker: str | None = None
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_topic_prefix: str = "nwws"
    mqtt_qos: int = 1
    mqtt_retain: bool = False
    mqtt_client_id: str = "nwws-oi-client"
    mqtt_message_expiry_minutes: int = 60  # Message expiry time in minutes

    @classmethod
    def from_env(cls) -> "OutputConfig":
        """Create output config from environment variables."""
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
            mqtt_retain=os.getenv("MQTT_RETAIN", "false").lower() in ("true", "1", "yes"),
            mqtt_client_id=os.getenv("MQTT_CLIENT_ID", "nwws-oi-client"),
            mqtt_message_expiry_minutes=int(os.getenv("MQTT_MESSAGE_EXPIRY_MINUTES", "60")),
        )
