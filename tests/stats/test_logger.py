"""Unit tests for StatsLogger."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from app.stats.collector import StatsCollector
from app.stats.logger import StatsLogger
from app.stats.statistic_models import (
    ApplicationStats,
    OutputHandlerStats,
    StatsSnapshot,
)


class TestStatsLoggerInitialization:
    """Test StatsLogger initialization."""

    @pytest.mark.unit
    def test_default_initialization(self) -> None:
        """Test default StatsLogger initialization."""
        with patch("app.stats.logger.LoggingConfig"):
            mock_collector = Mock(spec=StatsCollector)
            logger = StatsLogger(mock_collector)

        assert logger.stats_collector is mock_collector
        assert logger.log_interval_seconds == 60
        assert logger._logging_task is None
        assert logger._is_running is False
        assert logger._snapshots == []
        assert logger._max_snapshots == 10

    @pytest.mark.unit
    def test_custom_interval_initialization(self) -> None:
        """Test StatsLogger with custom interval."""
        with patch("app.stats.logger.LoggingConfig"):
            mock_collector = Mock(spec=StatsCollector)
            logger = StatsLogger(mock_collector, log_interval_seconds=30)

        assert logger.log_interval_seconds == 30

    @pytest.mark.unit
    def test_is_running_property(self) -> None:
        """Test is_running property."""
        with patch("app.stats.logger.LoggingConfig"):
            mock_collector = Mock(spec=StatsCollector)
            logger = StatsLogger(mock_collector)

        assert logger.is_running is False

        logger._is_running = True
        assert logger.is_running is True


class TestLoggingLifecycle:
    """Test logging start/stop lifecycle."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def logger(self, mock_collector: Mock) -> StatsLogger:
        """Create StatsLogger with mocked dependencies."""
        with patch("app.stats.logger.LoggingConfig"):
            return StatsLogger(mock_collector, log_interval_seconds=1)

    @pytest.mark.unit
    def test_start_logging(self, logger: StatsLogger) -> None:
        """Test starting periodic logging."""
        with patch("app.stats.logger.LoopingCall") as mock_looping_call:
            mock_task = Mock()
            mock_looping_call.return_value = mock_task

            logger.start()

        mock_looping_call.assert_called_once_with(logger._log_periodic_stats)
        mock_task.start.assert_called_once_with(1)
        assert logger._is_running is True
        assert logger._logging_task is mock_task

    @pytest.mark.unit
    def test_start_already_running(self, logger: StatsLogger) -> None:
        """Test starting when already running."""
        logger._is_running = True

        with patch("app.stats.logger.LoopingCall") as mock_looping_call:
            logger.start()

        mock_looping_call.assert_not_called()

    @pytest.mark.unit
    def test_start_exception_handling(self, logger: StatsLogger) -> None:
        """Test exception handling during start."""
        with patch("app.stats.logger.LoopingCall") as mock_looping_call:
            mock_looping_call.side_effect = Exception("Test error")

            with pytest.raises(Exception, match="Test error"):
                logger.start()

    @pytest.mark.unit
    def test_stop_logging(self, logger: StatsLogger) -> None:
        """Test stopping periodic logging."""
        # Set up running state
        mock_task = Mock()
        mock_task.running = True
        logger._logging_task = mock_task
        logger._is_running = True

        logger.stop()

        mock_task.stop.assert_called_once()
        assert logger._is_running is False

    @pytest.mark.unit
    def test_stop_not_running(self, logger: StatsLogger) -> None:
        """Test stopping when not running."""
        assert logger._is_running is False

        logger.stop()  # Should not raise any exceptions

    @pytest.mark.unit
    def test_stop_task_not_running(self, logger: StatsLogger) -> None:
        """Test stopping when task exists but not running."""
        mock_task = Mock()
        mock_task.running = False
        logger._logging_task = mock_task
        logger._is_running = True

        logger.stop()

        mock_task.stop.assert_not_called()
        assert logger._is_running is False

    @pytest.mark.unit
    def test_stop_exception_handling(self, logger: StatsLogger) -> None:
        """Test exception handling during stop."""
        mock_task = Mock()
        mock_task.running = True
        mock_task.stop.side_effect = Exception("Stop error")
        logger._logging_task = mock_task
        logger._is_running = True

        # Should not raise exception, but _is_running stays True due to exception
        logger.stop()
        assert logger._is_running is True  # Exception prevents setting to False


