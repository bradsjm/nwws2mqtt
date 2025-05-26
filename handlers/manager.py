"""Output manager for coordinating multiple output handlers."""

import asyncio

from loguru import logger

from .base import OutputConfig, OutputHandler
from .console import ConsoleOutputHandler
from .mqtt import MQTTOutputHandler


class OutputManager:
    """Manages multiple output handlers."""

    def __init__(self, config: OutputConfig, stats_collector=None) -> None:
        """Initialize output manager with configuration."""
        self.config = config
        self.stats_collector = stats_collector
        self.handlers: list[OutputHandler] = []
        self._initialize_handlers()

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
                
                # Register handler with stats collector
                if self.stats_collector:
                    self.stats_collector.register_output_handler(handler_name, handler_name)
                
                logger.info("Initialized output handler", handler=handler_name)
                
            except Exception as e:
                logger.error("Failed to initialize output handler", handler=handler_name, error=str(e))

        if not self.handlers:
            # Fallback to console if no handlers are configured
            logger.warning("No output handlers configured, falling back to console")
            handler = ConsoleOutputHandler(self.config)
            self.handlers.append(handler)
            if self.stats_collector:
                self.stats_collector.register_output_handler("console", "console")

    async def start(self) -> None:
        """Start all output handlers."""
        logger.info("Starting output handlers", count=len(self.handlers))
        for handler in self.handlers:
            try:
                await handler.start()
                # Record handler connection
                if self.stats_collector and handler.is_connected:
                    handler_name = type(handler).__name__.replace("OutputHandler", "").lower()
                    self.stats_collector.on_handler_connected(handler_name)
            except Exception as e:
                handler_name = type(handler).__name__
                logger.error("Failed to start handler", handler=handler_name, error=str(e))
                if self.stats_collector:
                    handler_name = type(handler).__name__.replace("OutputHandler", "").lower()
                    self.stats_collector.on_handler_connection_error(handler_name)

    async def stop(self) -> None:
        """Stop all output handlers."""
        logger.info("Stopping output handlers")
        for handler in self.handlers:
            try:
                await handler.stop()
                # Record handler disconnection
                if self.stats_collector:
                    handler_name = type(handler).__name__.replace("OutputHandler", "").lower()
                    self.stats_collector.on_handler_disconnected(handler_name)
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
            if self.stats_collector:
                self.stats_collector.on_handler_publish_success(handler_name)
        except Exception as e:
            logger.error("Error publishing to handler", handler=handler_name, error=str(e))
            if self.stats_collector:
                self.stats_collector.on_handler_publish_failed(handler_name)
            raise

    @property
    def connected_handlers_count(self) -> int:
        """Return the number of connected handlers."""
        return sum(1 for handler in self.handlers if handler.is_connected)
