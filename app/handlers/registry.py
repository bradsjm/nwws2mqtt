"""Handler registry for managing output handlers."""

import asyncio
import threading

from loguru import logger

from app.messaging import MessageBus, StatsHandlerMessage, Topics
from app.models import OutputConfig
from app.utils import LoggingConfig

from .base import OutputHandler

type HandlerFactory = type[OutputHandler]


class HandlerRegistry:
    """
    Registry for autonomous output handlers.

    Provides centralized configuration and monitoring without
    managing handler lifecycles directly.
    """

    def __init__(self, config: OutputConfig) -> None:
        """Initialize handler registry with configuration."""
        # Ensure logging is properly configured in this thread
        LoggingConfig.ensure_configured()

        self.config = config
        self._factories: dict[str, HandlerFactory] = {}
        self._active_handlers: dict[str, OutputHandler] = {}
        self._lock = threading.Lock()
        self._is_running = False

        # Register built-in handler factories
        self._register_builtin_handlers()

    def _register_builtin_handlers(self) -> None:
        """Register built-in handler factories."""
        from .console import ConsoleOutputHandler
        from .mqtt import MQTTOutputHandler

        self.register_handler_factory("console", ConsoleOutputHandler)
        self.register_handler_factory("mqtt", MQTTOutputHandler)

    def register_handler_factory(self, name: str, factory: HandlerFactory) -> None:
        """Register a handler factory."""
        with self._lock:
            self._factories[name] = factory
            logger.debug("Registered handler factory", handler=name)

    async def start(self) -> None:
        """Start all enabled handlers."""
        # Ensure logging is properly configured in this asyncio context
        LoggingConfig.ensure_configured()

        if self._is_running:
            logger.warning("Handler registry is already running")
            return

        self._is_running = True
        logger.info("Starting handler registry")

        # Create and start handlers for enabled types
        handlers_to_start = []
        for handler_name in self.config.enabled_handlers:
            handler_name = handler_name.lower()

            if handler_name not in self._factories:
                logger.warning("Unknown handler type", handler=handler_name)
                continue

            try:
                # Create handler instance
                factory = self._factories[handler_name]
                handler = factory(self.config)

                with self._lock:
                    self._active_handlers[handler_name] = handler

                handlers_to_start.append((handler_name, handler))

                # Publish registration event
                MessageBus.publish(
                    Topics.STATS_HANDLER_REGISTERED,
                    message=StatsHandlerMessage(handler_name=handler_name, handler_type=handler_name),
                )

                logger.info("Created handler instance", handler=handler_name)

            except Exception as e:
                logger.error("Failed to create handler", handler=handler_name, error=str(e))

        # Start all handlers concurrently
        if handlers_to_start:
            start_tasks = []
            for handler_name, handler in handlers_to_start:
                start_tasks.append(self._start_handler(handler_name, handler))

            # Start handlers with error isolation
            await asyncio.gather(*start_tasks, return_exceptions=True)

        # Ensure at least one handler is running (fallback to console)
        if not self._active_handlers:
            logger.warning("No handlers started")

    async def _start_handler(self, handler_name: str, handler: OutputHandler) -> None:
        """Start a single handler with error isolation."""
        # Ensure logging is properly configured for this handler's execution context
        LoggingConfig.ensure_configured()

        try:
            await handler.start()

            if handler.is_connected:
                MessageBus.publish(Topics.STATS_HANDLER_CONNECTED, message=StatsHandlerMessage(handler_name=handler_name))
                logger.info("Handler started successfully", handler=handler_name)
            else:
                logger.warning("Handler started but not connected", handler=handler_name)

        except Exception as e:
            logger.error("Failed to start handler", handler=handler_name, error=str(e))

            # Remove failed handler from active list
            with self._lock:
                self._active_handlers.pop(handler_name, None)

            MessageBus.publish(Topics.STATS_HANDLER_CONNECTION_ERROR, message=StatsHandlerMessage(handler_name=handler_name))

    async def stop(self) -> None:
        """Stop all active handlers."""
        if not self._is_running:
            return

        logger.info("Stopping handler registry")
        self._is_running = False

        # Stop all handlers concurrently
        stop_tasks = []
        with self._lock:
            for handler_name, handler in self._active_handlers.items():
                stop_tasks.append(self._stop_handler(handler_name, handler))

        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

        with self._lock:
            self._active_handlers.clear()

        logger.info("Handler registry stopped")

    async def _stop_handler(self, handler_name: str, handler: OutputHandler) -> None:
        """Stop a single handler with error isolation."""
        try:
            await handler.stop()

            MessageBus.publish(Topics.STATS_HANDLER_DISCONNECTED, message=StatsHandlerMessage(handler_name=handler_name))

            logger.info("Handler stopped", handler=handler_name)

        except Exception as e:
            logger.error("Error stopping handler", handler=handler_name, error=str(e))

    @property
    def active_handler_names(self) -> list[str]:
        """Get list of active handler names."""
        with self._lock:
            return list(self._active_handlers.keys())

    @property
    def connected_handlers_count(self) -> int:
        """Return the number of connected handlers."""
        with self._lock:
            return sum(1 for handler in self._active_handlers.values() if handler.is_connected)

    def get_handler_status(self) -> dict[str, bool]:
        """Get connection status for all active handlers."""
        with self._lock:
            return {name: handler.is_connected for name, handler in self._active_handlers.items()}
