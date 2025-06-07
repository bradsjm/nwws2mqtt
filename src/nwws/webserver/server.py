"""Unified web server for NWWS2MQTT service."""

from __future__ import annotations

import asyncio
import time
from asyncio import CancelledError
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from nwws.utils import WeatherGeoDataProvider

from .api import create_health_router, create_metrics_router
from .dashboard import create_dashboard_router

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from nwws.metrics.registry import MetricRegistry


class WebServer:
    """Unified web server managing all HTTP endpoints and WebSocket connections."""

    def __init__(
        self,
        registry: MetricRegistry,
        geo_provider: WeatherGeoDataProvider | None = None,
        templates_dir: str | None = None,
        static_dir: str | None = None,
    ) -> None:
        """Initialize web server with dependencies.

        Args:
            registry: MetricRegistry instance for metrics access
            geo_provider: Geographic data provider for office boundaries
            templates_dir: Path to templates directory
            static_dir: Path to static files directory

        """
        self._start_time = time.time()
        self.registry = registry
        self.geo_provider = geo_provider or WeatherGeoDataProvider()
        self.templates_dir = templates_dir
        self.static_dir = static_dir

        # Connection manager will be set when creating dashboard router
        self.app = self._create_app()
        self.server = None
        self.server_task = None
        self._broadcast_task = None

    @asynccontextmanager
    async def _lifespan_context(self, _app: FastAPI) -> AsyncGenerator[None]:
        """Manage application lifespan events."""
        logger.info("Starting NWWS2MQTT web server")
        yield
        logger.info("Shutting down NWWS2MQTT web server")

    def _create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        app = FastAPI(
            title="NWWS2MQTT Service",
            description="National Weather Service data processing and monitoring",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
            lifespan=self._lifespan_context,
        )

        # Add middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Mount static files if directory provided
        if self.static_dir and Path(self.static_dir).exists():
            app.mount("/static", StaticFiles(directory=self.static_dir), name="static")

        # Create and mount routers
        health_router = create_health_router(self.registry)
        metrics_router = create_metrics_router(self.registry)
        dashboard_router = create_dashboard_router(
            self.registry, self.geo_provider, self.templates_dir
        )

        # Mount with clear prefixes
        app.include_router(health_router, prefix="/api/v1", tags=["health"])
        app.include_router(metrics_router, prefix="/api/v1", tags=["metrics"])
        app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])

        # Root redirect to dashboard
        @app.get("/", include_in_schema=False)
        async def root_redirect() -> RedirectResponse:  # type: ignore[not-accessed]
            return RedirectResponse("/dashboard")

        return app

    async def start(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        log_level: str = "info",
        *,
        access_log: bool = False,
    ) -> None:
        """Start the web server.

        Args:
            host: Host to bind the server to
            port: Port to bind the server to
            log_level: Log level for uvicorn
            access_log: Whether to enable access logs

        """
        try:
            # Create uvicorn config
            uvicorn_config = uvicorn.Config(
                app=self.app,
                host=host,
                port=port,
                log_level=log_level.lower(),
                access_log=access_log,
                loop="asyncio",
            )

            # Create and start server in background task
            self.server = uvicorn.Server(uvicorn_config)
            self.server_task = asyncio.create_task(self.server.serve())

            logger.info("Web server started", host=host, port=port)

        except (OSError, RuntimeError, ValueError) as e:
            logger.error("Failed to start web server", error=str(e), error_type=type(e).__name__)

    async def stop(self, *, shutdown_timeout: float = 5.0) -> None:
        """Stop the web server gracefully.

        Args:
            shutdown_timeout: Maximum time to wait for server shutdown

        """
        if self.server_task and not self.server_task.done():
            try:
                # Signal the server to shutdown
                if self.server:
                    self.server.should_exit = True

                # Cancel the server task
                self.server_task.cancel()

                # Wait for the task to complete with timeout
                with suppress(CancelledError):
                    try:
                        await asyncio.wait_for(self.server_task, timeout=shutdown_timeout)
                    except asyncio.TimeoutError:
                        logger.warning("Web server shutdown timed out")

                logger.info("Web server stopped")

            except Exception:  # noqa: BLE001
                logger.exception("Error stopping web server")

    @property
    def is_running(self) -> bool:
        """Check if the server is currently running.

        Returns:
            True if the server is running, False otherwise.

        """
        return (
            self.server_task is not None and not self.server_task.done() and self.server is not None
        )

    @property
    def uptime(self) -> float:
        """Get server uptime in seconds.

        Returns:
            Server uptime in seconds

        """
        return time.time() - self._start_time
