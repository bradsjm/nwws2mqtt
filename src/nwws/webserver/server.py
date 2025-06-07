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
    """Unified web server for the NWWS2MQTT service providing HTTP endpoints and real-time monitoring.

    This class manages a FastAPI-based web server that serves multiple purposes within the
    NWWS2MQTT system architecture. It provides a unified interface for health monitoring,
    metrics collection, and real-time dashboard functionality. The server integrates with
    the MetricRegistry to expose system performance data and utilizes geographic data
    providers for weather office boundary visualization.

    The web server handles three primary responsibilities:
    - Health and metrics API endpoints for system monitoring and observability
    - Interactive dashboard with real-time WebSocket connections for live data streaming
    - Static file serving for dashboard assets and resources

    The server is designed for production deployment with proper CORS configuration,
    graceful shutdown handling, and comprehensive error logging. It supports both
    development and production environments with configurable static file serving
    and template directory management.
    """

    def __init__(
        self,
        registry: MetricRegistry,
        geo_provider: WeatherGeoDataProvider | None = None,
        templates_dir: str | None = None,
        static_dir: str | None = None,
    ) -> None:
        """Initialize the web server with all required dependencies and configuration.

        This constructor sets up the complete web server infrastructure by creating a
        FastAPI application instance with properly configured middleware, routers, and
        static file serving. The initialization process configures CORS middleware for
        cross-origin requests, mounts static file directories when available, and
        registers all API and dashboard routes with appropriate prefixes.

        The server tracks its start time for uptime calculations and maintains references
        to the uvicorn server instance and background tasks for proper lifecycle management.
        All route handlers are created with dependency injection to ensure testability
        and loose coupling between components.

        Args:
            registry: MetricRegistry instance providing access to system metrics and
                performance data for API endpoints and dashboard displays.
            geo_provider: Geographic data provider for weather office boundary data.
                If None, a default WeatherGeoDataProvider instance will be created.
            templates_dir: File system path to the Jinja2 templates directory for
                dashboard rendering. If None, default template discovery is used.
            static_dir: File system path to static assets (CSS, JavaScript, images)
                for dashboard functionality. Directory must exist to be mounted.

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
        """Start the web server and begin accepting HTTP connections.

        This method initializes and starts the uvicorn ASGI server in a background
        asyncio task, allowing the web server to run concurrently with other system
        components. The server is configured with the provided network settings and
        logging parameters, then launched asynchronously to avoid blocking the main
        application thread.

        The startup process creates a uvicorn.Config instance with the FastAPI
        application, network binding configuration, and logging settings. A background
        task is created to run the server's serve() method, which handles all incoming
        HTTP requests and WebSocket connections. The method includes comprehensive
        error handling for common startup failures such as port conflicts and
        network binding issues.

        All startup errors are logged with detailed context including error type and
        message to assist with debugging and system monitoring.

        Args:
            host: Network interface to bind the server to. Use "0.0.0.0" for all
                interfaces or specific IP addresses for restricted access.
            port: TCP port number for the server to listen on. Must be available
                and not conflicting with other services.
            log_level: Uvicorn logging verbosity level controlling server request
                and error logging output.
            access_log: Whether to enable detailed HTTP access logging for each
                request. Useful for debugging but may impact performance.

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
        """Stop the web server gracefully with proper cleanup and timeout handling.

        This method implements a graceful shutdown process that ensures all active
        connections are properly closed and resources are cleaned up before termination.
        The shutdown process signals the uvicorn server to stop accepting new connections,
        cancels the background server task, and waits for completion within the specified
        timeout period.

        The graceful shutdown sequence follows these steps:
        1. Signal the uvicorn server to begin shutdown by setting should_exit flag
        2. Cancel the background server task to interrupt the event loop
        3. Wait for task completion with timeout to prevent indefinite blocking
        4. Suppress CancelledError exceptions as they are expected during shutdown
        5. Log timeout warnings if shutdown exceeds the specified time limit

        All shutdown errors are caught and logged to prevent the shutdown process from
        failing and leaving resources in an inconsistent state. The method ensures
        the server state is properly cleaned up regardless of any errors encountered.

        Args:
            shutdown_timeout: Maximum time in seconds to wait for graceful shutdown
                completion. If exceeded, the server will be forcefully terminated.

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
                    except TimeoutError:
                        logger.warning("Web server shutdown timed out")

                logger.info("Web server stopped")

            except Exception:  # noqa: BLE001
                logger.exception("Error stopping web server")

    @property
    def is_running(self) -> bool:
        """Check if the web server is currently running and accepting connections.

        This property performs a comprehensive status check by verifying that the
        server task exists, is not completed or cancelled, and the uvicorn server
        instance is properly initialized. This provides an accurate indication of
        whether the server is actively processing HTTP requests and WebSocket
        connections.

        The status check ensures all components required for server operation are
        present and functional, including the background asyncio task and the
        uvicorn server instance.

        Returns:
            True if the server is actively running and accepting connections,
            False if the server is stopped, failed to start, or is shutting down.

        """
        return (
            self.server_task is not None and not self.server_task.done() and self.server is not None
        )

    @property
    def uptime(self) -> float:
        """Get the total server uptime since initialization.

        This property calculates the elapsed time since the WebServer instance was
        created, providing an accurate measure of how long the server has been
        operational. The uptime is measured from the moment of object instantiation
        rather than when the server actually starts accepting connections, giving
        a complete view of the server lifecycle.

        The uptime calculation uses wall-clock time and is suitable for monitoring
        and dashboard display purposes. For high-precision time measurements or
        elapsed time calculations that should be immune to system clock changes,
        consider using time.monotonic() instead.

        Returns:
            Total uptime in seconds as a floating-point number, providing
            sub-second precision for accurate monitoring and metrics collection.

        """
        return time.time() - self._start_time
