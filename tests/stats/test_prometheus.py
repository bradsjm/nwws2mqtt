"""Unit tests for PrometheusMetricsExporter."""

from collections import Counter
from unittest.mock import Mock, call, patch

import pytest

from app.stats.collector import StatsCollector
from app.stats.prometheus import PrometheusMetricsExporter
from app.stats.statistic_models import (
    ApplicationStats,
    OutputHandlerStats,
)


class TestPrometheusExporterInitialization:
    """Test PrometheusMetricsExporter initialization."""

    @pytest.mark.unit
    def test_default_initialization(self) -> None:
        """Test default PrometheusMetricsExporter initialization."""
        with patch("app.stats.prometheus.LoggingConfig"):
            mock_collector = Mock(spec=StatsCollector)
            exporter = PrometheusMetricsExporter(mock_collector)

        assert exporter.stats_collector is mock_collector
        assert exporter.port == 8080
        assert exporter.update_interval == 30
        assert exporter._is_running is False
        assert exporter._update_task is None
        assert exporter._server_thread is None
        assert exporter.registry is not None

    @pytest.mark.unit
    def test_custom_initialization(self) -> None:
        """Test PrometheusMetricsExporter with custom parameters."""
        with patch("app.stats.prometheus.LoggingConfig"):
            mock_collector = Mock(spec=StatsCollector)
            exporter = PrometheusMetricsExporter(mock_collector, port=9090, update_interval=60)

        assert exporter.port == 9090
        assert exporter.update_interval == 60

    @pytest.mark.unit
    def test_metrics_initialization(self) -> None:
        """Test that all Prometheus metrics are initialized."""
        with patch("app.stats.prometheus.LoggingConfig"):
            mock_collector = Mock(spec=StatsCollector)
            exporter = PrometheusMetricsExporter(mock_collector)

        # Check that key metrics exist
        assert hasattr(exporter, "app_info")
        assert hasattr(exporter, "app_uptime_seconds")
        assert hasattr(exporter, "connection_status")
        assert hasattr(exporter, "messages_received_total")
        assert hasattr(exporter, "output_handler_status")

    @pytest.mark.unit
    def test_is_running_property(self) -> None:
        """Test is_running property."""
        with patch("app.stats.prometheus.LoggingConfig"):
            mock_collector = Mock(spec=StatsCollector)
            exporter = PrometheusMetricsExporter(mock_collector)

        assert exporter.is_running is False

        exporter._is_running = True
        assert exporter.is_running is True

    @pytest.mark.unit
    def test_metrics_url_property(self) -> None:
        """Test metrics_url property."""
        with patch("app.stats.prometheus.LoggingConfig"):
            mock_collector = Mock(spec=StatsCollector)
            exporter = PrometheusMetricsExporter(mock_collector, port=9090)

        assert exporter.metrics_url == "http://localhost:9090/metrics"


