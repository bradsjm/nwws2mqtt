"""Tests for message bus functionality."""

from unittest.mock import Mock, call, patch

import pytest
from pubsub import pub

from app.messaging.message_bus import (
    MessageBus,
    ProductMessage,
    StatsConnectionMessage,
    StatsHandlerMessage,
    StatsMessageProcessingMessage,
)
from app.messaging.topics import Topics


class TestProductMessage:
    """Test cases for ProductMessage dataclass."""

    def test_product_message_creation(self):
        """Test ProductMessage creation with required fields."""
        message = ProductMessage(
            source="NWWS-OI", afos="AFGAFC", product_id="AFGAFC.2025.05.27.120000", structured_data='{"test": "data"}'
        )

        assert message.source == "NWWS-OI"
        assert message.afos == "AFGAFC"
        assert message.product_id == "AFGAFC.2025.05.27.120000"
        assert message.structured_data == '{"test": "data"}'
        assert message.subject == ""
        assert message.metadata is None

    def test_product_message_creation_with_optional_fields(self):
        """Test ProductMessage creation with all fields."""
        metadata = {"priority": "high", "expires": "2025-05-27T13:00:00Z"}
        message = ProductMessage(
            source="NWWS-OI",
            afos="AFGAFC",
            product_id="AFGAFC.2025.05.27.120000",
            structured_data='{"test": "data"}',
            subject="Test Weather Alert",
            metadata=metadata,
        )

        assert message.source == "NWWS-OI"
        assert message.afos == "AFGAFC"
        assert message.product_id == "AFGAFC.2025.05.27.120000"
        assert message.structured_data == '{"test": "data"}'
        assert message.subject == "Test Weather Alert"
        assert message.metadata == metadata


class TestStatsMessages:
    """Test cases for statistics message dataclasses."""

    def test_stats_connection_message_creation(self):
        """Test StatsConnectionMessage creation."""
        message = StatsConnectionMessage()
        assert isinstance(message, StatsConnectionMessage)

    def test_stats_message_processing_message_defaults(self):
        """Test StatsMessageProcessingMessage with default values."""
        message = StatsMessageProcessingMessage()

        assert message.source is None
        assert message.afos is None
        assert message.product_id is None
        assert message.error_type is None

    def test_stats_message_processing_message_with_values(self):
        """Test StatsMessageProcessingMessage with provided values."""
        message = StatsMessageProcessingMessage(
            source="NWWS-OI", afos="AFGAFC", product_id="AFGAFC.2025.05.27.120000", error_type="parsing_error"
        )

        assert message.source == "NWWS-OI"
        assert message.afos == "AFGAFC"
        assert message.product_id == "AFGAFC.2025.05.27.120000"
        assert message.error_type == "parsing_error"

    def test_stats_handler_message_required_fields(self):
        """Test StatsHandlerMessage with required fields."""
        message = StatsHandlerMessage(handler_name="mqtt_handler")

        assert message.handler_name == "mqtt_handler"
        assert message.handler_type is None

    def test_stats_handler_message_all_fields(self):
        """Test StatsHandlerMessage with all fields."""
        message = StatsHandlerMessage(handler_name="mqtt_handler", handler_type="mqtt")

        assert message.handler_name == "mqtt_handler"
        assert message.handler_type == "mqtt"


