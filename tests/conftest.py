"""Test configuration and fixtures."""

from unittest.mock import Mock, patch

import pytest
from pubsub import pub


@pytest.fixture(autouse=True)
def reset_pubsub():
    """Reset pubsub state before each test."""
    yield

    # After test, clear all listeners from existing topics
    try:
        root_topic = pub.getDefaultTopicMgr().getRootAllTopics()

        def clear_listeners_recursive(topic):
            # Clear listeners for this topic
            for listener in topic.getListeners():
                try:
                    pub.unsubscribe(listener, topic.getName())
                except Exception:
                    pass

            # Recursively clear subtopics
            for subtopic in topic.getSubtopics():
                clear_listeners_recursive(subtopic)

        clear_listeners_recursive(root_topic)
    except Exception:
        pass  # Best effort cleanup


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    with patch("app.messaging.message_bus.logger") as mock_log:
        yield mock_log


@pytest.fixture
def sample_product_message():
    """Sample ProductMessage for testing."""
    from app.messaging.message_bus import ProductMessage

    return ProductMessage(
        source="NWWS-OI",
        afos="AFGAFC",
        product_id="AFGAFC.2025.05.27.120000",
        structured_data='{"test": "data"}',
        subject="Test Weather Alert",
        metadata={"priority": "high", "expires": "2025-05-27T13:00:00Z"},
    )


@pytest.fixture
def sample_stats_message():
    """Sample StatsMessageProcessingMessage for testing."""
    from app.messaging.message_bus import StatsMessageProcessingMessage

    return StatsMessageProcessingMessage(
        source="NWWS-OI", afos="AFGAFC", wmo="AFGAFC.2025.05.27.120000", error_type=None
    )


@pytest.fixture
def sample_handler_message():
    """Sample StatsHandlerMessage for testing."""
    from app.messaging.message_bus import StatsHandlerMessage

    return StatsHandlerMessage(handler_name="mqtt_handler", handler_type="mqtt")


@pytest.fixture
def mock_listener():
    """Mock listener function for testing subscriptions."""
    mock = Mock()
    mock.__name__ = "mock_listener"
    return mock
