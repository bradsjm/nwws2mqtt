"""Web-based status dashboard for NWWS2MQTT application."""

from datetime import UTC, datetime

from nicegui import ui

from .collector import StatsCollector


class StatusDashboard:
    """Web-based status dashboard for monitoring application health."""

    def __init__(self, stats_collector: StatsCollector) -> None:
        """Initialize dashboard with statistics collector.

        Args:
            stats_collector: Statistics collector for real-time data

        """
        self.stats_collector = stats_collector
        self.update_timer: ui.timer | None = None

        # Get initial stats for display
        self.stats = self.stats_collector.get_stats()

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime seconds into human-readable string.

        Args:
            seconds: Uptime in seconds

        Returns:
            Formatted uptime string

        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        if seconds < 3600:
            return f"{seconds / 60:.1f}m"
        if seconds < 86400:
            return f"{seconds / 3600:.1f}h"
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        return f"{days}d {hours}h"

    def _format_datetime(self, dt: datetime | None) -> str:
        """Format datetime for display.

        Args:
            dt: Datetime to format

        Returns:
            Formatted datetime string

        """
        if dt is None:
            return "Never"
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    def _get_status_color(self, is_connected: bool, has_errors: bool = False) -> str:
        """Get status indicator color.

        Args:
            is_connected: Whether connection is active
            has_errors: Whether there are errors

        Returns:
            CSS color class

        """
        if not is_connected:
            return "red"
        if has_errors:
            return "orange"
        return "green"

    def _create_header(self) -> None:
        """Create dashboard header."""
        with ui.row().classes("w-full justify-between items-center p-4 bg-blue-100"):
            ui.label("NWWS2MQTT Status Dashboard").classes("text-2xl font-bold")
            with ui.column().classes("text-right"):
                self.current_time_label = ui.label().classes("text-sm text-gray-600")
                overall_status = self._get_status_color(
                    self.stats.connection.is_connected,
                    self.stats.messages.total_failed > 0,
                )
                with ui.row().classes("items-center gap-2"):
                    ui.icon("circle", color=overall_status).classes("text-lg")
                    ui.label("System Status").classes("font-medium")

    def _create_app_overview(self) -> None:
        """Create application overview section."""
        with ui.card().classes("w-full"):
            ui.label("Application Overview").classes("text-lg font-bold mb-4")

            with ui.grid(columns=3).classes("gap-4 w-full"):
                # Uptime
                with ui.column().classes("text-center"):
                    ui.label("Uptime").classes("text-sm text-gray-600")
                    self.uptime_label = ui.label().classes("text-xl font-bold")

                # Start Time
                with ui.column().classes("text-center"):
                    ui.label("Started At").classes("text-sm text-gray-600")
                    ui.label(self._format_datetime(self.stats.start_time)).classes("text-lg")

                # Status
                with ui.column().classes("text-center"):
                    ui.label("Connection Status").classes("text-sm text-gray-600")
                    color = self._get_status_color(self.stats.connection.is_connected)
                    status_text = (
                        "Connected" if self.stats.connection.is_connected else "Disconnected"
                    )
                    ui.label(status_text).classes(f"text-xl font-bold text-{color}-600")

    def _create_connection_status(self) -> None:
        """Create connection status section."""
        with ui.card().classes("w-full"):
            ui.label("XMPP Connection").classes("text-lg font-bold mb-4")

            conn = self.stats.connection

            # Connection metrics in grid
            with ui.grid(columns=4).classes("gap-4 w-full"):
                # Session uptime
                with ui.column().classes("text-center"):
                    ui.label("Session Uptime").classes("text-sm text-gray-600")
                    self.session_uptime_label = ui.label().classes("text-lg font-bold")

                # Total connections
                with ui.column().classes("text-center"):
                    ui.label("Connections").classes("text-sm text-gray-600")
                    ui.label(str(conn.total_connections)).classes("text-lg font-bold")

                # Reconnects
                with ui.column().classes("text-center"):
                    ui.label("Reconnects").classes("text-sm text-gray-600")
                    ui.label(str(conn.reconnect_attempts)).classes("text-lg font-bold")

                # Errors
                with ui.column().classes("text-center"):
                    ui.label("Errors").classes("text-sm text-gray-600")
                    error_count = conn.auth_failures + conn.connection_errors
                    color = "red" if error_count > 0 else "gray"
                    ui.label(str(error_count)).classes(f"text-lg font-bold text-{color}-600")

            # Connection timestamps
            with ui.row().classes("gap-8 mt-4"):
                with ui.column():
                    ui.label("Connected At").classes("text-sm text-gray-600")
                    ui.label(self._format_datetime(conn.connected_at)).classes("text-sm")

                with ui.column():
                    ui.label("Last Ping").classes("text-sm text-gray-600")
                    ui.label(self._format_datetime(conn.last_ping_sent)).classes("text-sm")

                with ui.column():
                    ui.label("Last Pong").classes("text-sm text-gray-600")
                    ui.label(self._format_datetime(conn.last_pong_received)).classes("text-sm")

    def _create_message_stats(self) -> None:
        """Create message processing statistics section."""
        with ui.card().classes("w-full"):
            ui.label("Message Processing").classes("text-lg font-bold mb-4")

            msg = self.stats.messages

            # Main metrics
            with ui.grid(columns=4).classes("gap-4 w-full mb-4"):
                # Received
                with ui.column().classes("text-center"):
                    ui.label("Received").classes("text-sm text-gray-600")
                    self.received_label = ui.label(str(msg.total_received)).classes(
                        "text-xl font-bold text-blue-600",
                    )

                # Processed
                with ui.column().classes("text-center"):
                    ui.label("Processed").classes("text-sm text-gray-600")
                    self.processed_label = ui.label(str(msg.total_processed)).classes(
                        "text-xl font-bold text-green-600",
                    )

                # Failed
                with ui.column().classes("text-center"):
                    ui.label("Failed").classes("text-sm text-gray-600")
                    color = "red" if msg.total_failed > 0 else "gray"
                    self.failed_label = ui.label(str(msg.total_failed)).classes(
                        f"text-xl font-bold text-{color}-600",
                    )

                # Published
                with ui.column().classes("text-center"):
                    ui.label("Published").classes("text-sm text-gray-600")
                    self.published_label = ui.label(str(msg.total_published)).classes(
                        "text-xl font-bold text-purple-600",
                    )

            # Success and error rates
            with ui.row().classes("gap-8 mb-4"):
                with ui.column().classes("text-center"):
                    ui.label("Success Rate").classes("text-sm text-gray-600")
                    self.success_rate_label = ui.label(f"{msg.success_rate:.1f}%").classes(
                        "text-lg font-bold text-green-600",
                    )

                with ui.column().classes("text-center"):
                    ui.label("Error Rate").classes("text-sm text-gray-600")
                    color = "red" if msg.error_rate > 0 else "gray"
                    self.error_rate_label = ui.label(f"{msg.error_rate:.1f}%").classes(
                        f"text-lg font-bold text-{color}-600",
                    )

            # Last message times
            with ui.row().classes("gap-8"):
                with ui.column():
                    ui.label("Last Message").classes("text-sm text-gray-600")
                    self.last_message_label = ui.label(
                        self._format_datetime(msg.last_message_time),
                    ).classes("text-sm")

                with ui.column():
                    ui.label("Last Groupchat").classes("text-sm text-gray-600")
                    self.last_groupchat_label = ui.label(
                        self._format_datetime(msg.last_groupchat_message_time),
                    ).classes("text-sm")

    def _create_message_breakdowns(self) -> None:
        """Create message breakdown sections."""
        msg = self.stats.messages

        with ui.row().classes("w-full gap-4"):
            # WMO
            with ui.card().classes("flex-1"):
                ui.label("Top WMO Codes").classes("text-lg font-bold mb-2")
                if msg.wmo_codes:
                    for wmo, count in msg.wmo_codes.most_common(5):
                        with ui.row().classes("justify-between w-full"):
                            ui.label(wmo).classes("text-sm")
                            ui.label(str(count)).classes("text-sm font-bold")
                else:
                    ui.label("No data").classes("text-sm text-gray-500")

            # Sources
            with ui.card().classes("flex-1"):
                ui.label("Top Sources").classes("text-lg font-bold mb-2")
                if msg.sources:
                    for source, count in msg.sources.most_common(5):
                        with ui.row().classes("justify-between w-full"):
                            ui.label(source).classes("text-sm")
                            ui.label(str(count)).classes("text-sm font-bold")
                else:
                    ui.label("No data").classes("text-sm text-gray-500")

            # AFOS codes
            with ui.card().classes("flex-1"):
                ui.label("Top AFOS Codes").classes("text-lg font-bold mb-2")
                if msg.afos_codes:
                    for afos, count in msg.afos_codes.most_common(5):
                        with ui.row().classes("justify-between w-full"):
                            ui.label(afos).classes("text-sm")
                            ui.label(str(count)).classes("text-sm font-bold")
                else:
                    ui.label("No data").classes("text-sm text-gray-500")

    def _create_output_handlers(self) -> None:
        """Create output handlers section."""
        with ui.card().classes("w-full"):
            ui.label("Output Handlers").classes("text-lg font-bold mb-4")

            if not self.stats.output_handlers:
                ui.label("No output handlers configured").classes("text-gray-500")
                return

            # Create table for handlers
            columns = [
                {"name": "handler", "label": "Handler", "field": "handler", "align": "left"},
                {"name": "status", "label": "Status", "field": "status", "align": "center"},
                {"name": "published", "label": "Published", "field": "published", "align": "right"},
                {"name": "failed", "label": "Failed", "field": "failed", "align": "right"},
                {
                    "name": "success_rate",
                    "label": "Success %",
                    "field": "success_rate",
                    "align": "right",
                },
                {
                    "name": "last_publish",
                    "label": "Last Publish",
                    "field": "last_publish",
                    "align": "center",
                },
            ]

            rows: list[dict[str, str | int]] = []
            for handler_stats in self.stats.output_handlers.values():
                status_icon = "✅" if handler_stats.is_connected else "❌"
                rows.append(
                    {
                        "handler": handler_stats.handler_type,
                        "status": status_icon,
                        "published": handler_stats.total_published,
                        "failed": handler_stats.total_failed,
                        "success_rate": f"{handler_stats.success_rate:.1f}%",
                        "last_publish": self._format_datetime(handler_stats.last_publish_time),
                    },
                )

            ui.table(columns=columns, rows=rows).classes("w-full")

    def _create_recent_errors(self) -> None:
        """Create recent errors section."""
        with ui.card().classes("w-full"):
            ui.label("Processing Errors").classes("text-lg font-bold mb-4")

            if not self.stats.messages.processing_errors:
                ui.label("No processing errors").classes("text-green-600")
                return

            # Show top processing errors
            for error, count in self.stats.messages.processing_errors.most_common(10):
                with ui.row().classes("justify-between w-full p-2 bg-red-50 rounded"):
                    ui.label(error).classes("text-sm text-red-800")
                    ui.label(f"({count})").classes("text-sm font-bold text-red-600")

    def _update_dynamic_content(self) -> None:
        """Update dynamic content that changes frequently."""
        # Get fresh statistics
        self.stats = self.stats_collector.get_stats()

        # Update current time
        self.current_time_label.text = f"Updated: {datetime.now(UTC).strftime('%H:%M:%S UTC')}"

        # Update uptime
        self.uptime_label.text = self._format_uptime(self.stats.running_time_seconds)

        # Update session uptime
        self.session_uptime_label.text = self._format_uptime(self.stats.connection.uptime_seconds)

        # Update message counts
        msg = self.stats.messages
        self.received_label.text = str(msg.total_received)
        self.processed_label.text = str(msg.total_processed)
        self.failed_label.text = str(msg.total_failed)
        self.published_label.text = str(msg.total_published)

        # Update rates
        self.success_rate_label.text = f"{msg.success_rate:.1f}%"
        self.error_rate_label.text = f"{msg.error_rate:.1f}%"

        # Update last message times
        self.last_message_label.text = self._format_datetime(msg.last_message_time)
        self.last_groupchat_label.text = self._format_datetime(msg.last_groupchat_message_time)

    def create_dashboard(self) -> None:
        """Create the complete dashboard layout."""
        # Set page title and dark mode
        ui.page_title("NWWS2MQTT Status Dashboard")

        with ui.column().classes("w-full max-w-7xl mx-auto p-4 gap-6"):
            self._create_header()
            self._create_app_overview()
            self._create_connection_status()
            self._create_message_stats()
            self._create_message_breakdowns()
            self._create_output_handlers()
            self._create_recent_errors()

        # Start update timer
        self.update_timer = ui.timer(5.0, self._update_dynamic_content)

    def stop_updates(self) -> None:
        """Stop the dashboard update timer."""
        if self.update_timer:
            self.update_timer.cancel()
