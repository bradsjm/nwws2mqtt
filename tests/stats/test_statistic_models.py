"""Unit tests for statistics data models."""

from collections import Counter
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.stats.statistic_models import (
    ApplicationStats,
    ConnectionStats,
    MessageStats,
    OutputHandlerStats,
    StatsSnapshot,
)


class TestConnectionStats:
    """Test ConnectionStats model."""

    @pytest.mark.unit
    def test_default_initialization(self) -> None:
        """Test default ConnectionStats initialization."""
        stats = ConnectionStats()

        assert isinstance(stats.start_time, datetime)
        assert stats.connected_at is None
        assert stats.disconnected_at is None
        assert stats.total_connections == 0
        assert stats.total_disconnections == 0
        assert stats.reconnect_attempts == 0
        assert stats.auth_failures == 0
        assert stats.connection_errors == 0
        assert stats.is_connected is False
        assert stats.last_ping_sent is None
        assert stats.last_pong_received is None
        assert stats.outstanding_pings == 0

    @pytest.mark.unit
    def test_uptime_seconds_no_connection(self) -> None:
        """Test uptime calculation when never connected."""
        stats = ConnectionStats()
        assert stats.uptime_seconds == 0.0

    @pytest.mark.unit
    def test_uptime_seconds_with_connection(self) -> None:
        """Test uptime calculation with active connection."""
        now = datetime.utcnow()
        connected_time = now - timedelta(minutes=5)

        stats = ConnectionStats(connected_at=connected_time)

        with patch("app.stats.statistic_models.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = now
            uptime = stats.uptime_seconds

        assert uptime == pytest.approx(300.0, rel=1e-2)  # 5 minutes

    @pytest.mark.unit
    def test_uptime_seconds_with_disconnection(self) -> None:
        """Test uptime calculation with disconnected state."""
        now = datetime.utcnow()
        connected_time = now - timedelta(minutes=10)
        disconnected_time = now - timedelta(minutes=3)

        stats = ConnectionStats(connected_at=connected_time, disconnected_at=disconnected_time)

        uptime = stats.uptime_seconds
        assert uptime == pytest.approx(420.0, rel=1e-2)  # 7 minutes

    @pytest.mark.unit
    def test_total_uptime_seconds(self) -> None:
        """Test total uptime calculation since start."""
        now = datetime.utcnow()
        start_time = now - timedelta(hours=2)

        stats = ConnectionStats(start_time=start_time)

        with patch("app.stats.statistic_models.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = now
            total_uptime = stats.total_uptime_seconds

        assert total_uptime == pytest.approx(7200.0, rel=1e-2)  # 2 hours

    @pytest.mark.unit
    def test_total_uptime_seconds_no_start_time(self) -> None:
        """Test total uptime when start_time is None."""
        stats = ConnectionStats(start_time=None)  # type: ignore
        assert stats.total_uptime_seconds == 0.0


class TestMessageStats:
    """Test MessageStats model."""

    @pytest.mark.unit
    def test_default_initialization(self) -> None:
        """Test default MessageStats initialization."""
        stats = MessageStats()

        assert stats.total_received == 0
        assert stats.total_processed == 0
        assert stats.total_failed == 0
        assert stats.total_published == 0
        assert stats.last_message_time is None
        assert stats.last_groupchat_message_time is None
        assert isinstance(stats.wmo_codes, Counter)
        assert isinstance(stats.sources, Counter)
        assert isinstance(stats.afos_codes, Counter)
        assert isinstance(stats.processing_errors, Counter)

    @pytest.mark.unit
    def test_success_rate_no_messages(self) -> None:
        """Test success rate calculation with no messages."""
        stats = MessageStats()
        assert stats.success_rate == 0.0

    @pytest.mark.unit
    def test_success_rate_with_messages(self) -> None:
        """Test success rate calculation with messages."""
        stats = MessageStats(total_received=100, total_processed=85)
        assert stats.success_rate == 85.0

    @pytest.mark.unit
    def test_error_rate_no_messages(self) -> None:
        """Test error rate calculation with no messages."""
        stats = MessageStats()
        assert stats.error_rate == 0.0

    @pytest.mark.unit
    def test_error_rate_with_messages(self) -> None:
        """Test error rate calculation with messages."""
        stats = MessageStats(total_received=100, total_failed=15)
        assert stats.error_rate == 15.0

    @pytest.mark.unit
    def test_counters_functionality(self) -> None:
        """Test that Counter objects work correctly."""
        stats = MessageStats()

        # Test WMO codes
        stats.wmo_codes["FXUS61"] = 5
        stats.wmo_codes["FXUS62"] = 3
        assert stats.wmo_codes["FXUS61"] == 5
        assert stats.wmo_codes["FXUS62"] == 3
        assert stats.wmo_codes["UNKNOWN"] == 0  # Default counter behavior

        # Test sources
        stats.sources["NWWS-OI"] = 10
        assert stats.sources["NWWS-OI"] == 10

        # Test AFOS codes
        stats.afos_codes["AFGAFC"] = 2
        assert stats.afos_codes["AFGAFC"] == 2

        # Test processing errors
        stats.processing_errors["parse_error"] = 1
        assert stats.processing_errors["parse_error"] == 1


class TestOutputHandlerStats:
    """Test OutputHandlerStats model."""

    @pytest.mark.unit
    def test_initialization(self) -> None:
        """Test OutputHandlerStats initialization."""
        stats = OutputHandlerStats(handler_type="mqtt")

        assert stats.handler_type == "mqtt"
        assert stats.total_published == 0
        assert stats.total_failed == 0
        assert stats.is_connected is False
        assert stats.connected_at is None
        assert stats.disconnected_at is None
        assert stats.connection_errors == 0
        assert stats.last_publish_time is None

    @pytest.mark.unit
    def test_success_rate_no_attempts(self) -> None:
        """Test success rate with no publish attempts."""
        stats = OutputHandlerStats(handler_type="mqtt")
        assert stats.success_rate == 0.0

    @pytest.mark.unit
    def test_success_rate_with_attempts(self) -> None:
        """Test success rate with publish attempts."""
        stats = OutputHandlerStats(handler_type="mqtt", total_published=80, total_failed=20)
        assert stats.success_rate == 80.0

    @pytest.mark.unit
    def test_success_rate_all_successful(self) -> None:
        """Test success rate with all successful publishes."""
        stats = OutputHandlerStats(handler_type="mqtt", total_published=100, total_failed=0)
        assert stats.success_rate == 100.0

    @pytest.mark.unit
    def test_success_rate_all_failed(self) -> None:
        """Test success rate with all failed publishes."""
        stats = OutputHandlerStats(handler_type="mqtt", total_published=0, total_failed=100)
        assert stats.success_rate == 0.0


class TestApplicationStats:
    """Test ApplicationStats model."""

    @pytest.mark.unit
    def test_default_initialization(self) -> None:
        """Test default ApplicationStats initialization."""
        stats = ApplicationStats()

        assert isinstance(stats.start_time, datetime)
        assert isinstance(stats.connection, ConnectionStats)
        assert isinstance(stats.messages, MessageStats)
        assert isinstance(stats.output_handlers, dict)
        assert len(stats.output_handlers) == 0

    @pytest.mark.unit
    def test_running_time_seconds(self) -> None:
        """Test running time calculation."""
        now = datetime.utcnow()
        start_time = now - timedelta(hours=1, minutes=30)

        stats = ApplicationStats(start_time=start_time)

        with patch("app.stats.statistic_models.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = now
            running_time = stats.running_time_seconds

        assert running_time == pytest.approx(5400.0, rel=1e-2)  # 1.5 hours

    @pytest.mark.unit
    def test_output_handlers_management(self) -> None:
        """Test output handlers dictionary functionality."""
        stats = ApplicationStats()

        # Add handler
        mqtt_handler = OutputHandlerStats(handler_type="mqtt")
        stats.output_handlers["mqtt_primary"] = mqtt_handler

        assert "mqtt_primary" in stats.output_handlers
        assert stats.output_handlers["mqtt_primary"].handler_type == "mqtt"

        # Add another handler
        console_handler = OutputHandlerStats(handler_type="console")
        stats.output_handlers["console"] = console_handler

        assert len(stats.output_handlers) == 2
        assert "console" in stats.output_handlers


class TestStatsSnapshot:
    """Test StatsSnapshot model."""

    @pytest.mark.unit
    def test_initialization_with_timestamp(self) -> None:
        """Test StatsSnapshot initialization with provided timestamp."""
        timestamp = datetime.utcnow()
        stats = ApplicationStats()
        snapshot = StatsSnapshot(timestamp=timestamp, stats=stats)

        assert snapshot.timestamp == timestamp
        assert snapshot.stats == stats

    @pytest.mark.unit
    def test_initialization_without_timestamp(self) -> None:
        """Test StatsSnapshot initialization without timestamp."""
        stats = ApplicationStats()
        snapshot = StatsSnapshot(timestamp=None, stats=stats)  # type: ignore

        # __post_init__ should set timestamp
        assert snapshot.timestamp is not None
        assert isinstance(snapshot.timestamp, datetime)

    @pytest.mark.unit
    def test_post_init_sets_timestamp(self) -> None:
        """Test that __post_init__ sets timestamp when None."""
        stats = ApplicationStats()

        with patch("app.stats.statistic_models.datetime") as mock_datetime:
            expected_time = datetime.utcnow()
            mock_datetime.utcnow.return_value = expected_time

            snapshot = StatsSnapshot(timestamp=None, stats=stats)  # type: ignore

        assert snapshot.timestamp == expected_time

    @pytest.mark.unit
    def test_post_init_preserves_existing_timestamp(self) -> None:
        """Test that __post_init__ preserves existing timestamp."""
        stats = ApplicationStats()
        original_timestamp = datetime.utcnow() - timedelta(minutes=5)

        snapshot = StatsSnapshot(timestamp=original_timestamp, stats=stats)

        assert snapshot.timestamp == original_timestamp


class TestComplexStatisticsScenarios:
    """Test complex scenarios with multiple stats objects."""

    @pytest.mark.unit
    def test_complete_application_stats_scenario(self) -> None:
        """Test a complete application statistics scenario."""
        # Create application stats
        app_stats = ApplicationStats()

        # Simulate connection events
        app_stats.connection.total_connections = 3
        app_stats.connection.total_disconnections = 2
        app_stats.connection.reconnect_attempts = 1
        app_stats.connection.is_connected = True
        app_stats.connection.connected_at = datetime.utcnow() - timedelta(minutes=30)

        # Simulate message processing
        app_stats.messages.total_received = 1000
        app_stats.messages.total_processed = 950
        app_stats.messages.total_failed = 50
        app_stats.messages.total_published = 940

        # Add WMO codes and sources
        app_stats.messages.wmo_codes["FXUS61"] = 300
        app_stats.messages.wmo_codes["FXUS62"] = 250
        app_stats.messages.sources["NWWS-OI"] = 1000
        app_stats.messages.afos_codes["AFGAFC"] = 150
        app_stats.messages.processing_errors["parse_error"] = 30
        app_stats.messages.processing_errors["timeout"] = 20

        # Add output handlers
        mqtt_stats = OutputHandlerStats(
            handler_type="mqtt", total_published=470, total_failed=5, is_connected=True
        )
        console_stats = OutputHandlerStats(
            handler_type="console", total_published=470, total_failed=0, is_connected=True
        )

        app_stats.output_handlers["mqtt_primary"] = mqtt_stats
        app_stats.output_handlers["console"] = console_stats

        # Verify calculations
        assert app_stats.messages.success_rate == 95.0
        assert app_stats.messages.error_rate == 5.0
        assert mqtt_stats.success_rate == pytest.approx(98.95, rel=1e-2)
        assert console_stats.success_rate == 100.0

        # Verify counters
        assert sum(app_stats.messages.wmo_codes.values()) == 550
        assert app_stats.messages.sources["NWWS-OI"] == 1000
        assert sum(app_stats.messages.processing_errors.values()) == 50

    @pytest.mark.unit
    def test_stats_snapshot_with_complex_data(self) -> None:
        """Test StatsSnapshot with complex application data."""
        # Create complex app stats
        app_stats = ApplicationStats()

        # Set up complex message stats
        app_stats.messages.total_received = 5000
        app_stats.messages.total_processed = 4800
        app_stats.messages.wmo_codes.update(
            {"FXUS61": 1500, "FXUS62": 1200, "WWUS75": 800, "URGENT": 300}
        )

        # Create snapshot
        timestamp = datetime.utcnow()
        snapshot = StatsSnapshot(timestamp=timestamp, stats=app_stats)

        # Verify snapshot captures all data
        assert snapshot.stats.messages.total_received == 5000
        assert snapshot.stats.messages.total_processed == 4800
        assert len(snapshot.stats.messages.wmo_codes) == 4
        assert snapshot.stats.messages.wmo_codes["FXUS61"] == 1500
        assert snapshot.timestamp == timestamp
