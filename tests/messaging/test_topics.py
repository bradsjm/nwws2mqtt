"""Tests for topic definitions."""

import pytest

from app.messaging.topics import Topics


class TestTopics:
    """Test cases for Topics class constants."""

    def test_product_topics_exist(self):
        """Test that product-related topics are defined."""
        assert hasattr(Topics, "PRODUCT_RECEIVED")
        assert hasattr(Topics, "PRODUCT_PROCESSED")
        assert hasattr(Topics, "PRODUCT_FAILED")

        assert Topics.PRODUCT_RECEIVED == "product.received"
        assert Topics.PRODUCT_PROCESSED == "product.processed"
        assert Topics.PRODUCT_FAILED == "product.failed"

    def test_xmpp_topics_exist(self):
        """Test that XMPP connection topics are defined."""
        assert hasattr(Topics, "XMPP_CONNECTED")
        assert hasattr(Topics, "XMPP_DISCONNECTED")
        assert hasattr(Topics, "XMPP_ERROR")

        assert Topics.XMPP_CONNECTED == "xmpp.connected"
        assert Topics.XMPP_DISCONNECTED == "xmpp.disconnected"
        assert Topics.XMPP_ERROR == "xmpp.error"

    def test_handler_topics_exist(self):
        """Test that handler-related topics are defined."""
        assert hasattr(Topics, "HANDLER_CONNECTED")
        assert hasattr(Topics, "HANDLER_DISCONNECTED")
        assert hasattr(Topics, "HANDLER_ERROR")

        assert Topics.HANDLER_CONNECTED == "handler.connected"
        assert Topics.HANDLER_DISCONNECTED == "handler.disconnected"
        assert Topics.HANDLER_ERROR == "handler.error"

    def test_stats_connection_topics_exist(self):
        """Test that statistics connection topics are defined."""
        expected_connection_topics = [
            ("STATS_CONNECTION_ATTEMPT", "stats.connection.attempt"),
            ("STATS_CONNECTION_ESTABLISHED", "stats.connection.established"),
            ("STATS_CONNECTION_LOST", "stats.connection.lost"),
            ("STATS_RECONNECT_ATTEMPT", "stats.reconnect.attempt"),
            ("STATS_AUTH_FAILURE", "stats.auth.failure"),
            ("STATS_CONNECTION_ERROR", "stats.connection.error"),
            ("STATS_PING_SENT", "stats.ping.sent"),
            ("STATS_PONG_RECEIVED", "stats.pong.received"),
        ]

        for attr_name, expected_value in expected_connection_topics:
            assert hasattr(Topics, attr_name)
            assert getattr(Topics, attr_name) == expected_value

    def test_stats_message_topics_exist(self):
        """Test that statistics message topics are defined."""
        expected_message_topics = [
            ("STATS_MESSAGE_RECEIVED", "stats.message.received"),
            ("STATS_GROUPCHAT_MESSAGE_RECEIVED", "stats.message.groupchat.received"),
            ("STATS_MESSAGE_PROCESSED", "stats.message.processed"),
            ("STATS_MESSAGE_FAILED", "stats.message.failed"),
            ("STATS_MESSAGE_PUBLISHED", "stats.message.published"),
        ]

        for attr_name, expected_value in expected_message_topics:
            assert hasattr(Topics, attr_name)
            assert getattr(Topics, attr_name) == expected_value

    def test_stats_handler_topics_exist(self):
        """Test that statistics handler topics are defined."""
        expected_handler_topics = [
            ("STATS_HANDLER_REGISTERED", "stats.handler.registered"),
            ("STATS_HANDLER_CONNECTED", "stats.handler.connected"),
            ("STATS_HANDLER_DISCONNECTED", "stats.handler.disconnected"),
            ("STATS_HANDLER_PUBLISH_SUCCESS", "stats.handler.publish.success"),
            ("STATS_HANDLER_PUBLISH_FAILED", "stats.handler.publish.failed"),
            ("STATS_HANDLER_CONNECTION_ERROR", "stats.handler.connection.error"),
        ]

        for attr_name, expected_value in expected_handler_topics:
            assert hasattr(Topics, attr_name)
            assert getattr(Topics, attr_name) == expected_value

    def test_all_topics_are_strings(self):
        """Test that all topic values are strings."""
        for attr_name in dir(Topics):
            if not attr_name.startswith("_"):  # Skip private/magic methods
                topic_value = getattr(Topics, attr_name)
                assert isinstance(topic_value, str), f"{attr_name} should be a string"

    def test_topic_naming_convention(self):
        """Test that topics follow the expected naming convention."""
        for attr_name in dir(Topics):
            if not attr_name.startswith("_"):  # Skip private/magic methods
                topic_value = getattr(Topics, attr_name)
                # Topics should contain dots and be lowercase
                assert "." in topic_value, f"{attr_name} should contain dots"
                assert topic_value.islower(), f"{attr_name} should be lowercase"

    def test_no_duplicate_topic_values(self):
        """Test that there are no duplicate topic values."""
        topic_values = []
        for attr_name in dir(Topics):
            if not attr_name.startswith("_"):  # Skip private/magic methods
                topic_value = getattr(Topics, attr_name)
                topic_values.append(topic_value)

        # Check for duplicates
        assert len(topic_values) == len(set(topic_values)), "Found duplicate topic values"

    @pytest.mark.parametrize(
        "topic_attr",
        [
            "PRODUCT_RECEIVED",
            "PRODUCT_PROCESSED",
            "PRODUCT_FAILED",
            "XMPP_CONNECTED",
            "XMPP_DISCONNECTED",
            "XMPP_ERROR",
            "HANDLER_CONNECTED",
            "HANDLER_DISCONNECTED",
            "HANDLER_ERROR",
        ],
    )
    def test_critical_topics_exist(self, topic_attr):
        """Test that critical topics are defined and accessible."""
        assert hasattr(Topics, topic_attr)
        topic_value = getattr(Topics, topic_attr)
        assert isinstance(topic_value, str)
        assert len(topic_value) > 0
