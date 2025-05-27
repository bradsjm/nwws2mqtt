"""Message bus and message types for the pubsub system."""

from dataclasses import dataclass
from typing import Any

from loguru import logger
from pubsub import pub


@dataclass
class ProductMessage:
    """Message containing weather product data."""
    source: str
    afos: str
    product_id: str
    structured_data: str
    subject: str = ""
    metadata: dict[str, Any] | None = None


class MessageBus:
    """Central message bus for application-wide communication."""
    
    @staticmethod
    def publish(topic: str, **kwargs) -> None:
        """Publish a message to a topic."""
        try:
            pub.sendMessage(topic, **kwargs)
            logger.debug("Published message", topic=topic, kwargs_keys=list(kwargs.keys()))
        except Exception as e:
            logger.error("Failed to publish message", topic=topic, error=str(e))
    
    @staticmethod
    def subscribe(topic: str, listener) -> None:
        """Subscribe to a topic."""
        try:
            pub.subscribe(listener, topic)
            logger.debug("Subscribed to topic", topic=topic, listener=listener.__name__)
        except Exception as e:
            logger.error("Failed to subscribe to topic", topic=topic, error=str(e))
    
    @staticmethod
    def unsubscribe(topic: str, listener) -> None:
        """Unsubscribe from a topic."""
        try:
            pub.unsubscribe(listener, topic)
            logger.debug("Unsubscribed from topic", topic=topic, listener=listener.__name__)
        except Exception as e:
            logger.error("Failed to unsubscribe from topic", topic=topic, error=str(e))
    
    @staticmethod
    def get_topic_subscribers(topic: str) -> list:
        """Get all subscribers for a topic."""
        try:
            return pub.getDefaultTopicMgr().getTopic(topic).getListeners()
        except Exception:
            return []
