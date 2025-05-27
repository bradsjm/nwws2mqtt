"""Topic definitions for the pubsub system."""


class Topics:
    """Centralized topic definitions for the application."""
    
    # Product-related topics
    PRODUCT_RECEIVED = "product.received"
    PRODUCT_PROCESSED = "product.processed"
    PRODUCT_FAILED = "product.failed"
    
    # Connection-related topics  
    XMPP_CONNECTED = "xmpp.connected"
    XMPP_DISCONNECTED = "xmpp.disconnected"
    XMPP_ERROR = "xmpp.error"
    
    # Handler-related topics
    HANDLER_CONNECTED = "handler.connected"
    HANDLER_DISCONNECTED = "handler.disconnected"
    HANDLER_ERROR = "handler.error"
    
    # Statistics topics
    STATS_CONNECTION_ATTEMPT = "stats.connection.attempt"
    STATS_CONNECTION_ESTABLISHED = "stats.connection.established"
    STATS_CONNECTION_LOST = "stats.connection.lost"
    STATS_RECONNECT_ATTEMPT = "stats.reconnect.attempt"
    STATS_AUTH_FAILURE = "stats.auth.failure"
    STATS_CONNECTION_ERROR = "stats.connection.error"
    STATS_PING_SENT = "stats.ping.sent"
    STATS_PONG_RECEIVED = "stats.pong.received"
    
    STATS_MESSAGE_RECEIVED = "stats.message.received"
    STATS_GROUPCHAT_MESSAGE_RECEIVED = "stats.message.groupchat.received"
    STATS_MESSAGE_PROCESSED = "stats.message.processed"
    STATS_MESSAGE_FAILED = "stats.message.failed"
    STATS_MESSAGE_PUBLISHED = "stats.message.published"
    
    STATS_HANDLER_REGISTERED = "stats.handler.registered"
    STATS_HANDLER_CONNECTED = "stats.handler.connected"
    STATS_HANDLER_DISCONNECTED = "stats.handler.disconnected"
    STATS_HANDLER_PUBLISH_SUCCESS = "stats.handler.publish.success"
    STATS_HANDLER_PUBLISH_FAILED = "stats.handler.publish.failed"
    STATS_HANDLER_CONNECTION_ERROR = "stats.handler.connection.error"
