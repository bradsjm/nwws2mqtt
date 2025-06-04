"""Health check API endpoints."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from fastapi import APIRouter
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from nwws.metrics.registry import MetricRegistry


def create_health_router(registry: MetricRegistry) -> APIRouter:
    """Create health check router.

    Args:
        registry: MetricRegistry instance for health metrics

    Returns:
        APIRouter configured with health endpoints

    """
    router = APIRouter()

    @router.get("/health")
    async def health_check() -> JSONResponse:  # type: ignore[no-untyped-def]
        """Return basic health check endpoint for Docker and load balancers.

        Returns:
            JSONResponse with health status and basic information.

        """
        health_data = {
            "status": "healthy",
            "service": "nwws2mqtt",
            "version": "1.0.0",
            "timestamp": time.time(),
            "metrics_count": len(registry.list_metrics()),
        }

        return JSONResponse(content=health_data)

    @router.get("/ready")
    async def readiness_check() -> JSONResponse:  # type: ignore[no-untyped-def]
        """Readiness check for Kubernetes deployments.

        Returns:
            JSONResponse indicating service readiness

        """
        # Basic readiness - can be enhanced with dependency checks
        ready_data = {
            "status": "ready",
            "service": "nwws2mqtt",
            "timestamp": time.time(),
        }

        return JSONResponse(content=ready_data)

    @router.get("/live")
    async def liveness_check() -> JSONResponse:  # type: ignore[no-untyped-def]
        """Liveness check for Kubernetes deployments.

        Returns:
            JSONResponse indicating service is alive

        """
        live_data = {
            "status": "alive",
            "service": "nwws2mqtt",
            "timestamp": time.time(),
        }

        return JSONResponse(content=live_data)

    return router
