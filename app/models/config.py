from app.handlers import OutputConfig


import os
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration class for NWWS-OI client."""
    username: str
    password: str
    server: str = "nwws-oi.weather.gov"
    port: int = 5222
    log_level: str = "INFO"
    log_file: str | None = None
    output_config: OutputConfig | None = None
    stats_interval: int = 60  # Statistics logging interval in seconds
    metrics_enabled: bool = True  # Enable Prometheus metrics endpoint
    metrics_port: int = 8080  # Port for Prometheus metrics endpoint
    metrics_update_interval: int = 30  # How often to update metrics in seconds

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables."""
        username = os.getenv("NWWS_USERNAME")
        password = os.getenv("NWWS_PASSWORD")

        if not username or not password:
            raise ValueError("NWWS_USERNAME and NWWS_PASSWORD environment variables must be set")

        return cls(
            username=username,
            password=password,
            server=os.getenv("NWWS_SERVER", "nwws-oi.weather.gov"),
            port=int(os.getenv("NWWS_PORT", "5222")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE"),
            output_config=OutputConfig.from_env(),
            stats_interval=int(os.getenv("STATS_INTERVAL", "60")),
            metrics_enabled=os.getenv("METRICS_ENABLED", "true").lower() in ("true", "1", "yes"),
            metrics_port=int(os.getenv("METRICS_PORT", "8080")),
            metrics_update_interval=int(os.getenv("METRICS_UPDATE_INTERVAL", "30")),
        )