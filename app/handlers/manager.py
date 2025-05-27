"""Output manager for coordinating multiple output handlers."""

import asyncio

from loguru import logger

from .base import OutputConfig, OutputHandler
from .console import ConsoleOutputHandler
from .mqtt import MQTTOutputHandler
from messaging import MessageBus, ProductMessage, Topics
from messaging.message_bus import StatsHandlerMessage


class OutputManager:
    """Manages multiple output handlers."""

    def __init__(self, config: OutputConfig) -> None:
        """Initialize output manager with configuration."""
        self.config = config
        self.handlers: list[OutputHandler] = []
        self._initialize_handlers()
        self._subscribe_to_topics()

    def _initialize_handlers(self) -> None:
        """Initialize enabled output handlers."""
        for handler_type in self.config.enabled_handlers:
            handler_name = handler_type.lower()
            
            try:
                if handler_name == "console":
                    handler = ConsoleOutputHandler(self.config)
                elif handler_name == "mqtt":
                    handler = MQTTOutputHandler(self.config)
                else:
                    logger.warning("Unknown output handler", handler=handler_name)
                    continue
                
                self.handlers.append(handler)
                
                # Publish handler registration event
                MessageBus.publish(
                    Topics.STATS_HANDLER_REGISTERED,
                    message=StatsHandlerMessage(handler_name=handler_name, handler_type=handler_name)
                )
                
                logger.info("Initialized output handler", handler=handler_name)
                
            except Exception as e:
                logger.error("Failed to initialize output handler", handler=handler_name, error=str(e))

        if not self.handlers:
            # Fallback to console if no handlers are configured
            logger.warning("No output handlers configured, falling back to console")
            handler = ConsoleOutputHandler(self.config)
            self.handlers.append(handler)
            
            # Publish handler registration event for fallback console
            MessageBus.publish(
                Topics.STATS_HANDLER_REGISTERED,
                message=StatsHandlerMessage(handler_name="console", handler_type="console")
            )

    def _subscribe_to_topics(self) -> None:
        """Subscribe to pubsub topics."""
        MessageBus.subscribe(Topics.PRODUCT_RECEIVED, self._on_product_received)
        logger.info("Subscribed to product topics")

    def _on_product_received(self, message: ProductMessage) -> None:
        """Handle received product messages from pubsub."""
        try:
            # Create a task to publish the message asynchronously
            import asyncio
            import threading
            
            def publish_data():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        self.publish(
                            message.source, 
                            message.afos, 
                            message.product_id, 
                            message.structured_data, 
                            message.subject
                        )
                    )
                except Exception as e:
                    logger.error("Failed to publish product message", 
                               product_id=message.product_id, error=str(e))
                finally:
                    loop.close()
            
            # Run in a separate thread to avoid blocking the pubsub system
            publish_thread = threading.Thread(target=publish_data, daemon=True)
            publish_thread.start()
            
        except Exception as e:
            logger.error("Error handling product message", 
                        product_id=getattr(message, 'product_id', 'unknown'), 
                        error=str(e))

    async def start(self) -> None:
        """Start all output handlers."""
        logger.info("Starting output handlers", count=len(self.handlers))
        for handler in self.handlers:
            try:
                await handler.start()
                # Publish handler connection event
                if handler.is_connected:
                    handler_name = type(handler).__name__.replace("OutputHandler", "").lower()
                    MessageBus.publish(
                        Topics.STATS_HANDLER_CONNECTED,
                        message=StatsHandlerMessage(handler_name=handler_name)
                    )
            except Exception as e:
                handler_name = type(handler).__name__
                logger.error("Failed to start handler", handler=handler_name, error=str(e))
                handler_name = type(handler).__name__.replace("OutputHandler", "").lower()
                MessageBus.publish(
                    Topics.STATS_HANDLER_CONNECTION_ERROR,
                    message=StatsHandlerMessage(handler_name=handler_name)
                )

    async def stop(self) -> None:
        """Stop all output handlers."""
        logger.info("Stopping output handlers")
        
        # Unsubscribe from pubsub topics
        try:
            MessageBus.unsubscribe(Topics.PRODUCT_RECEIVED, self._on_product_received)
            logger.info("Unsubscribed from product topics")
        except Exception as e:
            logger.error("Error unsubscribing from topics", error=str(e))
        
        for handler in self.handlers:
            try:
                await handler.stop()
                # Publish handler disconnection event
                handler_name = type(handler).__name__.replace("OutputHandler", "").lower()
                MessageBus.publish(
                    Topics.STATS_HANDLER_DISCONNECTED,
                    message=StatsHandlerMessage(handler_name=handler_name)
                )
            except Exception as e:
                handler_name = type(handler).__name__
                logger.error("Failed to stop handler", handler=handler_name, error=str(e))

    async def publish(self, wfo: str, afos: str, product_id: str, structured_data: str, subject: str = "") -> None:
        """Publish data to all enabled handlers."""
        if not self.handlers:
            logger.warning("No output handlers available")
            return

        # Publish to all handlers concurrently
        tasks = []
        for handler in self.handlers:
            if handler.is_connected:
                tasks.append(self._publish_with_stats_tracking(handler, wfo, afos, product_id, structured_data, subject))
            else:
                handler_name = type(handler).__name__
                logger.warning("Handler not connected, skipping", handler=handler_name)

        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.error("Error publishing to handlers", error=str(e))
        else:
            logger.warning("No connected handlers available for publishing")

    async def _publish_with_stats_tracking(self, handler: OutputHandler, wfo: str, afos: str, product_id: str, structured_data: str, subject: str = "") -> None:
        """Publish to handler with stats tracking."""
        handler_name = type(handler).__name__.replace("OutputHandler", "").lower()
        try:
            await handler.publish(wfo, afos, product_id, structured_data, subject)
            # Publish handler publish success event
            MessageBus.publish(
                Topics.STATS_HANDLER_PUBLISH_SUCCESS,
                message=StatsHandlerMessage(handler_name=handler_name)
            )
        except Exception as e:
            logger.error("Error publishing to handler", handler=handler_name, error=str(e))
            # Publish handler publish failure event
            MessageBus.publish(
                Topics.STATS_HANDLER_PUBLISH_FAILED,
                message=StatsHandlerMessage(handler_name=handler_name)
            )
            raise

    @property
    def connected_handlers_count(self) -> int:
        """Return the number of connected handlers."""
        return sum(1 for handler in self.handlers if handler.is_connected)
