"""Metrics API endpoints."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from loguru import logger

from nwws.metrics.exporters import PrometheusExporter

if TYPE_CHECKING:
    from nwws.metrics.registry import MetricRegistry


def create_metrics_router(registry: MetricRegistry) -> APIRouter:
    """Create metrics router.

    Args:
        registry: MetricRegistry instance for metrics access

    Returns:
        APIRouter configured with metrics endpoints

    """
    router = APIRouter()
    prometheus_exporter = PrometheusExporter(registry)

    @router.get("/metrics")
    async def prometheus_metrics() -> Response:  # type: ignore[no-untyped-def]
        """Export metrics in Prometheus exposition format.

        Returns:
            PlainTextResponse with Prometheus-formatted metrics.

        """
        try:
            metrics_text = prometheus_exporter.export()
            content_type = prometheus_exporter.get_content_type()

            logger.debug("Prometheus metrics exported")
            return PlainTextResponse(content=metrics_text, media_type=content_type)

        except Exception as e:
            logger.exception("Failed to export Prometheus metrics")
            raise HTTPException(status_code=500, detail="Failed to export metrics") from e

    @router.get("/metrics/json")
    async def json_metrics() -> JSONResponse:  # type: ignore[no-untyped-def]
        """Export metrics in JSON format.

        Returns:
            JSONResponse with all metrics in structured format.

        """
        try:
            metrics_data = {
                "timestamp": time.time(),
                "metrics": [metric.to_dict() for metric in registry.list_metrics()],
            }

            logger.debug("JSON metrics exported")
            return JSONResponse(content=metrics_data)

        except Exception as e:
            logger.error("Failed to export JSON metrics", exception=e)
            raise HTTPException(status_code=500, detail="Failed to export metrics") from e

    return router