class TestImmediateLogging:
    """Test immediate logging functionality."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def logger(self, mock_collector: Mock) -> StatsLogger:
        """Create StatsLogger with mocked dependencies."""
        with patch("app.stats.logger.LoggingConfig"):
            return StatsLogger(mock_collector)

    @pytest.mark.unit
    def test_log_current_stats_success(self, logger: StatsLogger) -> None:
        """Test successful immediate stats logging."""
        mock_stats = Mock(spec=ApplicationStats)
        logger.stats_collector.get_stats.return_value = mock_stats

        with patch.object(logger, "_log_stats") as mock_log_stats:
            logger.log_current_stats()

        logger.stats_collector.get_stats.assert_called_once()
        mock_log_stats.assert_called_once_with(mock_stats)

    @pytest.mark.unit
    def test_log_current_stats_exception(self, logger: StatsLogger) -> None:
        """Test exception handling in immediate logging."""
        logger.stats_collector.get_stats.side_effect = Exception("Get stats error")

        # Should not raise exception
        logger.log_current_stats()


class TestPeriodicLogging:
    """Test periodic logging functionality."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def logger(self, mock_collector: Mock) -> StatsLogger:
        """Create StatsLogger with mocked dependencies."""
        with patch("app.stats.logger.LoggingConfig"):
            return StatsLogger(mock_collector)

    @pytest.fixture
    def sample_stats(self) -> ApplicationStats:
        """Create sample ApplicationStats for testing."""
        stats = ApplicationStats()
        stats.connection.is_connected = True
        stats.connection.total_connections = 5
        stats.messages.total_received = 100
        stats.messages.total_processed = 95
        stats.messages.total_failed = 5
        return stats

    @pytest.mark.unit
    def test_log_periodic_stats_success(self, logger: StatsLogger, sample_stats: ApplicationStats) -> None:
        """Test successful periodic stats logging."""
        logger.stats_collector.get_stats.return_value = sample_stats

        with patch.object(logger, "_log_stats") as mock_log_stats:
            with patch("app.stats.logger.datetime") as mock_datetime:
                mock_datetime.utcnow.return_value = datetime.utcnow()

                logger._log_periodic_stats()

        logger.stats_collector.get_stats.assert_called_once()
        mock_log_stats.assert_called_once_with(sample_stats)

        # Verify snapshot was stored
        assert len(logger._snapshots) == 1
        assert logger._snapshots[0].stats == sample_stats

    @pytest.mark.unit
    def test_log_periodic_stats_snapshot_management(self, logger: StatsLogger, sample_stats: ApplicationStats) -> None:
        """Test snapshot management in periodic logging."""
        logger.stats_collector.get_stats.return_value = sample_stats

        # Add more snapshots than max_snapshots
        with patch.object(logger, "_log_stats"):
            with patch("app.stats.logger.datetime") as mock_datetime:
                mock_datetime.utcnow.return_value = datetime.utcnow()

                # Add 12 snapshots (more than max of 10)
                for _ in range(12):
                    logger._log_periodic_stats()

        # Should only keep the last 10
        assert len(logger._snapshots) == logger._max_snapshots

    @pytest.mark.unit
    def test_log_periodic_stats_exception(self, logger: StatsLogger) -> None:
        """Test exception handling in periodic logging."""
        logger.stats_collector.get_stats.side_effect = Exception("Periodic error")

        # Should not raise exception
        logger._log_periodic_stats()