class TestExporterLifecycle:
    """Test exporter start/stop lifecycle."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def exporter(self, mock_collector: Mock) -> PrometheusMetricsExporter:
        """Create PrometheusMetricsExporter with mocked dependencies."""
        with patch("app.stats.prometheus.LoggingConfig"):
            return PrometheusMetricsExporter(mock_collector, update_interval=1)

    @pytest.mark.unit
    def test_start_exporter(self, exporter: PrometheusMetricsExporter) -> None:
        """Test starting the metrics exporter."""
        with patch("app.stats.prometheus.LoopingCall") as mock_looping_call:
            with patch.object(exporter, "_start_http_server"):
                mock_task = Mock()
                mock_looping_call.return_value = mock_task
                mock_thread = Mock()

                with patch("app.stats.prometheus.threading.Thread", return_value=mock_thread):
                    exporter.start()

        mock_thread.start.assert_called_once()
        mock_looping_call.assert_called_once_with(exporter._update_metrics)
        mock_task.start.assert_called_once_with(1)
        assert exporter._is_running is True
        assert exporter._update_task is mock_task
        assert exporter._server_thread is mock_thread

    @pytest.mark.unit
    def test_start_already_running(self, exporter: PrometheusMetricsExporter) -> None:
        """Test starting when already running."""
        exporter._is_running = True

        with patch("app.stats.prometheus.LoopingCall") as mock_looping_call:
            exporter.start()

        mock_looping_call.assert_not_called()

    @pytest.mark.unit
    def test_start_exception_handling(self, exporter: PrometheusMetricsExporter) -> None:
        """Test exception handling during start."""
        with patch("app.stats.prometheus.LoopingCall") as mock_looping_call:
            mock_looping_call.side_effect = Exception("Start error")

            with pytest.raises(Exception, match="Start error"):
                exporter.start()

    @pytest.mark.unit
    def test_stop_exporter(self, exporter: PrometheusMetricsExporter) -> None:
        """Test stopping the metrics exporter."""
        # Set up running state
        mock_task = Mock()
        mock_task.running = True
        exporter._update_task = mock_task
        exporter._is_running = True

        exporter.stop()

        mock_task.stop.assert_called_once()
        assert exporter._is_running is False

    @pytest.mark.unit
    def test_stop_not_running(self, exporter: PrometheusMetricsExporter) -> None:
        """Test stopping when not running."""
        assert exporter._is_running is False

        exporter.stop()  # Should not raise any exceptions

    @pytest.mark.unit
    def test_stop_task_not_running(self, exporter: PrometheusMetricsExporter) -> None:
        """Test stopping when task exists but not running."""
        mock_task = Mock()
        mock_task.running = False
        exporter._update_task = mock_task
        exporter._is_running = True

        exporter.stop()

        mock_task.stop.assert_not_called()
        assert exporter._is_running is False

    @pytest.mark.unit
    def test_stop_exception_handling(self, exporter: PrometheusMetricsExporter) -> None:
        """Test exception handling during stop."""
        mock_task = Mock()
        mock_task.running = True
        mock_task.stop.side_effect = Exception("Stop error")
        exporter._update_task = mock_task
        exporter._is_running = True

        # Should not raise exception, but _is_running stays True due to exception
        exporter.stop()
        assert exporter._is_running is True  # Exception prevents setting to False


class TestHTTPServer:
    """Test HTTP server functionality."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def exporter(self, mock_collector: Mock) -> PrometheusMetricsExporter:
        """Create PrometheusMetricsExporter with mocked dependencies."""
        with patch("app.stats.prometheus.LoggingConfig"):
            return PrometheusMetricsExporter(mock_collector, port=8080)

    @pytest.mark.unit
    def test_start_http_server_success(self, exporter: PrometheusMetricsExporter) -> None:
        """Test successful HTTP server start."""
        with patch("app.stats.prometheus.start_http_server") as mock_start_server:
            exporter._start_http_server()

        mock_start_server.assert_called_once_with(8080, registry=exporter.registry)

    @pytest.mark.unit
    def test_start_http_server_exception(self, exporter: PrometheusMetricsExporter) -> None:
        """Test HTTP server start exception handling."""
        with patch("app.stats.prometheus.start_http_server") as mock_start_server:
            mock_start_server.side_effect = Exception("Server error")

            with pytest.raises(Exception, match="Server error"):
                exporter._start_http_server()