class TestMessageBus:
    """Test cases for MessageBus functionality."""

    def test_publish_success(self, mock_logger):
        """Test successful message publishing."""
        with patch("pubsub.pub.sendMessage") as mock_send:
            MessageBus.publish(Topics.PRODUCT_RECEIVED, data="test")

            mock_send.assert_called_once_with(Topics.PRODUCT_RECEIVED, data="test")
            mock_logger.debug.assert_called_once_with("Published message", topic=Topics.PRODUCT_RECEIVED, kwargs_keys=["data"])

    def test_publish_with_multiple_kwargs(self, mock_logger):
        """Test publishing with multiple keyword arguments."""
        with patch("pubsub.pub.sendMessage") as mock_send:
            MessageBus.publish(Topics.PRODUCT_PROCESSED, message="test_message", handler="mqtt", status="success")

            mock_send.assert_called_once_with(Topics.PRODUCT_PROCESSED, message="test_message", handler="mqtt", status="success")
            mock_logger.debug.assert_called_once_with(
                "Published message", topic=Topics.PRODUCT_PROCESSED, kwargs_keys=["message", "handler", "status"]
            )

    def test_publish_failure(self, mock_logger):
        """Test handling of publish failures."""
        with patch("pubsub.pub.sendMessage", side_effect=Exception("Test error")):
            MessageBus.publish(Topics.PRODUCT_RECEIVED, data="test")

            mock_logger.error.assert_called_once_with(
                "Failed to publish message", topic=Topics.PRODUCT_RECEIVED, error="Test error"
            )

    def test_subscribe_success(self, mock_logger, mock_listener):
        """Test successful subscription to a topic."""
        with patch("pubsub.pub.subscribe") as mock_sub:
            MessageBus.subscribe(Topics.PRODUCT_RECEIVED, mock_listener)

            mock_sub.assert_called_once_with(mock_listener, Topics.PRODUCT_RECEIVED)
            mock_logger.debug.assert_called_once_with(
                "Subscribed to topic", topic=Topics.PRODUCT_RECEIVED, listener=mock_listener.__name__
            )

    def test_subscribe_failure(self, mock_logger, mock_listener):
        """Test handling of subscription failures."""
        with patch("pubsub.pub.subscribe", side_effect=Exception("Test error")):
            MessageBus.subscribe(Topics.PRODUCT_RECEIVED, mock_listener)

            mock_logger.error.assert_called_once_with(
                "Failed to subscribe to topic", topic=Topics.PRODUCT_RECEIVED, error="Test error"
            )

    def test_unsubscribe_success(self, mock_logger, mock_listener):
        """Test successful unsubscription from a topic."""
        with patch("pubsub.pub.unsubscribe") as mock_unsub:
            MessageBus.unsubscribe(Topics.PRODUCT_RECEIVED, mock_listener)

            mock_unsub.assert_called_once_with(mock_listener, Topics.PRODUCT_RECEIVED)
            mock_logger.debug.assert_called_once_with(
                "Unsubscribed from topic", topic=Topics.PRODUCT_RECEIVED, listener=mock_listener.__name__
            )

    def test_unsubscribe_failure(self, mock_logger, mock_listener):
        """Test handling of unsubscription failures."""
        with patch("pubsub.pub.unsubscribe", side_effect=Exception("Test error")):
            MessageBus.unsubscribe(Topics.PRODUCT_RECEIVED, mock_listener)

            mock_logger.error.assert_called_once_with(
                "Failed to unsubscribe from topic", topic=Topics.PRODUCT_RECEIVED, error="Test error"
            )

    def test_get_topic_subscribers_success(self):
        """Test getting subscribers for a topic."""
        mock_listeners = [Mock(), Mock()]
        mock_topic = Mock()
        mock_topic.getListeners.return_value = mock_listeners

        with patch("pubsub.pub.getDefaultTopicMgr") as mock_mgr:
            mock_mgr.return_value.getTopic.return_value = mock_topic

            subscribers = MessageBus.get_topic_subscribers(Topics.PRODUCT_RECEIVED)

            assert subscribers == mock_listeners
            mock_mgr.return_value.getTopic.assert_called_once_with(Topics.PRODUCT_RECEIVED)
            mock_topic.getListeners.assert_called_once()

    def test_get_topic_subscribers_failure(self):
        """Test handling of failures when getting topic subscribers."""
        with patch("pubsub.pub.getDefaultTopicMgr", side_effect=Exception("Test error")):
            subscribers = MessageBus.get_topic_subscribers(Topics.PRODUCT_RECEIVED)
            assert subscribers == []


