"""Statistics consumer that subscribes to message bus events."""

from loguru import logger

from messaging.message_bus import MessageBus, StatsConnectionMessage, StatsMessageProcessingMessage, StatsHandlerMessage
from messaging.topics import Topics
from .collector import StatsCollector


class StatsConsumer:
    """Consumer that listens to statistics events via message bus."""
    
    def __init__(self, stats_collector: StatsCollector) -> None:
        """Initialize the stats consumer.
        
        Args:
            stats_collector: The statistics collector instance
        """
        self.stats_collector = stats_collector
        self._subscribed = False
        logger.debug("Statistics consumer initialized")
    
    def start(self) -> None:
        """Start subscribing to statistics events."""
        if self._subscribed:
            logger.warning("Statistics consumer is already subscribed")
            return
        
        # Subscribe to connection events
        MessageBus.subscribe(Topics.STATS_CONNECTION_ATTEMPT, self._on_connection_attempt)
        MessageBus.subscribe(Topics.STATS_CONNECTION_ESTABLISHED, self._on_connection_established)
        MessageBus.subscribe(Topics.STATS_CONNECTION_LOST, self._on_connection_lost)
        MessageBus.subscribe(Topics.STATS_RECONNECT_ATTEMPT, self._on_reconnect_attempt)
        MessageBus.subscribe(Topics.STATS_AUTH_FAILURE, self._on_auth_failure)
        MessageBus.subscribe(Topics.STATS_CONNECTION_ERROR, self._on_connection_error)
        MessageBus.subscribe(Topics.STATS_PING_SENT, self._on_ping_sent)
        MessageBus.subscribe(Topics.STATS_PONG_RECEIVED, self._on_pong_received)
        
        # Subscribe to XMPP lifecycle events
        MessageBus.subscribe(Topics.XMPP_CONNECTED, self._on_xmpp_connected)
        MessageBus.subscribe(Topics.XMPP_DISCONNECTED, self._on_xmpp_disconnected)
        
        # Subscribe to message events
        MessageBus.subscribe(Topics.STATS_MESSAGE_RECEIVED, self._on_message_received)
        MessageBus.subscribe(Topics.STATS_GROUPCHAT_MESSAGE_RECEIVED, self._on_groupchat_message_received)
        MessageBus.subscribe(Topics.STATS_MESSAGE_PROCESSED, self._on_message_processed)
        MessageBus.subscribe(Topics.STATS_MESSAGE_FAILED, self._on_message_failed)
        MessageBus.subscribe(Topics.STATS_MESSAGE_PUBLISHED, self._on_message_published)
        
        # Subscribe to handler events
        MessageBus.subscribe(Topics.STATS_HANDLER_REGISTERED, self._on_handler_registered)
        MessageBus.subscribe(Topics.STATS_HANDLER_CONNECTED, self._on_handler_connected)
        MessageBus.subscribe(Topics.STATS_HANDLER_DISCONNECTED, self._on_handler_disconnected)
        MessageBus.subscribe(Topics.STATS_HANDLER_PUBLISH_SUCCESS, self._on_handler_publish_success)
        MessageBus.subscribe(Topics.STATS_HANDLER_PUBLISH_FAILED, self._on_handler_publish_failed)
        MessageBus.subscribe(Topics.STATS_HANDLER_CONNECTION_ERROR, self._on_handler_connection_error)
        
        self._subscribed = True
        logger.info("Statistics consumer started and subscribed to all stats topics")
    
    def stop(self) -> None:
        """Stop subscribing to statistics events."""
        if not self._subscribed:
            return
        
        # Unsubscribe from connection events
        MessageBus.unsubscribe(Topics.STATS_CONNECTION_ATTEMPT, self._on_connection_attempt)
        MessageBus.unsubscribe(Topics.STATS_CONNECTION_ESTABLISHED, self._on_connection_established)
        MessageBus.unsubscribe(Topics.STATS_CONNECTION_LOST, self._on_connection_lost)
        MessageBus.unsubscribe(Topics.STATS_RECONNECT_ATTEMPT, self._on_reconnect_attempt)
        MessageBus.unsubscribe(Topics.STATS_AUTH_FAILURE, self._on_auth_failure)
        MessageBus.unsubscribe(Topics.STATS_CONNECTION_ERROR, self._on_connection_error)
        MessageBus.unsubscribe(Topics.STATS_PING_SENT, self._on_ping_sent)
        MessageBus.unsubscribe(Topics.STATS_PONG_RECEIVED, self._on_pong_received)
        
        # Unsubscribe from XMPP lifecycle events
        MessageBus.unsubscribe(Topics.XMPP_CONNECTED, self._on_xmpp_connected)
        MessageBus.unsubscribe(Topics.XMPP_DISCONNECTED, self._on_xmpp_disconnected)
        
        # Unsubscribe from message events
        MessageBus.unsubscribe(Topics.STATS_MESSAGE_RECEIVED, self._on_message_received)
        MessageBus.unsubscribe(Topics.STATS_GROUPCHAT_MESSAGE_RECEIVED, self._on_groupchat_message_received)
        MessageBus.unsubscribe(Topics.STATS_MESSAGE_PROCESSED, self._on_message_processed)
        MessageBus.unsubscribe(Topics.STATS_MESSAGE_FAILED, self._on_message_failed)
        MessageBus.unsubscribe(Topics.STATS_MESSAGE_PUBLISHED, self._on_message_published)
        
        # Unsubscribe from handler events
        MessageBus.unsubscribe(Topics.STATS_HANDLER_REGISTERED, self._on_handler_registered)
        MessageBus.unsubscribe(Topics.STATS_HANDLER_CONNECTED, self._on_handler_connected)
        MessageBus.unsubscribe(Topics.STATS_HANDLER_DISCONNECTED, self._on_handler_disconnected)
        MessageBus.unsubscribe(Topics.STATS_HANDLER_PUBLISH_SUCCESS, self._on_handler_publish_success)
        MessageBus.unsubscribe(Topics.STATS_HANDLER_PUBLISH_FAILED, self._on_handler_publish_failed)
        MessageBus.unsubscribe(Topics.STATS_HANDLER_CONNECTION_ERROR, self._on_handler_connection_error)
        
        self._subscribed = False
        logger.info("Statistics consumer stopped and unsubscribed from all stats topics")
    
    # Connection event handlers
    def _on_connection_attempt(self, message: StatsConnectionMessage) -> None:
        """Handle connection attempt event."""
        self.stats_collector.on_connection_attempt()
    
    def _on_connection_established(self, message: StatsConnectionMessage) -> None:
        """Handle connection established event."""
        self.stats_collector.on_connected()
    
    def _on_connection_lost(self, message: StatsConnectionMessage) -> None:
        """Handle connection lost event."""
        self.stats_collector.on_disconnected()
    
    def _on_reconnect_attempt(self, message: StatsConnectionMessage) -> None:
        """Handle reconnect attempt event."""
        self.stats_collector.on_reconnect_attempt()
    
    def _on_auth_failure(self, message: StatsConnectionMessage) -> None:
        """Handle authentication failure event."""
        self.stats_collector.on_auth_failure()
    
    def _on_connection_error(self, message: StatsConnectionMessage) -> None:
        """Handle connection error event."""
        self.stats_collector.on_connection_error()
    
    def _on_ping_sent(self, message: StatsConnectionMessage) -> None:
        """Handle ping sent event."""
        self.stats_collector.on_ping_sent()
    
    def _on_pong_received(self, message: StatsConnectionMessage) -> None:
        """Handle pong received event."""
        self.stats_collector.on_pong_received()
    
    # XMPP lifecycle event handlers
    def _on_xmpp_connected(self, message=None) -> None:
        """Handle XMPP connected event."""
        self.stats_collector.on_connected()
    
    def _on_xmpp_disconnected(self, message=None) -> None:
        """Handle XMPP disconnected event."""
        self.stats_collector.on_disconnected()
    
    # Message event handlers
    def _on_message_received(self, message: StatsMessageProcessingMessage) -> None:
        """Handle message received event."""
        self.stats_collector.on_message_received()
    
    def _on_groupchat_message_received(self, message: StatsMessageProcessingMessage) -> None:
        """Handle groupchat message received event."""
        self.stats_collector.on_groupchat_message_received()
    
    def _on_message_processed(self, message: StatsMessageProcessingMessage) -> None:
        """Handle message processed event."""
        self.stats_collector.on_message_processed(
            source=message.source or "",
            afos=message.afos or "",
            product_id=message.product_id
        )
    
    def _on_message_failed(self, message: StatsMessageProcessingMessage) -> None:
        """Handle message failed event."""
        self.stats_collector.on_message_failed(message.error_type or "unknown")
    
    def _on_message_published(self, message: StatsMessageProcessingMessage) -> None:
        """Handle message published event."""
        self.stats_collector.on_message_published()
    
    # Handler event handlers
    def _on_handler_registered(self, message: StatsHandlerMessage) -> None:
        """Handle handler registered event."""
        self.stats_collector.register_output_handler(
            handler_name=message.handler_name,
            handler_type=message.handler_type or message.handler_name
        )
    
    def _on_handler_connected(self, message: StatsHandlerMessage) -> None:
        """Handle handler connected event."""
        self.stats_collector.on_handler_connected(message.handler_name)
    
    def _on_handler_disconnected(self, message: StatsHandlerMessage) -> None:
        """Handle handler disconnected event."""
        self.stats_collector.on_handler_disconnected(message.handler_name)
    
    def _on_handler_publish_success(self, message: StatsHandlerMessage) -> None:
        """Handle handler publish success event."""
        self.stats_collector.on_handler_publish_success(message.handler_name)
    
    def _on_handler_publish_failed(self, message: StatsHandlerMessage) -> None:
        """Handle handler publish failed event."""
        self.stats_collector.on_handler_publish_failed(message.handler_name)
    
    def _on_handler_connection_error(self, message: StatsHandlerMessage) -> None:
        """Handle handler connection error event."""
        self.stats_collector.on_handler_connection_error(message.handler_name)
    
    @property
    def is_subscribed(self) -> bool:
        """Check if the consumer is currently subscribed."""
        return self._subscribed
