"""Message bus and message types for the pubsub system."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from loguru import logger
from pubsub import pub

from app.models.product import TextProductModel


@dataclass
class ProductMessage:
    """Message containing weather product data."""

    source: str
    afos: str
    product_id: str
    text_product: TextProductModel
    subject: str = ""
    metadata: dict[str, Any] | None = None


@dataclass
class StatsConnectionMessage:
    """Message for connection-related statistics events."""


@dataclass
class StatsMessageProcessingMessage:
    """Message for message processing statistics events."""

    source: str | None = None
    afos: str | None = None
    wmo: str | None = None
    error_type: str | None = None


@dataclass
class StatsHandlerMessage:
    """Message for output handler statistics events."""

    handler_name: str
    handler_type: str | None = None


class MessageBus:
    """Central message bus for application-wide communication."""

    @staticmethod
    def publish(topic: str, **kwargs: Any) -> None:
        """Publish a message to a topic."""
        try:
            pub.sendMessage(topic, **kwargs)
            logger.debug("Published message", topic=topic, kwargs_keys=list(kwargs.keys()))
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to publish message", topic=topic, error=str(e))

    @staticmethod
    def subscribe(topic: str, listener: Callable[..., Any]) -> None:
        """Subscribe to a topic."""
        try:
            pub.subscribe(listener, topic)
            listener_name: str = getattr(listener, "__name__", str(listener))
            logger.debug("Subscribed to topic", topic=topic, listener=listener_name)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to subscribe to topic", topic=topic, error=str(e))

    @staticmethod
    def unsubscribe(topic: str, listener: Callable[..., Any]) -> None:
        """Unsubscribe from a topic."""
        try:
            pub.unsubscribe(listener, topic)
            listener_name: str = getattr(listener, "__name__", str(listener))
            logger.debug("Unsubscribed from topic", topic=topic, listener=listener_name)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to unsubscribe from topic", topic=topic, error=str(e))

    @staticmethod
    def get_topic_subscribers(topic: str) -> list[Callable[..., Any]]:
        """Get all subscribers for a topic."""
        try:
            return pub.getDefaultTopicMgr().getTopic(topic).getListeners()
        except Exception:  # noqa: BLE001
            return []