class TestMetricsUpdates:
    """Test metrics update functionality."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def exporter(self, mock_collector: Mock) -> PrometheusMetricsExporter:
        """Create PrometheusMetricsExporter with mocked dependencies."""
        with patch("app.stats.prometheus.LoggingConfig"):
            return PrometheusMetricsExporter(mock_collector)

    @pytest.fixture
    def sample_stats(self) -> ApplicationStats:
        """Create sample ApplicationStats for testing."""
        stats = ApplicationStats()

        # Connection stats
        stats.connection.is_connected = True
        stats.connection.total_connections = 5
        stats.connection.total_disconnections = 2
        stats.connection.reconnect_attempts = 1
        stats.connection.auth_failures = 0
        stats.connection.connection_errors = 1
        stats.connection.outstanding_pings = 2

        # Message stats
        stats.messages.total_received = 1000
        stats.messages.total_processed = 950
        stats.messages.total_failed = 50
        stats.messages.total_published = 940

        # Add counters
        stats.messages.wmo_codes = Counter({"FXUS61": 300, "FXUS62": 250})
        stats.messages.sources = Counter({"NWWS-OI": 1000})
        stats.messages.afos_codes = Counter({"AFGAFC": 150, "URGENT": 100})
        stats.messages.processing_errors = Counter({"parse_error": 30, "timeout": 20})

        # Output handlers
        mqtt_handler = OutputHandlerStats(
            handler_type="mqtt",
            total_published=470,
            total_failed=25,
            is_connected=True,
            connection_errors=2,
        )
        stats.output_handlers["mqtt_primary"] = mqtt_handler

        return stats

    @pytest.mark.unit
    def test_update_metrics_success(
        self, exporter: PrometheusMetricsExporter, sample_stats: ApplicationStats
    ) -> None:
        """Test successful metrics update."""
        exporter.stats_collector.get_stats.return_value = sample_stats

        with patch.object(exporter, "_update_application_metrics") as mock_app_update:
            with patch.object(exporter, "_update_connection_metrics") as mock_conn_update:
                with patch.object(exporter, "_update_message_metrics") as mock_msg_update:
                    with patch.object(
                        exporter, "_update_output_handler_metrics"
                    ) as mock_handler_update:
                        exporter._update_metrics()

        exporter.stats_collector.get_stats.assert_called_once()
        mock_app_update.assert_called_once_with(sample_stats)
        mock_conn_update.assert_called_once_with(sample_stats)
        mock_msg_update.assert_called_once_with(sample_stats)
        mock_handler_update.assert_called_once_with(sample_stats)

    @pytest.mark.unit
    def test_update_metrics_exception(self, exporter: PrometheusMetricsExporter) -> None:
        """Test exception handling in metrics update."""
        exporter.stats_collector.get_stats.side_effect = Exception("Update error")

        # Should not raise exception
        exporter._update_metrics()

    @pytest.mark.unit
    def test_update_application_metrics(
        self, exporter: PrometheusMetricsExporter, sample_stats: ApplicationStats
    ) -> None:
        """Test application metrics update."""
        with patch.object(exporter.app_info, "info") as mock_info:
            with patch.object(exporter.app_uptime_seconds, "set") as mock_uptime:
                exporter._update_application_metrics(sample_stats)

        mock_info.assert_called_once()
        mock_uptime.assert_called_once()

    @pytest.mark.unit
    def test_update_connection_metrics_first_time(
        self, exporter: PrometheusMetricsExporter, sample_stats: ApplicationStats
    ) -> None:
        """Test connection metrics update for first time."""
        with patch.object(exporter.connection_status, "set") as mock_status:
            with patch.object(exporter.connection_uptime_seconds, "set") as mock_uptime:
                with patch.object(exporter.connection_total_connections, "inc") as mock_connections:
                    exporter._update_connection_metrics(sample_stats)

        mock_status.assert_called_once_with(1)
        mock_uptime.assert_called_once()
        mock_connections.assert_called_once_with(5)

        # Verify last values were stored
        assert hasattr(exporter, "_last_connection_values")
        assert exporter._last_connection_values["total_connections"] == 5

    @pytest.mark.unit
    def test_update_connection_metrics_incremental(
        self, exporter: PrometheusMetricsExporter, sample_stats: ApplicationStats
    ) -> None:
        """Test incremental connection metrics update."""
        # Set initial values
        exporter._last_connection_values = {
            "total_connections": 3,
            "total_disconnections": 1,
            "reconnect_attempts": 0,
            "auth_failures": 0,
            "connection_errors": 0,
        }

        with patch.object(exporter.connection_total_connections, "inc") as mock_connections:
            with patch.object(
                exporter.connection_total_disconnections, "inc"
            ) as mock_disconnections:
                with patch.object(exporter.connection_reconnect_attempts, "inc") as mock_reconnects:
                    with patch.object(exporter.connection_errors, "inc") as mock_errors:
                        exporter._update_connection_metrics(sample_stats)

        # Should increment by the difference
        mock_connections.assert_called_once_with(2)  # 5 - 3
        mock_disconnections.assert_called_once_with(1)  # 2 - 1
        mock_reconnects.assert_called_once_with(1)  # 1 - 0
        mock_errors.assert_called_once_with(1)  # 1 - 0

    @pytest.mark.unit
    def test_update_message_metrics_first_time(
        self, exporter: PrometheusMetricsExporter, sample_stats: ApplicationStats
    ) -> None:
        """Test message metrics update for first time."""
        with patch.object(exporter.messages_received_total, "inc") as mock_received:
            with patch.object(exporter.message_processing_success_rate, "set") as mock_success_rate:
                with patch.object(exporter.wmo_total, "labels") as mock_product_labels:
                    mock_product_counter = Mock()
                    mock_product_labels.return_value = mock_product_counter

                    exporter._update_message_metrics(sample_stats)

        mock_received.assert_called_once_with(1000)
        mock_success_rate.assert_called_once()

        # Verify last values were stored
        assert hasattr(exporter, "_last_message_values")
        assert exporter._last_message_values["total_received"] == 1000

    @pytest.mark.unit
    def test_update_output_handler_metrics(
        self, exporter: PrometheusMetricsExporter, sample_stats: ApplicationStats
    ) -> None:
        """Test output handler metrics update."""
        with (
            patch.object(exporter.output_handler_status, "labels") as mock_status_labels,
            patch.object(
                exporter.output_handler_published_total, "labels"
            ) as mock_published_labels,
            patch.object(
                exporter.output_handler_success_rate, "labels"
            ) as mock_success_rate_labels,
        ):
            # Mock the labeled metric objects
            mock_status_metric = Mock()
            mock_published_metric = Mock()
            mock_success_rate_metric = Mock()

            mock_status_labels.return_value = mock_status_metric
            mock_published_labels.return_value = mock_published_metric
            mock_success_rate_labels.return_value = mock_success_rate_metric

            exporter._update_output_handler_metrics(sample_stats)

            # Verify labels were called with handler info
            mock_status_labels.assert_called_with(handler_name="mqtt_primary", handler_type="mqtt")
            mock_published_labels.assert_called_with(
                handler_name="mqtt_primary", handler_type="mqtt"
            )
            mock_success_rate_labels.assert_called_with(
                handler_name="mqtt_primary", handler_type="mqtt"
            )

            # Verify metrics were set/incremented
            mock_status_metric.set.assert_called_once_with(1)
            mock_success_rate_metric.set.assert_called_once()


class TestCounterManagement:
    """Test counter-based metrics management."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def exporter(self, mock_collector: Mock) -> PrometheusMetricsExporter:
        """Create PrometheusMetricsExporter with mocked dependencies."""
        with patch("app.stats.prometheus.LoggingConfig"):
            return PrometheusMetricsExporter(mock_collector)

    @pytest.mark.unit
    def test_counter_increments_only_on_change(self, exporter: PrometheusMetricsExporter) -> None:
        """Test that counters only increment when values change."""
        # First update
        stats1 = ApplicationStats()
        stats1.connection.total_connections = 5

        with patch.object(exporter.connection_total_connections, "inc") as mock_inc:
            exporter._update_connection_metrics(stats1)

        mock_inc.assert_called_once_with(5)

        # Second update with same values
        with patch.object(exporter.connection_total_connections, "inc") as mock_inc:
            exporter._update_connection_metrics(stats1)

        mock_inc.assert_not_called()  # Should not increment again

    @pytest.mark.unit
    def test_message_error_counters_by_type(self, exporter: PrometheusMetricsExporter) -> None:
        """Test message error counters by error type."""
        stats = ApplicationStats()
        stats.messages.processing_errors = Counter({"parse_error": 10, "timeout": 5})

        with patch.object(exporter.messages_failed_total, "labels") as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter

            exporter._update_message_metrics(stats)

        # Should be called for each error type
        expected_calls = [call(error_type="parse_error"), call(error_type="timeout")]
        mock_labels.assert_has_calls(expected_calls, any_order=True)
        assert mock_counter.inc.call_count == 2


