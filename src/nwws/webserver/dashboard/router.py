"""Dashboard FastAPI router."""

from __future__ import annotations

from typing import TYPE_CHECKING

import jinja2
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger

from nwws.webserver.dashboard.endpoints import (
    create_geo_endpoints,
    create_metrics_endpoints,
)

if TYPE_CHECKING:
    from utils import WeatherGeoDataProvider

    from nwws.metrics.registry import MetricRegistry


def _setup_templates(templates_dir: str | None) -> Environment | None:
    """Set up Jinja2 templates environment.

    Args:
        templates_dir: Path to templates directory

    Returns:
        Configured Jinja2 environment or None if setup fails

    """
    if not templates_dir:
        return None

    try:
        return Environment(
            loader=FileSystemLoader(templates_dir), autoescape=select_autoescape(["html", "xml"])
        )
    except FileNotFoundError as e:
        logger.warning("Templates directory not found", error=str(e))
        return None
    except PermissionError as e:
        logger.warning("Permission denied accessing templates", error=str(e))
        return None


def _create_dashboard_endpoints(
    router: APIRouter,
    geo_provider: WeatherGeoDataProvider,
    templates: Environment | None,
) -> None:
    """Create dashboard HTML endpoints.

    Args:
        router: FastAPI router to add endpoints to
        geo_provider: Geographic data provider
        templates: Jinja2 templates environment

    """

    @router.get("/", response_class=HTMLResponse)
    async def dashboard_home() -> HTMLResponse:  # type: ignore[no-untyped-def]
        """Serve the main dashboard HTML page."""
        if not templates:
            return HTMLResponse(
                content="<h1>Dashboard Unavailable</h1><p>Templates not configured</p>",
                status_code=503,
            )

        try:
            # Get initial data for dashboard
            initial_data = {
                "office_count": len(geo_provider.get_office_metadata().get("offices", {})),
                "regions": geo_provider.get_region_summary(),
                "api_endpoints": {
                    "metrics": "/dashboard/api/metrics",
                    "geographic": "/dashboard/api/geo/activity",
                },
            }

            template = templates.get_template("dashboard.html")
            content = template.render(
                title="Weather Operations Dashboard",
                initial_data=initial_data,
            )

            return HTMLResponse(content=content)

        except jinja2.TemplateError as e:
            logger.error(
                "Dashboard template error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return HTMLResponse(
                content=f"<h1>Dashboard Error</h1><p>A template error occurred: {e}</p>",
                status_code=500,
            )


def create_dashboard_router(
    registry: MetricRegistry,
    geo_provider: WeatherGeoDataProvider,
    templates_dir: str | None = None,
) -> APIRouter:
    """Create dashboard router with all dashboard endpoints.

    Args:
        registry: MetricRegistry instance for metrics access
        geo_provider: Geographic data provider for office boundaries
        templates_dir: Path to templates directory

    Returns:
        Tuple of (APIRouter configured with dashboard endpoints, DashboardConnectionManager)

    """
    router = APIRouter()
    templates = _setup_templates(templates_dir)

    # Add all endpoint groups
    _create_dashboard_endpoints(router, geo_provider, templates)
    create_geo_endpoints(router, geo_provider)
    create_metrics_endpoints(router, registry)

    return router
