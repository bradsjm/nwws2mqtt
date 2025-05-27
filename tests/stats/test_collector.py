"""Unit tests for StatsCollector."""

from datetime import datetime
from unittest.mock import patch

import pytest

from app.stats.collector import StatsCollector
from app.stats.statistic_models import ApplicationStats, OutputHandlerStats


class TestStatsCollectorInitialization:
    """Test StatsCollector initialization."""

    @pytest.mark.unit
    def test_initialization(self) -> None:
        """Test StatsCollector initialization."""
        with patch("app.stats.collector.LoggingConfig"):
            collector = StatsCollector()

        assert collector._stats is not None
        assert isinstance(collector._stats, ApplicationStats)
        assert collector._lock is not None

    @pytest.mark.unit
    def test_get_stats_returns_copy(self) -> None:
        """Test that get_stats returns a deep copy."""
        with patch("app.stats.collector.LoggingConfig"):
            collector = StatsCollector()

        # Modify original stats
        collector._stats.messages.total_received = 100

        # Get stats copy
        stats_copy = collector.get_stats()

        # Modify original again
        collector._stats.messages.total_received = 200

        # Copy should remain unchanged
        assert stats_copy.messages.total_received == 100
        assert collector._stats.messages.total_received == 200

    @pytest.mark.unit
    def test_get_stats_deep_copy_structure(self) -> None:
        """Test that get_stats creates proper deep copy of nested structures."""
        with patch("app.stats.collector.LoggingConfig"):
            collector = StatsCollector()

        # Add complex data
        collector._stats.messages.product_types["FXUS61"] = 50
        collector._stats.output_handlers["mqtt"] = OutputHandlerStats(handler_type="mqtt")

        # Get copy
        stats_copy = collector.get_stats()

        # Modify original nested data
        collector._stats.messages.product_types["FXUS61"] = 100
        collector._stats.output_handlers["mqtt"].total_published = 25

        # Copy should be unchanged
        assert stats_copy.messages.product_types["FXUS61"] == 50
        assert stats_copy.output_handlers["mqtt"].total_published == 0


class TestConnectionTracking:
    """Test connection tracking methods."""

    @pytest.fixture
    def collector(self) -> StatsCollector:
        """Create StatsCollector instance for testing."""
        with patch("app.stats.collector.LoggingConfig"):
            return StatsCollector()

    @pytest.mark.unit
    def test_on_connection_attempt(self, collector: StatsCollector) -> None:
        """Test recording connection attempt."""
        # Method exists but currently only logs
        collector.on_connection_attempt()
        # No assertion needed as method currently only logs

    @pytest.mark.unit
    def test_on_connected(self, collector: StatsCollector) -> None:
        """Test recording successful connection."""
        with patch("app.stats.collector.datetime") as mock_datetime:
            test_time = datetime.utcnow()
            mock_datetime.utcnow.return_value = test_time

            collector.on_connected()

        stats = collector.get_stats()
        assert stats.connection.connected_at == test_time
        assert stats.connection.disconnected_at is None
        assert stats.connection.total_connections == 1
        assert stats.connection.is_connected is True

    @pytest.mark.unit
    def test_on_disconnected(self, collector: StatsCollector) -> None:
        """Test recording disconnection."""
        # First connect
        collector.on_connected()

        # Then disconnect
        with patch("app.stats.collector.datetime") as mock_datetime:
            test_time = datetime.utcnow()
            mock_datetime.utcnow.return_value = test_time

            collector.on_disconnected()

        stats = collector.get_stats()
        assert stats.connection.disconnected_at == test_time
        assert stats.connection.total_disconnections == 1
        assert stats.connection.is_connected is False

    @pytest.mark.unit
    def test_on_reconnect_attempt(self, collector: StatsCollector) -> None:
        """Test recording reconnection attempt."""
        collector.on_reconnect_attempt()

        stats = collector.get_stats()
        assert stats.connection.reconnect_attempts == 1

    @pytest.mark.unit
    def test_on_auth_failure(self, collector: StatsCollector) -> None:
        """Test recording authentication failure."""
        collector.on_auth_failure()

        stats = collector.get_stats()
        assert stats.connection.auth_failures == 1

    @pytest.mark.unit
    def test_on_connection_error(self, collector: StatsCollector) -> None:
        """Test recording connection error."""
        collector.on_connection_error()

        stats = collector.get_stats()
        assert stats.connection.connection_errors == 1

    @pytest.mark.unit
    def test_on_ping_sent(self, collector: StatsCollector) -> None:
        """Test recording ping sent."""
        with patch("app.stats.collector.datetime") as mock_datetime:
            test_time = datetime.utcnow()
            mock_datetime.utcnow.return_value = test_time

            collector.on_ping_sent()

        stats = collector.get_stats()
        assert stats.connection.last_ping_sent == test_time
        assert stats.connection.outstanding_pings == 1

    @pytest.mark.unit
    def test_on_pong_received(self, collector: StatsCollector) -> None:
        """Test recording pong received."""
        # First send a ping to have outstanding pings
        collector.on_ping_sent()

        with patch("app.stats.collector.datetime") as mock_datetime:
            test_time = datetime.utcnow()
            mock_datetime.utcnow.return_value = test_time

            collector.on_pong_received()

        stats = collector.get_stats()
        assert stats.connection.last_pong_received == test_time
        assert stats.connection.outstanding_pings == 0

    @pytest.mark.unit
    def test_on_pong_received_no_outstanding_pings(self, collector: StatsCollector) -> None:
        """Test recording pong when no pings are outstanding."""
        collector.on_pong_received()

        stats = collector.get_stats()
        assert stats.connection.outstanding_pings == 0

    @pytest.mark.unit
    def test_multiple_connection_events(self, collector: StatsCollector) -> None:
        """Test multiple connection events."""
        # Multiple connection attempts and failures
        collector.on_connection_attempt()
        collector.on_connection_error()
        collector.on_reconnect_attempt()
        collector.on_connected()
        collector.on_disconnected()
        collector.on_reconnect_attempt()
        collector.on_auth_failure()
        collector.on_connected()

        stats = collector.get_stats()
        assert stats.connection.total_connections == 2
        assert stats.connection.total_disconnections == 1
        assert stats.connection.reconnect_attempts == 2
        assert stats.connection.auth_failures == 1
        assert stats.connection.connection_errors == 1
        assert stats.connection.is_connected is True