class TestMessageBusIntegration:
    """Integration tests for MessageBus with actual pubsub functionality."""

    @pytest.mark.integration
    def test_publish_subscribe_integration(self):
        """Test actual publish/subscribe integration."""
        received_messages = []

        def listener(message, priority):
            received_messages.append({"message": message, "priority": priority})

        # Subscribe to topic
        MessageBus.subscribe(Topics.PRODUCT_RECEIVED, listener)

        # Publish message
        MessageBus.publish(Topics.PRODUCT_RECEIVED, message="test", priority="high")

        # Verify message was received
        assert len(received_messages) == 1
        assert received_messages[0] == {"message": "test", "priority": "high"}

    @pytest.mark.integration
    def test_multiple_subscribers(self):
        """Test multiple subscribers receiving the same message."""
        received_messages_1 = []
        received_messages_2 = []

        def listener1(handler, status):
            received_messages_1.append({"handler": handler, "status": status})

        def listener2(handler, status):
            received_messages_2.append({"handler": handler, "status": status})

        # Subscribe both listeners
        MessageBus.subscribe(Topics.PRODUCT_PROCESSED, listener1)
        MessageBus.subscribe(Topics.PRODUCT_PROCESSED, listener2)

        # Publish message
        MessageBus.publish(Topics.PRODUCT_PROCESSED, handler="mqtt", status="success")

        # Verify both listeners received the message
        expected_data = {"handler": "mqtt", "status": "success"}
        assert len(received_messages_1) == 1
        assert len(received_messages_2) == 1
        assert received_messages_1[0] == expected_data
        assert received_messages_2[0] == expected_data

    @pytest.mark.integration
    def test_unsubscribe_integration(self):
        """Test unsubscription stops message delivery."""
        received_messages = []

        def listener(status):
            received_messages.append({"status": status})

        # Subscribe and publish first message
        MessageBus.subscribe(Topics.XMPP_CONNECTED, listener)
        MessageBus.publish(Topics.XMPP_CONNECTED, status="connected")

        # Unsubscribe and publish second message
        MessageBus.unsubscribe(Topics.XMPP_CONNECTED, listener)
        MessageBus.publish(Topics.XMPP_CONNECTED, status="still_connected")

        # Verify only first message was received
        assert len(received_messages) == 1
        assert received_messages[0] == {"status": "connected"}

    @pytest.mark.integration
    def test_get_topic_subscribers_integration(self):
        """Test getting actual topic subscribers."""

        def listener1(**kwargs):
            pass

        def listener2(**kwargs):
            pass

        # Initially no subscribers
        subscribers = MessageBus.get_topic_subscribers(Topics.HANDLER_CONNECTED)
        assert len(subscribers) == 0

        # Add subscribers
        MessageBus.subscribe(Topics.HANDLER_CONNECTED, listener1)
        MessageBus.subscribe(Topics.HANDLER_CONNECTED, listener2)

        # Check subscribers
        subscribers = MessageBus.get_topic_subscribers(Topics.HANDLER_CONNECTED)
        assert len(subscribers) == 2

        # Unsubscribe one
        MessageBus.unsubscribe(Topics.HANDLER_CONNECTED, listener1)
        subscribers = MessageBus.get_topic_subscribers(Topics.HANDLER_CONNECTED)
        assert len(subscribers) == 1


class TestMessageBusWithDataclasses:
    """Test MessageBus usage with the defined message dataclasses."""

    @pytest.mark.integration
    def test_publish_product_message(self, sample_product_message):
        """Test publishing a ProductMessage through the message bus."""
        received_messages = []

        def product_listener(message):
            received_messages.append(message)

        MessageBus.subscribe(Topics.PRODUCT_FAILED, product_listener)
        MessageBus.publish(Topics.PRODUCT_FAILED, message=sample_product_message)

        assert len(received_messages) == 1
        assert received_messages[0] == sample_product_message

    @pytest.mark.integration
    def test_publish_stats_message(self, sample_stats_message):
        """Test publishing a StatsMessageProcessingMessage through the message bus."""
        received_messages = []

        def stats_listener(message):
            received_messages.append(message)

        MessageBus.subscribe(Topics.STATS_MESSAGE_PROCESSED, stats_listener)
        MessageBus.publish(Topics.STATS_MESSAGE_PROCESSED, message=sample_stats_message)

        assert len(received_messages) == 1
        assert received_messages[0] == sample_stats_message

    @pytest.mark.integration
    def test_publish_handler_message(self, sample_handler_message):
        """Test publishing a StatsHandlerMessage through the message bus."""
        received_messages = []

        def handler_listener(message):
            received_messages.append(message)

        MessageBus.subscribe(Topics.STATS_HANDLER_CONNECTED, handler_listener)
        MessageBus.publish(Topics.STATS_HANDLER_CONNECTED, message=sample_handler_message)

        assert len(received_messages) == 1
        assert received_messages[0] == sample_handler_message
