"""Unit tests for StatsConsumer."""

from unittest.mock import Mock, patch

import pytest

from app.messaging import Topics
from app.stats.collector import StatsCollector
from app.stats.consumer import StatsConsumer


class TestStatsConsumerInitialization:
    """Test StatsConsumer initialization."""

    @pytest.mark.unit
    def test_initialization(self) -> None:
        """Test StatsConsumer initialization."""
        with patch("app.stats.consumer.LoggingConfig"):
            mock_collector = Mock(spec=StatsCollector)
            consumer = StatsConsumer(mock_collector)

        assert consumer.stats_collector is mock_collector
        assert consumer._subscribed is False

    @pytest.mark.unit
    def test_is_subscribed_property(self) -> None:
        """Test is_subscribed property."""
        with patch("app.stats.consumer.LoggingConfig"):
            mock_collector = Mock(spec=StatsCollector)
            consumer = StatsConsumer(mock_collector)

        assert consumer.is_subscribed is False

        consumer._subscribed = True
        assert consumer.is_subscribed is True


class TestSubscriptionLifecycle:
    """Test subscription lifecycle methods."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def consumer(self, mock_collector: Mock) -> StatsConsumer:
        """Create StatsConsumer with mocked dependencies."""
        with patch("app.stats.consumer.LoggingConfig"):
            return StatsConsumer(mock_collector)

    @pytest.mark.unit
    def test_start_subscribes_to_all_topics(self, consumer: StatsConsumer) -> None:
        """Test that start subscribes to all required topics."""
        with patch("app.stats.consumer.MessageBus") as mock_bus:
            consumer.start()

        # Verify subscription calls were made
        expected_topics = [
            Topics.STATS_CONNECTION_ATTEMPT,
            Topics.STATS_CONNECTION_ESTABLISHED,
            Topics.STATS_CONNECTION_LOST,
            Topics.STATS_RECONNECT_ATTEMPT,
            Topics.STATS_AUTH_FAILURE,
            Topics.STATS_CONNECTION_ERROR,
            Topics.STATS_PING_SENT,
            Topics.STATS_PONG_RECEIVED,
            Topics.XMPP_CONNECTED,
            Topics.XMPP_DISCONNECTED,
            Topics.STATS_MESSAGE_RECEIVED,
            Topics.STATS_GROUPCHAT_MESSAGE_RECEIVED,
            Topics.STATS_MESSAGE_PROCESSED,
            Topics.STATS_MESSAGE_FAILED,
            Topics.STATS_MESSAGE_PUBLISHED,
            Topics.STATS_HANDLER_REGISTERED,
            Topics.STATS_HANDLER_CONNECTED,
            Topics.STATS_HANDLER_DISCONNECTED,
            Topics.STATS_HANDLER_PUBLISH_SUCCESS,
            Topics.STATS_HANDLER_PUBLISH_FAILED,
            Topics.STATS_HANDLER_CONNECTION_ERROR,
        ]

        # Check that subscribe was called for each topic
        assert mock_bus.subscribe.call_count == len(expected_topics)

        # Verify consumer is marked as subscribed
        assert consumer.is_subscribed is True

    @pytest.mark.unit
    def test_start_already_subscribed_warning(self, consumer: StatsConsumer) -> None:
        """Test start when already subscribed logs warning."""
        consumer._subscribed = True

        with patch("app.stats.consumer.MessageBus") as mock_bus:
            consumer.start()

        # Should not make any subscription calls
        mock_bus.subscribe.assert_not_called()

    @pytest.mark.unit
    def test_stop_unsubscribes_from_all_topics(self, consumer: StatsConsumer) -> None:
        """Test that stop unsubscribes from all topics."""
        # Start first to set subscribed state
        with patch("app.stats.consumer.MessageBus"):
            consumer.start()

        # Now test stop
        with patch("app.stats.consumer.MessageBus") as mock_bus:
            consumer.stop()

        expected_topics = [
            Topics.STATS_CONNECTION_ATTEMPT,
            Topics.STATS_CONNECTION_ESTABLISHED,
            Topics.STATS_CONNECTION_LOST,
            Topics.STATS_RECONNECT_ATTEMPT,
            Topics.STATS_AUTH_FAILURE,
            Topics.STATS_CONNECTION_ERROR,
            Topics.STATS_PING_SENT,
            Topics.STATS_PONG_RECEIVED,
            Topics.XMPP_CONNECTED,
            Topics.XMPP_DISCONNECTED,
            Topics.STATS_MESSAGE_RECEIVED,
            Topics.STATS_GROUPCHAT_MESSAGE_RECEIVED,
            Topics.STATS_MESSAGE_PROCESSED,
            Topics.STATS_MESSAGE_FAILED,
            Topics.STATS_MESSAGE_PUBLISHED,
            Topics.STATS_HANDLER_REGISTERED,
            Topics.STATS_HANDLER_CONNECTED,
            Topics.STATS_HANDLER_DISCONNECTED,
            Topics.STATS_HANDLER_PUBLISH_SUCCESS,
            Topics.STATS_HANDLER_PUBLISH_FAILED,
            Topics.STATS_HANDLER_CONNECTION_ERROR,
        ]

        # Check that unsubscribe was called for each topic
        assert mock_bus.unsubscribe.call_count == len(expected_topics)

        # Verify consumer is marked as not subscribed
        assert consumer.is_subscribed is False

    @pytest.mark.unit
    def test_stop_not_subscribed(self, consumer: StatsConsumer) -> None:
        """Test stop when not subscribed does nothing."""
        assert consumer.is_subscribed is False

        with patch("app.stats.consumer.MessageBus") as mock_bus:
            consumer.stop()

        # Should not make any unsubscription calls
        mock_bus.unsubscribe.assert_not_called()


class TestConnectionEventHandlers:
    """Test connection event handlers."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def consumer(self, mock_collector: Mock) -> StatsConsumer:
        """Create StatsConsumer with mocked dependencies."""
        with patch("app.stats.consumer.LoggingConfig"):
            return StatsConsumer(mock_collector)

    @pytest.fixture
    def mock_connection_message(self) -> Mock:
        """Create mock StatsConnectionMessage."""
        return Mock()

    @pytest.mark.unit
    def test_on_connection_attempt(
        self, consumer: StatsConsumer, mock_connection_message: Mock
    ) -> None:
        """Test connection attempt handler."""
        consumer._on_connection_attempt(mock_connection_message)
        consumer.stats_collector.on_connection_attempt.assert_called_once()

    @pytest.mark.unit
    def test_on_connection_established(
        self, consumer: StatsConsumer, mock_connection_message: Mock
    ) -> None:
        """Test connection established handler."""
        consumer._on_connection_established(mock_connection_message)
        consumer.stats_collector.on_connected.assert_called_once()

    @pytest.mark.unit
    def test_on_connection_lost(
        self, consumer: StatsConsumer, mock_connection_message: Mock
    ) -> None:
        """Test connection lost handler."""
        consumer._on_connection_lost(mock_connection_message)
        consumer.stats_collector.on_disconnected.assert_called_once()

    @pytest.mark.unit
    def test_on_reconnect_attempt(
        self, consumer: StatsConsumer, mock_connection_message: Mock
    ) -> None:
        """Test reconnect attempt handler."""
        consumer._on_reconnect_attempt(mock_connection_message)
        consumer.stats_collector.on_reconnect_attempt.assert_called_once()

    @pytest.mark.unit
    def test_on_auth_failure(self, consumer: StatsConsumer, mock_connection_message: Mock) -> None:
        """Test auth failure handler."""
        consumer._on_auth_failure(mock_connection_message)
        consumer.stats_collector.on_auth_failure.assert_called_once()

    @pytest.mark.unit
    def test_on_connection_error(
        self, consumer: StatsConsumer, mock_connection_message: Mock
    ) -> None:
        """Test connection error handler."""
        consumer._on_connection_error(mock_connection_message)
        consumer.stats_collector.on_connection_error.assert_called_once()

    @pytest.mark.unit
    def test_on_ping_sent(self, consumer: StatsConsumer, mock_connection_message: Mock) -> None:
        """Test ping sent handler."""
        consumer._on_ping_sent(mock_connection_message)
        consumer.stats_collector.on_ping_sent.assert_called_once()

    @pytest.mark.unit
    def test_on_pong_received(self, consumer: StatsConsumer, mock_connection_message: Mock) -> None:
        """Test pong received handler."""
        consumer._on_pong_received(mock_connection_message)
        consumer.stats_collector.on_pong_received.assert_called_once()


