"""API package for NWWS2MQTT web server endpoints."""

from .health_router import create_health_router
from .metrics_router import create_metrics_router

__all__ = ["create_health_router", "create_metrics_router"]