class TestMessageTracking:
    """Test message tracking methods."""

    @pytest.fixture
    def collector(self) -> StatsCollector:
        """Create StatsCollector instance for testing."""
        with patch("app.stats.collector.LoggingConfig"):
            return StatsCollector()

    @pytest.mark.unit
    def test_on_message_received(self, collector: StatsCollector) -> None:
        """Test recording message received."""
        with patch("app.stats.collector.datetime") as mock_datetime:
            test_time = datetime.utcnow()
            mock_datetime.utcnow.return_value = test_time

            collector.on_message_received()

        stats = collector.get_stats()
        assert stats.messages.total_received == 1
        assert stats.messages.last_message_time == test_time

    @pytest.mark.unit
    def test_on_groupchat_message_received(self, collector: StatsCollector) -> None:
        """Test recording groupchat message received."""
        with patch("app.stats.collector.datetime") as mock_datetime:
            test_time = datetime.utcnow()
            mock_datetime.utcnow.return_value = test_time

            collector.on_groupchat_message_received()

        stats = collector.get_stats()
        assert stats.messages.last_groupchat_message_time == test_time

    @pytest.mark.unit
    def test_on_message_processed(self, collector: StatsCollector) -> None:
        """Test recording message processed with all parameters."""
        collector.on_message_processed(source="NWWS-OI", afos="AFGAFC", product_id="FXUS61KBOU")

        stats = collector.get_stats()
        assert stats.messages.total_processed == 1
        assert stats.messages.sources["NWWS-OI"] == 1
        assert stats.messages.afos_codes["AFGAFC"] == 1
        assert stats.messages.product_types["FXUS61"] == 1

    @pytest.mark.unit
    def test_on_message_processed_short_product_id(self, collector: StatsCollector) -> None:
        """Test message processed with short product ID."""
        collector.on_message_processed(source="NWWS-OI", afos="AFGAFC", product_id="FX")

        stats = collector.get_stats()
        assert stats.messages.product_types["FX"] == 1

    @pytest.mark.unit
    def test_on_message_processed_no_product_id(self, collector: StatsCollector) -> None:
        """Test message processed without product ID."""
        collector.on_message_processed(source="NWWS-OI", afos="AFGAFC")

        stats = collector.get_stats()
        assert stats.messages.total_processed == 1
        assert stats.messages.sources["NWWS-OI"] == 1
        assert stats.messages.afos_codes["AFGAFC"] == 1
        assert len(stats.messages.product_types) == 0

    @pytest.mark.unit
    def test_on_message_processed_empty_values(self, collector: StatsCollector) -> None:
        """Test message processed with empty values."""
        collector.on_message_processed(source="", afos="", product_id="")

        stats = collector.get_stats()
        assert stats.messages.total_processed == 1
        # Empty strings should not increment counters
        assert len(stats.messages.sources) == 0
        assert len(stats.messages.afos_codes) == 0
        assert len(stats.messages.product_types) == 0

    @pytest.mark.unit
    def test_on_message_failed(self, collector: StatsCollector) -> None:
        """Test recording message processing failure."""
        collector.on_message_failed("parse_error")

        stats = collector.get_stats()
        assert stats.messages.total_failed == 1
        assert stats.messages.processing_errors["parse_error"] == 1

    @pytest.mark.unit
    def test_on_message_published(self, collector: StatsCollector) -> None:
        """Test recording message published."""
        collector.on_message_published()

        stats = collector.get_stats()
        assert stats.messages.total_published == 1

    @pytest.mark.unit
    def test_multiple_message_events(self, collector: StatsCollector) -> None:
        """Test multiple message processing events."""
        # Process various messages
        collector.on_message_received()
        collector.on_message_received()
        collector.on_message_processed("NWWS-OI", "AFGAFC", "FXUS61KBOU")
        collector.on_message_processed("NWWS-OI", "URGENT", "FXUS62KDEN")
        collector.on_message_failed("timeout")
        collector.on_message_published()
        collector.on_message_published()

        stats = collector.get_stats()
        assert stats.messages.total_received == 2
        assert stats.messages.total_processed == 2
        assert stats.messages.total_failed == 1
        assert stats.messages.total_published == 2
        assert stats.messages.sources["NWWS-OI"] == 2
        assert stats.messages.afos_codes["AFGAFC"] == 1
        assert stats.messages.afos_codes["URGENT"] == 1
        assert stats.messages.product_types["FXUS61"] == 1
        assert stats.messages.product_types["FXUS62"] == 1
        assert stats.messages.processing_errors["timeout"] == 1