class TestXMPPLifecycleHandlers:
    """Test XMPP lifecycle event handlers."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def consumer(self, mock_collector: Mock) -> StatsConsumer:
        """Create StatsConsumer with mocked dependencies."""
        with patch("app.stats.consumer.LoggingConfig"):
            return StatsConsumer(mock_collector)

    @pytest.mark.unit
    def test_on_xmpp_connected(self, consumer: StatsConsumer) -> None:
        """Test XMPP connected handler."""
        consumer._on_xmpp_connected()
        consumer.stats_collector.on_connected.assert_called_once()

    @pytest.mark.unit
    def test_on_xmpp_connected_with_message(self, consumer: StatsConsumer) -> None:
        """Test XMPP connected handler with message."""
        consumer._on_xmpp_connected(message=Mock())
        consumer.stats_collector.on_connected.assert_called_once()

    @pytest.mark.unit
    def test_on_xmpp_disconnected(self, consumer: StatsConsumer) -> None:
        """Test XMPP disconnected handler."""
        consumer._on_xmpp_disconnected()
        consumer.stats_collector.on_disconnected.assert_called_once()

    @pytest.mark.unit
    def test_on_xmpp_disconnected_with_message(self, consumer: StatsConsumer) -> None:
        """Test XMPP disconnected handler with message."""
        consumer._on_xmpp_disconnected(message=Mock())
        consumer.stats_collector.on_disconnected.assert_called_once()


class TestMessageEventHandlers:
    """Test message processing event handlers."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def consumer(self, mock_collector: Mock) -> StatsConsumer:
        """Create StatsConsumer with mocked dependencies."""
        with patch("app.stats.consumer.LoggingConfig"):
            return StatsConsumer(mock_collector)

    @pytest.fixture
    def mock_message_processing_message(self) -> Mock:
        """Create mock StatsMessageProcessingMessage."""
        message = Mock()
        message.source = "NWWS-OI"
        message.afos = "AFGAFC"
        message.product_id = "FXUS61KBOU"
        message.error_type = "parse_error"
        return message

    @pytest.mark.unit
    def test_on_message_received(
        self, consumer: StatsConsumer, mock_message_processing_message: Mock
    ) -> None:
        """Test message received handler."""
        consumer._on_message_received(mock_message_processing_message)
        consumer.stats_collector.on_message_received.assert_called_once()

    @pytest.mark.unit
    def test_on_groupchat_message_received(
        self, consumer: StatsConsumer, mock_message_processing_message: Mock
    ) -> None:
        """Test groupchat message received handler."""
        consumer._on_groupchat_message_received(mock_message_processing_message)
        consumer.stats_collector.on_groupchat_message_received.assert_called_once()

    @pytest.mark.unit
    def test_on_message_processed(
        self, consumer: StatsConsumer, mock_message_processing_message: Mock
    ) -> None:
        """Test message processed handler."""
        consumer._on_message_processed(mock_message_processing_message)
        consumer.stats_collector.on_message_processed.assert_called_once_with(
            source="NWWS-OI", afos="AFGAFC", product_id="FXUS61KBOU"
        )

    @pytest.mark.unit
    def test_on_message_processed_none_values(self, consumer: StatsConsumer) -> None:
        """Test message processed handler with None values."""
        message = Mock()
        message.source = None
        message.afos = None
        message.product_id = "FXUS61KBOU"

        consumer._on_message_processed(message)
        consumer.stats_collector.on_message_processed.assert_called_once_with(
            source="", afos="", product_id="FXUS61KBOU"
        )

    @pytest.mark.unit
    def test_on_message_failed(
        self, consumer: StatsConsumer, mock_message_processing_message: Mock
    ) -> None:
        """Test message failed handler."""
        consumer._on_message_failed(mock_message_processing_message)
        consumer.stats_collector.on_message_failed.assert_called_once_with("parse_error")

    @pytest.mark.unit
    def test_on_message_failed_none_error_type(self, consumer: StatsConsumer) -> None:
        """Test message failed handler with None error type."""
        message = Mock()
        message.error_type = None

        consumer._on_message_failed(message)
        consumer.stats_collector.on_message_failed.assert_called_once_with("unknown")

    @pytest.mark.unit
    def test_on_message_published(
        self, consumer: StatsConsumer, mock_message_processing_message: Mock
    ) -> None:
        """Test message published handler."""
        consumer._on_message_published(mock_message_processing_message)
        consumer.stats_collector.on_message_published.assert_called_once()


