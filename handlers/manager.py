"""Output manager for coordinating multiple output handlers."""

import asyncio

from loguru import logger

from .base import OutputConfig, OutputHandler
from .console import ConsoleOutputHandler
from .mqtt import MQTTOutputHandler


class OutputManager:
    """Manages multiple output handlers."""

    def __init__(self, config: OutputConfig) -> None:
        """Initialize output manager with configuration."""
        self.config = config
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
                    logger.warning(f"Unknown output handler: {handler_name}")
                    continue
                
                self.handlers.append(handler)
                logger.info(f"Initialized {handler_name} output handler")
                
            except Exception as e:
                logger.error(f"Failed to initialize {handler_name} handler: {e}")

        if not self.handlers:
            # Fallback to console if no handlers are configured
            logger.warning("No output handlers configured, falling back to console")
            self.handlers.append(ConsoleOutputHandler(self.config))

    async def start(self) -> None:
        """Start all output handlers."""
        logger.info(f"Starting {len(self.handlers)} output handlers")
        for handler in self.handlers:
            try:
                await handler.start()
            except Exception as e:
                logger.error(f"Failed to start handler {type(handler).__name__}: {e}")

    async def stop(self) -> None:
        """Stop all output handlers."""
        logger.info("Stopping output handlers")
        for handler in self.handlers:
            try:
                await handler.stop()
            except Exception as e:
                logger.error(f"Failed to stop handler {type(handler).__name__}: {e}")

    async def publish(self, wfo: str, afos: str, product_id: str, structured_data: str, subject: str = "") -> None:
        """Publish data to all enabled handlers."""
        if not self.handlers:
            logger.warning("No output handlers available")
            return

        # Publish to all handlers concurrently
        tasks = []
        for handler in self.handlers:
            if handler.is_connected:
                tasks.append(handler.publish(wfo, afos, product_id, structured_data, subject))
            else:
                logger.warning(f"Handler {type(handler).__name__} is not connected, skipping")

        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error publishing to handlers: {e}")
        else:
            logger.warning("No connected handlers available for publishing")

    @property
    def connected_handlers_count(self) -> int:
        """Return the number of connected handlers."""
        return sum(1 for handler in self.handlers if handler.is_connected)
