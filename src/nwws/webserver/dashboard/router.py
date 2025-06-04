"""Dashboard FastAPI router."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

from aiohttp import WebSocketError
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger

if TYPE_CHECKING:
    from utils import WeatherGeoDataProvider

    from nwws.metrics.registry import MetricRegistry


class DashboardConnectionManager:
    """Manages WebSocket connections for real-time dashboard updates."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: list[WebSocket] = []
        self._broadcast_task = None

    async def connect(self, websocket: WebSocket) -> None:
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """Send message to specific WebSocket connection."""
        try:
            await websocket.send_text(message)
        except (RuntimeError, WebSocketDisconnect):
            logger.warning("Failed to send message to WebSocket connection due to RuntimeError")

    async def broadcast(self, message: str) -> None:
        """Broadcast message to all active connections."""
        disconnected: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except (RuntimeError, WebSocketDisconnect):
                disconnected.append(connection)

        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_json(self, data: dict[str, Any]) -> None:
        """Broadcast JSON data to all active connections."""
        message = json.dumps(data)
        await self.broadcast(message)


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
                    "metrics": "/api/v1/metrics/json",
                    "geographic": "/dashboard/api/geo/activity",
                    "websocket": "/dashboard/ws",
                },
            }

            template = templates.get_template("dashboard.html")
            content = template.render(
                title="NWWS2MQTT Weather Operations Dashboard",
                initial_data=initial_data,
            )

            return HTMLResponse(content=content)

        except FileNotFoundError as e:
            logger.error("Dashboard template not found", error=str(e))
            return HTMLResponse(
                content="<h1>Dashboard Error</h1><p>Template not found</p>",
                status_code=500,
            )
        except PermissionError as e:
            logger.error("Permission denied accessing template", error=str(e))
            return HTMLResponse(
                content="<h1>Dashboard Error</h1><p>Template access denied</p>",
                status_code=500,
            )


def _create_geo_endpoints(router: APIRouter, geo_provider: WeatherGeoDataProvider) -> None:
    """Create geographic data endpoints.

    Args:
        router: FastAPI router to add endpoints to
        geo_provider: Geographic data provider

    """

    @router.get("/api/geo/boundaries")
    async def get_office_boundaries(simplification: str = "web") -> JSONResponse:  # type: ignore[no-untyped-def]
        """Get Weather Forecast Office boundaries as GeoJSON."""
        try:
            geojson_data = geo_provider.get_cwa_geojson(simplification)
            return JSONResponse(content=geojson_data)
        except Exception as e:
            logger.error("Failed to get office boundaries", error=str(e))
            raise HTTPException(
                status_code=500, detail="Failed to retrieve office boundaries"
            ) from e

    @router.get("/api/geo/metadata")
    async def get_office_metadata() -> JSONResponse:  # type: ignore[no-untyped-def]
        """Get office locations, regions, and coverage metadata."""
        try:
            metadata = geo_provider.get_office_metadata()
            return JSONResponse(content=metadata)
        except Exception as e:
            logger.error("Failed to get office metadata", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to retrieve office metadata") from e

    @router.get("/api/geo/regions")
    async def get_region_summary() -> JSONResponse:  # type: ignore[no-untyped-def]
        """Get summary statistics by NWS region."""
        try:
            regions = geo_provider.get_region_summary()
            return JSONResponse(content=regions)
        except Exception as e:
            logger.error("Failed to get region summary", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to retrieve region summary") from e

    @router.get("/api/geo/activity")
    async def get_geographic_activity() -> JSONResponse:  # type: ignore[no-untyped-def]
        """Get geographic activity data for map visualization."""
        try:
            activity_data: dict[str, Any] = {
                "regions": {},
                "offices": {},
                "timestamp": time.time(),
            }
            return JSONResponse(content=activity_data)
        except Exception as e:
            logger.error("Failed to get geographic activity", error=str(e))
            raise HTTPException(
                status_code=500, detail="Failed to retrieve geographic activity"
            ) from e


def _create_metrics_endpoints(router: APIRouter, registry: MetricRegistry) -> None:
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


async def _handle_client_message(
    data: str, websocket: WebSocket, manager: DashboardConnectionManager
) -> None:
    """Handle incoming WebSocket message from client."""
    try:
        message = json.loads(data)

        if message.get("type") == "ping":
            await manager.send_personal_message(
                json.dumps({"type": "pong", "timestamp": time.time()}), websocket
            )
        elif message.get("type") == "subscribe":
            # Handle subscription requests
            await manager.send_personal_message(
                json.dumps({"type": "subscribed", "topics": message.get("topics", [])}),
                websocket,
            )

    except json.JSONDecodeError:
        logger.warning("Invalid JSON received from WebSocket client")
    except WebSocketError as e:
        logger.error("Error handling WebSocket message", error=str(e))


def _create_websocket_endpoints(
    router: APIRouter, connection_manager: DashboardConnectionManager
) -> None:
    """Create WebSocket endpoints.

    Args:
        router: FastAPI router to add endpoints to
        connection_manager: WebSocket connection manager

    """

    @router.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:  # type: ignore[no-untyped-def]
        """WebSocket endpoint for real-time dashboard updates."""
        await connection_manager.connect(websocket)
        logger.info("Dashboard WebSocket connection established")

        try:
            while True:
                # Wait for client messages
                data = await websocket.receive_text()

                # Handle client message (could be ping, subscription requests, etc.)
                await _handle_client_message(data, websocket, connection_manager)

        except WebSocketDisconnect:
            logger.info("Dashboard WebSocket connection closed")
        finally:
            connection_manager.disconnect(websocket)


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
        APIRouter configured with dashboard endpoints

    """
    router = APIRouter()
    connection_manager = DashboardConnectionManager()
    templates = _setup_templates(templates_dir)

    # Add all endpoint groups
    _create_dashboard_endpoints(router, geo_provider, templates)
    _create_geo_endpoints(router, geo_provider)
    _create_metrics_endpoints(router, registry)
    _create_websocket_endpoints(router, connection_manager)

    return router