class TestStatsFormatting:
    """Test statistics formatting and display."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def logger(self, mock_collector: Mock) -> StatsLogger:
        """Create StatsLogger with mocked dependencies."""
        with patch("app.stats.logger.LoggingConfig"):
            return StatsLogger(mock_collector)

    @pytest.fixture
    def complete_stats(self) -> ApplicationStats:
        """Create complete ApplicationStats for testing."""
        stats = ApplicationStats()

        # Connection stats
        stats.connection.is_connected = True
        stats.connection.total_connections = 3
        stats.connection.reconnect_attempts = 1
        stats.connection.outstanding_pings = 2

        # Message stats
        stats.messages.total_received = 1000
        stats.messages.total_processed = 950
        stats.messages.total_failed = 50

        # Output handlers
        mqtt_handler = OutputHandlerStats(
            handler_type="mqtt", total_published=475, total_failed=25, is_connected=True, connection_errors=2
        )
        console_handler = OutputHandlerStats(
            handler_type="console", total_published=470, total_failed=0, is_connected=True, connection_errors=0
        )

        stats.output_handlers["mqtt_primary"] = mqtt_handler
        stats.output_handlers["console"] = console_handler

        return stats

    @pytest.mark.unit
    def test_log_stats_formatting(self, logger: StatsLogger, complete_stats: ApplicationStats) -> None:
        """Test complete stats formatting and logging."""
        with patch.object(logger, "_calculate_rates", return_value={"messages_per_minute": 10.5, "processing_per_minute": 9.8}):
            with patch.object(logger, "_format_duration", side_effect=lambda x: f"{x:.0f}s"):
                with patch("app.stats.logger.logger") as mock_logger:
                    logger._log_stats(complete_stats)

        # Verify logging calls were made
        assert mock_logger.info.call_count >= 3  # At least app stats, message stats, and handler stats

    @pytest.mark.unit
    def test_calculate_rates_no_snapshots(self, logger: StatsLogger) -> None:
        """Test rate calculation with no snapshots."""
        rates = logger._calculate_rates()
        assert rates == {}

    @pytest.mark.unit
    def test_calculate_rates_insufficient_snapshots(self, logger: StatsLogger) -> None:
        """Test rate calculation with only one snapshot."""
        # Add one snapshot
        snapshot = StatsSnapshot(timestamp=datetime.utcnow(), stats=ApplicationStats())
        logger._snapshots.append(snapshot)

        rates = logger._calculate_rates()
        assert rates == {}

    @pytest.mark.unit
    def test_calculate_rates_success(self, logger: StatsLogger) -> None:
        """Test successful rate calculation."""
        now = datetime.utcnow()

        # Create old snapshot
        old_stats = ApplicationStats()
        old_stats.messages.total_received = 100
        old_stats.messages.total_processed = 95
        old_snapshot = StatsSnapshot(timestamp=now - timedelta(minutes=1), stats=old_stats)

        # Create new snapshot
        new_stats = ApplicationStats()
        new_stats.messages.total_received = 160
        new_stats.messages.total_processed = 152
        new_snapshot = StatsSnapshot(timestamp=now, stats=new_stats)

        logger._snapshots = [old_snapshot, new_snapshot]

        rates = logger._calculate_rates()

        assert "messages_per_minute" in rates
        assert "processing_per_minute" in rates
        assert rates["messages_per_minute"] == 60.0  # 60 messages per minute
        assert rates["processing_per_minute"] == 57.0  # 57 processed per minute

    @pytest.mark.unit
    def test_calculate_rates_zero_time_diff(self, logger: StatsLogger) -> None:
        """Test rate calculation with zero time difference."""
        now = datetime.utcnow()

        # Create snapshots with same timestamp
        old_snapshot = StatsSnapshot(timestamp=now, stats=ApplicationStats())
        new_snapshot = StatsSnapshot(timestamp=now, stats=ApplicationStats())

        logger._snapshots = [old_snapshot, new_snapshot]

        rates = logger._calculate_rates()
        assert rates == {}

    @pytest.mark.unit
    def test_format_duration_seconds(self, logger: StatsLogger) -> None:
        """Test duration formatting for seconds."""
        assert logger._format_duration(30) == "30s"
        assert logger._format_duration(59.9) == "60s"

    @pytest.mark.unit
    def test_format_duration_minutes(self, logger: StatsLogger) -> None:
        """Test duration formatting for minutes."""
        assert logger._format_duration(90) == "1.5m"
        assert logger._format_duration(150) == "2.5m"

    @pytest.mark.unit
    def test_format_duration_hours(self, logger: StatsLogger) -> None:
        """Test duration formatting for hours."""
        assert logger._format_duration(3600) == "1.0h"
        assert logger._format_duration(7200) == "2.0h"
        assert logger._format_duration(5400) == "1.5h"

    @pytest.mark.unit
    def test_format_duration_days(self, logger: StatsLogger) -> None:
        """Test duration formatting for days."""
        assert logger._format_duration(86400) == "1.0d"
        assert logger._format_duration(172800) == "2.0d"
        assert logger._format_duration(129600) == "1.5d"


class TestSnapshotManagement:
    """Test snapshot storage and management."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def logger(self, mock_collector: Mock) -> StatsLogger:
        """Create StatsLogger with mocked dependencies."""
        with patch("app.stats.logger.LoggingConfig"):
            return StatsLogger(mock_collector)

    @pytest.mark.unit
    def test_snapshot_storage_within_limit(self, logger: StatsLogger) -> None:
        """Test snapshot storage within max limit."""
        with patch.object(logger, "_log_stats"):
            with patch("app.stats.logger.datetime") as mock_datetime:
                mock_datetime.utcnow.return_value = datetime.utcnow()

                logger.stats_collector.get_stats.return_value = ApplicationStats()

                # Add 5 snapshots (within limit)
                for _ in range(5):
                    logger._log_periodic_stats()

        assert len(logger._snapshots) == 5

    @pytest.mark.unit
    def test_snapshot_storage_exceeds_limit(self, logger: StatsLogger) -> None:
        """Test snapshot storage exceeding max limit."""
        with patch.object(logger, "_log_stats"):
            with patch("app.stats.logger.datetime") as mock_datetime:
                mock_datetime.utcnow.return_value = datetime.utcnow()

                logger.stats_collector.get_stats.return_value = ApplicationStats()

                # Add more than max_snapshots
                for _ in range(15):
                    logger._log_periodic_stats()

        assert len(logger._snapshots) == logger._max_snapshots

    @pytest.mark.unit
    def test_snapshot_ordering(self, logger: StatsLogger) -> None:
        """Test that snapshots maintain chronological order."""
        timestamps = []

        with patch.object(logger, "_log_stats"):
            with patch("app.stats.logger.datetime") as mock_datetime:
                logger.stats_collector.get_stats.return_value = ApplicationStats()

                # Add snapshots with different timestamps
                for i in range(5):
                    timestamp = datetime.utcnow() + timedelta(minutes=i)
                    timestamps.append(timestamp)
                    mock_datetime.utcnow.return_value = timestamp
                    logger._log_periodic_stats()

        # Verify snapshots are in chronological order
        for i in range(len(logger._snapshots)):
            assert logger._snapshots[i].timestamp == timestamps[i]