class TestHandlerEventHandlers:
    """Test output handler event handlers."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def consumer(self, mock_collector: Mock) -> StatsConsumer:
        """Create StatsConsumer with mocked dependencies."""
        with patch("app.stats.consumer.LoggingConfig"):
            return StatsConsumer(mock_collector)

    @pytest.fixture
    def mock_handler_message(self) -> Mock:
        """Create mock StatsHandlerMessage."""
        message = Mock()
        message.handler_name = "mqtt_primary"
        message.handler_type = "mqtt"
        return message

    @pytest.mark.unit
    def test_on_handler_registered(
        self, consumer: StatsConsumer, mock_handler_message: Mock
    ) -> None:
        """Test handler registered event."""
        consumer._on_handler_registered(mock_handler_message)
        consumer.stats_collector.register_output_handler.assert_called_once_with(
            handler_name="mqtt_primary", handler_type="mqtt"
        )

    @pytest.mark.unit
    def test_on_handler_registered_none_handler_type(self, consumer: StatsConsumer) -> None:
        """Test handler registered with None handler type."""
        message = Mock()
        message.handler_name = "mqtt_primary"
        message.handler_type = None

        consumer._on_handler_registered(message)
        consumer.stats_collector.register_output_handler.assert_called_once_with(
            handler_name="mqtt_primary",
            handler_type="mqtt_primary",  # Falls back to handler_name
        )

    @pytest.mark.unit
    def test_on_handler_connected(
        self, consumer: StatsConsumer, mock_handler_message: Mock
    ) -> None:
        """Test handler connected event."""
        consumer._on_handler_connected(mock_handler_message)
        consumer.stats_collector.on_handler_connected.assert_called_once_with("mqtt_primary")

    @pytest.mark.unit
    def test_on_handler_disconnected(
        self, consumer: StatsConsumer, mock_handler_message: Mock
    ) -> None:
        """Test handler disconnected event."""
        consumer._on_handler_disconnected(mock_handler_message)
        consumer.stats_collector.on_handler_disconnected.assert_called_once_with("mqtt_primary")

    @pytest.mark.unit
    def test_on_handler_publish_success(
        self, consumer: StatsConsumer, mock_handler_message: Mock
    ) -> None:
        """Test handler publish success event."""
        consumer._on_handler_publish_success(mock_handler_message)
        consumer.stats_collector.on_handler_publish_success.assert_called_once_with("mqtt_primary")

    @pytest.mark.unit
    def test_on_handler_publish_failed(
        self, consumer: StatsConsumer, mock_handler_message: Mock
    ) -> None:
        """Test handler publish failed event."""
        consumer._on_handler_publish_failed(mock_handler_message)
        consumer.stats_collector.on_handler_publish_failed.assert_called_once_with("mqtt_primary")

    @pytest.mark.unit
    def test_on_handler_connection_error(
        self, consumer: StatsConsumer, mock_handler_message: Mock
    ) -> None:
        """Test handler connection error event."""
        consumer._on_handler_connection_error(mock_handler_message)
        consumer.stats_collector.on_handler_connection_error.assert_called_once_with("mqtt_primary")


class TestFullIntegration:
    """Test full integration scenarios."""

    @pytest.fixture
    def mock_collector(self) -> Mock:
        """Create mock StatsCollector."""
        return Mock(spec=StatsCollector)

    @pytest.fixture
    def consumer(self, mock_collector: Mock) -> StatsConsumer:
        """Create StatsConsumer with mocked dependencies."""
        with patch("app.stats.consumer.LoggingConfig"):
            return StatsConsumer(mock_collector)

    @pytest.mark.unit
    def test_complete_lifecycle(self, consumer: StatsConsumer) -> None:
        """Test complete subscription lifecycle."""
        # Initially not subscribed
        assert not consumer.is_subscribed

        # Start subscription
        with patch("app.stats.consumer.MessageBus") as mock_bus:
            consumer.start()
            assert consumer.is_subscribed
            assert mock_bus.subscribe.call_count > 0

        # Stop subscription
        with patch("app.stats.consumer.MessageBus") as mock_bus:
            consumer.stop()
            assert not consumer.is_subscribed
            assert mock_bus.unsubscribe.call_count > 0

    @pytest.mark.unit
    def test_event_handling_without_subscription(self, consumer: StatsConsumer) -> None:
        """Test that event handlers work even without explicit subscription."""
        # Test connection events
        message = Mock()
        consumer._on_connection_attempt(message)
        consumer._on_connection_established(message)
        consumer._on_connection_lost(message)

        # Verify collector methods were called
        consumer.stats_collector.on_connection_attempt.assert_called_once()
        consumer.stats_collector.on_connected.assert_called_once()
        consumer.stats_collector.on_disconnected.assert_called_once()

    @pytest.mark.unit
    def test_multiple_start_stop_cycles(self, consumer: StatsConsumer) -> None:
        """Test multiple start/stop cycles."""
        with patch("app.stats.consumer.MessageBus") as mock_bus:
            # First cycle
            consumer.start()
            assert consumer.is_subscribed
            consumer.stop()
            assert not consumer.is_subscribed

            # Second cycle
            consumer.start()
            assert consumer.is_subscribed
            consumer.stop()
            assert not consumer.is_subscribed

            # Should have made subscription calls for each start
            assert mock_bus.subscribe.call_count > 0
            assert mock_bus.unsubscribe.call_count > 0
