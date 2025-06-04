"""Geo API endpoints for weather data."""

import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from nwws.metrics.registry import MetricRegistry


def create_metrics_endpoints(router: APIRouter, registry: MetricRegistry) -> None:
    """Create metrics endpoints for dashboard.

    Args:
        router: FastAPI router to add endpoints to
        registry: MetricRegistry instance

    """

    @router.get("/api/metrics")
    async def get_current_metrics() -> JSONResponse:  # type: ignore[no-untyped-def]
        """Get current metrics for dashboard display."""
        try:
            metrics_data = {
                "timestamp": time.time(),
                "metrics": [metric.to_dict() for metric in registry.list_metrics()],
            }
            return JSONResponse(content=metrics_data)
        except Exception as e:
            logger.error("Failed to get dashboard metrics", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to retrieve metrics") from e