class TestComplexScenarios:
    """Test complex logging scenarios."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def logger(self, mock_collector: Mock) -> StatsLogger:
        """Create StatsLogger with mocked dependencies."""
        with patch("app.stats.logger.LoggingConfig"):
            return StatsLogger(mock_collector, log_interval_seconds=1)

    @pytest.mark.unit
    def test_full_lifecycle_with_logging(self, logger: StatsLogger) -> None:
        """Test complete lifecycle including actual logging."""
        # Create realistic stats
        stats = ApplicationStats()
        stats.connection.is_connected = True
        stats.messages.total_received = 500
        stats.messages.total_processed = 475
        stats.output_handlers["mqtt"] = OutputHandlerStats(handler_type="mqtt", total_published=237, is_connected=True)

        logger.stats_collector.get_stats.return_value = stats

        # Test immediate logging
        with patch("app.stats.logger.logger"):
            logger.log_current_stats()

        # Test periodic logging
        with patch("app.stats.logger.logger"):
            logger._log_periodic_stats()

        assert len(logger._snapshots) == 1

    @pytest.mark.unit
    def test_rate_calculation_with_realistic_data(self, logger: StatsLogger) -> None:
        """Test rate calculation with realistic message flow."""
        base_time = datetime.utcnow()

        # Simulate 5 minutes of snapshots
        for minute in range(5):
            stats = ApplicationStats()
            stats.messages.total_received = 100 * (minute + 1)
            stats.messages.total_processed = 95 * (minute + 1)

            snapshot = StatsSnapshot(timestamp=base_time + timedelta(minutes=minute), stats=stats)
            logger._snapshots.append(snapshot)

        # Keep only last 10 (should keep all 5)
        if len(logger._snapshots) > logger._max_snapshots:
            logger._snapshots = logger._snapshots[-logger._max_snapshots :]

        rates = logger._calculate_rates()

        # Should calculate rate based on most recent minute
        assert "messages_per_minute" in rates
        assert "processing_per_minute" in rates
        assert rates["messages_per_minute"] == 100.0
        assert rates["processing_per_minute"] == 95.0
