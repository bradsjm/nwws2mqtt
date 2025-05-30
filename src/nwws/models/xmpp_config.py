"""Configuration for XMPP client."""

from dataclasses import dataclass


@dataclass
class XMPPConfig:
    """Configuration class for XMPP client."""

    username: str
    password: str
    server: str = "nwws-oi.weather.gov"
    port: int = 5222
