"""Web dashboard server for real-time NWWS2MQTT statistics monitoring."""

import threading
import time

from loguru import logger
from nicegui import ui

from app.utils import LoggingConfig

from .collector import StatsCollector
from .dashboard_ui import StatusDashboard


class WebDashboardServer:
    """WebDashboardServer provides a real-time web-based dashboard for monitoring application stats.

    Attributes:
        stats_collector (StatsCollector): The statistics collector instance providing stats.
        port (int): The port on which the web dashboard is served.
        host (str): The host address to bind the web server to.
        update_interval (float): Interval in seconds for updating dashboard content.
        _is_running (bool): Indicates if the dashboard server is currently running.
        _server_thread (Optional[threading.Thread]): Thread running the web server.
        _dashboard_instance (Optional[StatusDashboard]): The dashboard instance for the session.

    Methods:
        start(): Starts the web dashboard server.
        stop(): Stops the web dashboard server.
        is_running: Property indicating if the server is running.
        dashboard_url: Property returning the URL of the dashboard.

    Usage:
        dashboard_server = WebDashboardServer(stats_collector, port=8081)
        dashboard_server.start()
        # Dashboard available at dashboard_server.dashboard_url
        dashboard_server.stop()

    """

    def __init__(
        self,
        stats_collector: StatsCollector,
        port: int = 8081,
        host: str = "127.0.0.1",
        update_interval: float = 5.0,
    ) -> None:
        """Initialize the web dashboard server.

        Args:
            stats_collector: The statistics collector instance
            port: Port to serve dashboard on
            host: Host address to bind the server to
            update_interval: How often to update dashboard content (seconds)

        """
        # Ensure logging is properly configured
        LoggingConfig.ensure_configured()

        self.stats_collector = stats_collector
        self.port = port
        self.host = host
        self.update_interval = update_interval
        self._is_running = False
        self._server_thread: threading.Thread | None = None
        self._dashboard_instance: StatusDashboard | None = None

        logger.info(
            "Web dashboard server initialized",
            port=port,
            host=host,
            update_interval=update_interval,
        )

    def start(self) -> None:
        """Start the web dashboard server in a separate thread."""
        if self._is_running:
            logger.warning("Web dashboard server is already running")
            return

        try:
            self._is_running = True
            self._server_thread = threading.Thread(target=self._run_server, daemon=True)
            self._server_thread.start()

            # Give the server a moment to start
            time.sleep(1.0)

            logger.info("Web dashboard server started", url=self.dashboard_url)

        except Exception as e:
            self._is_running = False
            logger.error("Failed to start web dashboard server", error=str(e))
            raise

    def stop(self) -> None:
        """Stop the web dashboard server."""
        if not self._is_running:
            return

        try:
            self._is_running = False

            # Stop the dashboard update timer if it exists
            if self._dashboard_instance:
                self._dashboard_instance.stop_updates()

            # Give time for graceful shutdown
            if self._server_thread and self._server_thread.is_alive():
                self._server_thread.join(timeout=5.0)

            logger.info("Web dashboard server stopped")

        except (TimeoutError, OSError, ConnectionError, RuntimeError) as e:
            logger.error("Error stopping web dashboard server", error=str(e))

    def _run_server(self) -> None:
        """Run the NiceGUI server in a separate thread."""
        try:
            # Ensure logging is configured in this thread
            LoggingConfig.reconfigure_for_thread()

            # Configure the NiceGUI app
            self._setup_routes()

            logger.info("Starting NiceGUI web server", host=self.host, port=self.port)

            # Run the server
            ui.run(
                host=self.host,
                port=self.port,
                title="NWWS2MQTT Status Dashboard",
                show=False,  # Don't open browser automatically
                reload=False,  # Disable auto-reload in production
                show_welcome_message=False,  # Disable welcome message
            )

        except (TimeoutError, OSError, ConnectionError, RuntimeError) as e:
            logger.error("Error running web dashboard server", error=str(e))
            self._is_running = False

    def _setup_routes(self) -> None:
        """Define NiceGUI routes and pages."""

        @ui.page("/")
        def index() -> None:  # type: ignore  # noqa: PGH003
            """Display main dashboard page."""
            try:
                # Create dashboard instance with stats collector
                self._dashboard_instance = StatusDashboard(self.stats_collector)
                self._dashboard_instance.create_dashboard()

                logger.debug("Dashboard page rendered successfully")

            except (TimeoutError, OSError, ConnectionError, RuntimeError) as e:
                logger.error("Error rendering dashboard page", error=str(e))
                # Show error page
                ui.label("Dashboard Error").classes("text-2xl font-bold text-red-600")
                ui.label(f"Failed to load dashboard: {e}").classes("text-red-500")

        @ui.page("/health")
        def health() -> None:  # type: ignore  # noqa: PGH003
            """Health check endpoint."""
            ui.label("OK")

    @property
    def is_running(self) -> bool:
        """Check if the dashboard server is currently running."""
        return self._is_running

    @property
    def dashboard_url(self) -> str:
        """Get the dashboard URL."""
        return f"http://{self.host}:{self.port}"