class TestOutputHandlerTracking:
    """Test output handler tracking methods."""

    @pytest.fixture
    def collector(self) -> StatsCollector:
        """Create StatsCollector instance for testing."""
        with patch("app.stats.collector.LoggingConfig"):
            return StatsCollector()

    @pytest.mark.unit
    def test_register_output_handler(self, collector: StatsCollector) -> None:
        """Test registering output handler."""
        collector.register_output_handler("mqtt_primary", "mqtt")

        stats = collector.get_stats()
        assert "mqtt_primary" in stats.output_handlers
        assert stats.output_handlers["mqtt_primary"].handler_type == "mqtt"

    @pytest.mark.unit
    def test_register_duplicate_handler(self, collector: StatsCollector) -> None:
        """Test registering same handler twice."""
        collector.register_output_handler("mqtt_primary", "mqtt")
        collector.register_output_handler("mqtt_primary", "mqtt")

        stats = collector.get_stats()
        assert len(stats.output_handlers) == 1

    @pytest.mark.unit
    def test_on_handler_connected(self, collector: StatsCollector) -> None:
        """Test recording handler connection."""
        collector.register_output_handler("mqtt_primary", "mqtt")

        with patch("app.stats.collector.datetime") as mock_datetime:
            test_time = datetime.utcnow()
            mock_datetime.utcnow.return_value = test_time

            collector.on_handler_connected("mqtt_primary")

        stats = collector.get_stats()
        handler_stats = stats.output_handlers["mqtt_primary"]
        assert handler_stats.connected_at == test_time
        assert handler_stats.disconnected_at is None
        assert handler_stats.is_connected is True

    @pytest.mark.unit
    def test_on_handler_connected_unregistered(self, collector: StatsCollector) -> None:
        """Test connecting unregistered handler."""
        collector.on_handler_connected("unknown_handler")

        stats = collector.get_stats()
        assert "unknown_handler" not in stats.output_handlers

    @pytest.mark.unit
    def test_on_handler_disconnected(self, collector: StatsCollector) -> None:
        """Test recording handler disconnection."""
        collector.register_output_handler("mqtt_primary", "mqtt")
        collector.on_handler_connected("mqtt_primary")

        with patch("app.stats.collector.datetime") as mock_datetime:
            test_time = datetime.utcnow()
            mock_datetime.utcnow.return_value = test_time

            collector.on_handler_disconnected("mqtt_primary")

        stats = collector.get_stats()
        handler_stats = stats.output_handlers["mqtt_primary"]
        assert handler_stats.disconnected_at == test_time
        assert handler_stats.is_connected is False

    @pytest.mark.unit
    def test_on_handler_publish_success(self, collector: StatsCollector) -> None:
        """Test recording successful handler publish."""
        collector.register_output_handler("mqtt_primary", "mqtt")

        with patch("app.stats.collector.datetime") as mock_datetime:
            test_time = datetime.utcnow()
            mock_datetime.utcnow.return_value = test_time

            collector.on_handler_publish_success("mqtt_primary")

        stats = collector.get_stats()
        handler_stats = stats.output_handlers["mqtt_primary"]
        assert handler_stats.total_published == 1
        assert handler_stats.last_publish_time == test_time

    @pytest.mark.unit
    def test_on_handler_publish_failed(self, collector: StatsCollector) -> None:
        """Test recording failed handler publish."""
        collector.register_output_handler("mqtt_primary", "mqtt")

        collector.on_handler_publish_failed("mqtt_primary")

        stats = collector.get_stats()
        handler_stats = stats.output_handlers["mqtt_primary"]
        assert handler_stats.total_failed == 1

    @pytest.mark.unit
    def test_on_handler_connection_error(self, collector: StatsCollector) -> None:
        """Test recording handler connection error."""
        collector.register_output_handler("mqtt_primary", "mqtt")

        collector.on_handler_connection_error("mqtt_primary")

        stats = collector.get_stats()
        handler_stats = stats.output_handlers["mqtt_primary"]
        assert handler_stats.connection_errors == 1

    @pytest.mark.unit
    def test_multiple_handlers(self, collector: StatsCollector) -> None:
        """Test tracking multiple output handlers."""
        # Register multiple handlers
        collector.register_output_handler("mqtt_primary", "mqtt")
        collector.register_output_handler("console", "console")
        collector.register_output_handler("mqtt_secondary", "mqtt")

        # Simulate various events
        collector.on_handler_connected("mqtt_primary")
        collector.on_handler_connected("console")
        collector.on_handler_publish_success("mqtt_primary")
        collector.on_handler_publish_success("console")
        collector.on_handler_publish_failed("mqtt_secondary")
        collector.on_handler_connection_error("mqtt_secondary")

        stats = collector.get_stats()
        assert len(stats.output_handlers) == 3

        # Check mqtt_primary
        mqtt_primary = stats.output_handlers["mqtt_primary"]
        assert mqtt_primary.is_connected is True
        assert mqtt_primary.total_published == 1
        assert mqtt_primary.total_failed == 0

        # Check console
        console = stats.output_handlers["console"]
        assert console.is_connected is True
        assert console.total_published == 1

        # Check mqtt_secondary
        mqtt_secondary = stats.output_handlers["mqtt_secondary"]
        assert mqtt_secondary.is_connected is False
        assert mqtt_secondary.total_failed == 1
        assert mqtt_secondary.connection_errors == 1


