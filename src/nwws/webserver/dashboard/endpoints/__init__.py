"""Dashboard Endpoints."""

from .geo import create_geo_endpoints
from .metrics import create_metrics_endpoints

__all__ = [
    "create_geo_endpoints",
    "create_metrics_endpoints",
]