class TestComplexScenarios:
    """Test complex metrics scenarios."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def exporter(self, mock_collector: Mock) -> PrometheusMetricsExporter:
        """Create PrometheusMetricsExporter with mocked dependencies."""
        with patch("app.stats.prometheus.LoggingConfig"):
            return PrometheusMetricsExporter(mock_collector, update_interval=1)

    @pytest.mark.unit
    def test_progressive_metrics_updates(self, exporter: PrometheusMetricsExporter) -> None:
        """Test progressive metrics updates over time."""
        # First update
        stats1 = ApplicationStats()
        stats1.messages.total_received = 100
        stats1.messages.total_processed = 95

        with patch.object(exporter.messages_received_total, "inc") as mock_received:
            with patch.object(exporter.messages_processed_total, "inc") as mock_processed:
                exporter._update_message_metrics(stats1)

        mock_received.assert_called_once_with(100)
        mock_processed.assert_called_once_with(95)

        # Second update with incremental values
        stats2 = ApplicationStats()
        stats2.messages.total_received = 150
        stats2.messages.total_processed = 140

        with patch.object(exporter.messages_received_total, "inc") as mock_received:
            with patch.object(exporter.messages_processed_total, "inc") as mock_processed:
                exporter._update_message_metrics(stats2)

        mock_received.assert_called_once_with(50)  # 150 - 100
        mock_processed.assert_called_once_with(45)  # 140 - 95

    @pytest.mark.unit
    def test_full_exporter_lifecycle(self, exporter: PrometheusMetricsExporter) -> None:
        """Test complete exporter lifecycle."""
        # Prepare stats
        stats = ApplicationStats()
        stats.connection.is_connected = True
        stats.messages.total_received = 500
        exporter.stats_collector.get_stats.return_value = stats

        # Test lifecycle
        assert not exporter.is_running

        # Start (mocked)
        with patch("app.stats.prometheus.LoopingCall"):
            with patch.object(exporter, "_start_http_server"):
                with patch("app.stats.prometheus.threading.Thread"):
                    exporter.start()

        assert exporter.is_running

        # Update metrics
        exporter._update_metrics()

        # Stop
        mock_task = Mock()
        mock_task.running = True
        exporter._update_task = mock_task

        exporter.stop()
        assert not exporter.is_running