class TestStatsReset:
    """Test statistics reset functionality."""

    @pytest.fixture
    def collector(self) -> StatsCollector:
        """Create StatsCollector instance for testing."""
        with patch("app.stats.collector.LoggingConfig"):
            return StatsCollector()

    @pytest.mark.unit
    def test_reset_stats(self, collector: StatsCollector) -> None:
        """Test resetting all statistics."""
        # Populate with data
        collector.on_connected()
        collector.on_message_received()
        collector.on_message_processed("NWWS-OI", "AFGAFC", "FXUS61KBOU")
        collector.register_output_handler("mqtt", "mqtt")
        collector.on_handler_publish_success("mqtt")

        # Verify data exists
        stats = collector.get_stats()
        assert stats.connection.total_connections == 1
        assert stats.messages.total_received == 1
        assert len(stats.output_handlers) == 1

        # Reset
        collector.reset_stats()

        # Verify reset
        reset_stats = collector.get_stats()
        assert reset_stats.connection.total_connections == 0
        assert reset_stats.messages.total_received == 0
        assert len(reset_stats.output_handlers) == 0
        assert isinstance(reset_stats, ApplicationStats)


class TestThreadSafety:
    """Test thread safety of StatsCollector."""

    @pytest.fixture
    def collector(self) -> StatsCollector:
        """Create StatsCollector instance for testing."""
        with patch("app.stats.collector.LoggingConfig"):
            return StatsCollector()

    @pytest.mark.unit
    def test_concurrent_access_simulation(self, collector: StatsCollector) -> None:
        """Test that concurrent-like access works correctly."""
        import threading
        import time

        results = []

        def worker_function():
            """Simulate concurrent stats operations."""
            for i in range(10):
                collector.on_message_received()
                collector.on_message_processed("NWWS-OI", f"AFOS{i}", f"PROD{i}")
                time.sleep(0.001)  # Small delay to simulate processing
                stats = collector.get_stats()
                results.append(stats.messages.total_received)

        # Run multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=worker_function)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify final state
        final_stats = collector.get_stats()
        assert final_stats.messages.total_received == 30
        assert final_stats.messages.total_processed == 30

        # Verify all intermediate results were valid
        assert all(isinstance(result, int) and result > 0 for result in results)
