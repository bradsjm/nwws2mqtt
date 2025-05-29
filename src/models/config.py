"""Application configuration for NWWS-OI client."""

import os
from dataclasses import dataclass

from .mqtt_config import MqttConfig


@dataclass
class Config:
    """Configuration class for NWWS-OI client."""

    username: str
    password: str
    server: str = "nwws-oi.weather.gov"
    port: int = 5222
    log_level: str = "INFO"
    log_file: str | None = None
    mqtt_config: MqttConfig | None = None
    stats_interval: int = 60  # Statistics logging interval in seconds
    metrics_enabled: bool = False  # Enable Prometheus metrics endpoint
    metrics_port: int = 8080  # Port for Prometheus metrics endpoint
    metrics_update_interval: int = 30  # How often to update metrics in seconds
    dashboard_enabled: bool = True  # Enable web dashboard
    dashboard_port: int = 8081  # Port for web dashboard
    dashboard_host: str = "127.0.0.1"  # Host for web dashboard

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables."""
        return cls(
            username=os.getenv("NWWS_USERNAME", ""),
            password=os.getenv("NWWS_PASSWORD", ""),
            server=os.getenv("NWWS_SERVER", "nwws-oi.weather.gov"),
            port=int(os.getenv("NWWS_PORT", "5222")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE"),
            mqtt_config=MqttConfig.from_env(),
            stats_interval=int(os.getenv("STATS_INTERVAL", "60")),
            metrics_enabled=os.getenv("METRICS_ENABLED", "false").lower() in ("true", "1", "yes"),
            metrics_port=int(os.getenv("METRICS_PORT", "8080")),
            metrics_update_interval=int(os.getenv("METRICS_UPDATE_INTERVAL", "30")),
            dashboard_enabled=os.getenv("DASHBOARD_ENABLED", "false").lower() in ("true", "1", "yes"),
            dashboard_port=int(os.getenv("DASHBOARD_PORT", "8081")),
            dashboard_host=os.getenv("DASHBOARD_HOST", "127.0.0.1"),
        )
