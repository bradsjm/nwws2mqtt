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
