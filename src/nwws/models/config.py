"""Application configuration for NWWS-OI client."""

import os
from dataclasses import dataclass

from .mqtt_config import MqttConfig


@dataclass
class Config:
    """Configuration class for NWWS-OI client."""

    nwws_username: str
    nwws_password: str
    nwws_server: str = "nwws-oi.weather.gov"
    nwws_port: int = 5222
    log_level: str = "INFO"
    log_file: str | None = None
    mqtt_config: MqttConfig | None = None
    metric_server: bool = True  # Enable metrics
    metric_port: int = 8080  # Port for  metrics endpoint
    metric_host: str = "127.0.0.1"  # Host for metrics endpoint
    outputs: str = "console"  # Comma-separated list of outputs (console,mqtt)

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables."""
        return cls(
            nwws_username=os.getenv("NWWS_USERNAME", ""),
            nwws_password=os.getenv("NWWS_PASSWORD", ""),
            nwws_server=os.getenv("NWWS_SERVER", "nwws-oi.weather.gov"),
            nwws_port=int(os.getenv("NWWS_PORT", "5222")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE"),
            mqtt_config=MqttConfig.from_env(),
            metric_server=os.getenv("METRIC_SERVER", "true").lower()
            in ("true", "1", "yes"),
            metric_port=int(os.getenv("METRIC_PORT", "8080")),
            metric_host=os.getenv("METRIC_HOST", "127.0.0.1"),
            outputs=os.getenv("OUTPUTS", "console"),
        )
