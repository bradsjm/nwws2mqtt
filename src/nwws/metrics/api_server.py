# pyright: strict
# pyright: reportUnusedFunction=false
"""FastAPI endpoints for metrics and health monitoring."""

from __future__ import annotations

import asyncio
import time
from asyncio import CancelledError

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from loguru import logger

from .exporters import PrometheusExporter
from .registry import MetricRegistry
from .ui import DashboardUI


class MetricApiServer:
    """FastAPI application for exposing metrics and health endpoints."""

    def __init__(self, registry: MetricRegistry | None = None) -> None:
        """Initialize the MetricsAPI with a metric registry.

        Args:
            registry: MetricRegistry instance. If None, creates a new one.

        """
        self.registry = registry or MetricRegistry()
        self.prometheus_exporter = PrometheusExporter(self.registry)
        self.dashboard_ui = DashboardUI()
        self.app = self._create_app()
        self._start_time = time.time()
        self.server = None
        self.server_task = None

    def _create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        app = FastAPI(
            title="NWWS2MQTT Metrics API",
            description="Health and metrics endpoints for NWWS2MQTT service",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
        )

        @app.get("/", include_in_schema=False)
        async def root() -> RedirectResponse:
            """Root endpoint to redirect to the dashboard."""
            return RedirectResponse("/dashboard")

        # Add endpoints
        app.add_api_route("/dashboard", self.dashboard, methods=["GET"])
        app.add_api_route("/health", self.health_check, methods=["GET"])
        app.add_api_route("/metrics", self.prometheus_metrics, methods=["GET"])
        app.add_api_route("/metrics/json", self.json_metrics, methods=["GET"])

        return app

    async def health_check(self) -> JSONResponse:
        """Return basic health check endpoint for Docker and load balancers.

        Returns:
            JSONResponse with health status and basic information.

        """
        uptime = time.time() - self._start_time

        health_data = {
            "status": "healthy",
            "service": "nwws2mqtt",
            "version": "1.0.0",
            "uptime_seconds": round(uptime, 2),
            "timestamp": time.time(),
            "metrics_count": len(self.registry.list_metrics()),
        }

        return JSONResponse(content=health_data)

    async def prometheus_metrics(self) -> Response:
        """Export metrics in Prometheus exposition format.

        Returns:
            PlainTextResponse with Prometheus-formatted metrics.

        """
        try:
            metrics_text = self.prometheus_exporter.export()
            content_type = self.prometheus_exporter.get_content_type()

            logger.debug("Prometheus metrics exported")
            return PlainTextResponse(content=metrics_text, media_type=content_type)

        except Exception as e:
            logger.exception("Failed to export Prometheus metrics")
            raise HTTPException(
                status_code=500, detail="Failed to export metrics"
            ) from e

    async def json_metrics(self) -> JSONResponse:
        """Export metrics in JSON format.

        Returns:
            JSONResponse with all metrics in structured format.

        """
        try:
            metrics_data = {
                "timestamp": time.time(),
                "metrics": [
                    metric.to_dict() for metric in self.registry.list_metrics()
                ],
            }

            logger.debug("JSON metrics exported")
            return JSONResponse(content=metrics_data)

        except Exception as e:
            logger.error("Failed to export JSON metrics", exception=e)
            raise HTTPException(
                status_code=500, detail="Failed to export metrics"
            ) from e

    async def dashboard(self) -> Response:
        """Render the interactive dashboard UI.

        Returns:
            HTMLResponse containing the complete dashboard interface.

        """
        try:
            # Get current health and metrics data
            health_data = {
                "status": "healthy",
                "service": "nwws2mqtt",
                "version": "1.0.0",
                "uptime_seconds": round(time.time() - self._start_time, 2),
                "timestamp": time.time(),
                "metrics_count": len(self.registry.list_metrics()),
            }

            metrics_data = {
                "timestamp": time.time(),
                "metrics": [
                    metric.to_dict() for metric in self.registry.list_metrics()
                ],
            }

            logger.debug("Dashboard rendered successfully")
            return self.dashboard_ui.render(health_data, metrics_data)

        except Exception as e:
            logger.error("Failed to render dashboard", exception=e)
            raise HTTPException(
                status_code=500, detail="Failed to render dashboard"
            ) from e

    async def start_server(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        log_level: str = "info",
        *,
        access_log: bool = False,
    ) -> None:
        """Start the uvicorn server in a background task.

        Args:
            host: Host to bind the server to.
            port: Port to bind the server to.
            log_level: Log level for uvicorn.
            access_log: Whether to enable access logs.

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

            logger.info("Metric API server started", host, port)

        except Exception:
            logger.exception("Failed to start metric API server")
            raise

    async def stop_server(self, *, shutdown_timeout: float = 5.0) -> None:
        """Stop the uvicorn server gracefully.

        Args:
            shutdown_timeout: Maximum time to wait for server shutdown.

        """
        if self.server_task and not self.server_task.done():
            try:
                # Signal the server to shutdown
                if self.server:
                    self.server.should_exit = True

                # Cancel the server task
                self.server_task.cancel()

                # Wait for the task to complete with timeout
                try:
                    await asyncio.wait_for(self.server_task, timeout=shutdown_timeout)
                except TimeoutError:
                    logger.warning("Metric API server shutdown timed out")
                except CancelledError:
                    pass  # Expected when cancelling

                logger.info("Metric API server stopped")

            except Exception:
                logger.exception("Error stopping metric API server")
                raise

    @property
    def is_running(self) -> bool:
        """Check if the server is currently running.

        Returns:
            True if the server is running, False otherwise.

        """
        return (
            self.server_task is not None
            and not self.server_task.done()
            and self.server is not None
        )
