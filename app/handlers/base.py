"""Base output handler that subscribes to pubsub directly."""

import asyncio
from abc import ABC, abstractmethod

from loguru import logger

from app.messaging import MessageBus, ProductMessage, StatsHandlerMessage, Topics
from app.models import OutputConfig
from app.utils import LoggingConfig


class OutputHandler(ABC):
    """
    Base class for autonomous output handlers.

    Each handler subscribes directly to the pubsub system and manages
    its own lifecycle independently for better isolation and reliability.
    """

    def __init__(self, config: OutputConfig) -> None:
        """Initialize the autonomous output handler."""
        # Ensure logging is properly configured
        LoggingConfig.ensure_configured()

        self.config = config
        self._is_started = False
        self._handler_name = self.__class__.__name__.replace("OutputHandler", "").lower()

    async def start(self) -> None:
        """Start the handler and subscribe to topics."""
        if self._is_started:
            logger.warning("Handler already started", handler=self._handler_name)
            return

        try:
            # Initialize the specific handler implementation
            await self._start_handler()

            # Subscribe to product messages
            MessageBus.subscribe(Topics.PRODUCT_RECEIVED, self._on_product_received)

            self._is_started = True
            logger.info("Autonomous handler started", handler=self._handler_name)

        except Exception as e:
            logger.error("Failed to start autonomous handler", handler=self._handler_name, error=str(e))
            raise

    async def stop(self) -> None:
        """Stop the handler and unsubscribe from topics."""
        if not self._is_started:
            return

        try:
            # Unsubscribe from topics
            MessageBus.unsubscribe(Topics.PRODUCT_RECEIVED, self._on_product_received)

            # Stop the specific handler implementation
            await self._stop_handler()

            self._is_started = False
            logger.info("Autonomous handler stopped", handler=self._handler_name)

        except Exception as e:
            logger.error("Error stopping autonomous handler", handler=self._handler_name, error=str(e))

    def _on_product_received(self, message: ProductMessage) -> None:
        """Handle received product messages from pubsub."""
        if not self._is_started or not self.is_connected:
            return

        try:
            # Try to get the current event loop, if none exists, create and schedule in a new thread
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, create task directly
                loop.create_task(self._process_product_message(message))
            except RuntimeError:
                # No running loop, schedule in a thread
                import threading

                def run_async():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        new_loop.run_until_complete(self._process_product_message(message))
                    except Exception as e:
                        logger.error(
                            "Failed to process product message in thread",
                            handler=self._handler_name,
                            product_id=getattr(message, "product_id", "unknown"),
                            error=str(e),
                        )
                    finally:
                        new_loop.close()

                thread = threading.Thread(target=run_async, daemon=True)
                thread.start()

        except Exception as e:
            logger.error(
                "Error handling product message",
                handler=self._handler_name,
                product_id=getattr(message, "product_id", "unknown"),
                error=str(e),
            )

    async def _process_product_message(self, message: ProductMessage) -> None:
        """Process a product message asynchronously."""
        try:
            await self.publish(message.source, message.afos, message.product_id, message.structured_data, message.subject)

            # Publish success event
            MessageBus.publish(Topics.STATS_HANDLER_PUBLISH_SUCCESS, message=StatsHandlerMessage(handler_name=self._handler_name))

        except Exception as e:
            logger.error(
                "Failed to publish product message", handler=self._handler_name, product_id=message.product_id, error=str(e)
            )

            # Publish failure event
            MessageBus.publish(Topics.STATS_HANDLER_PUBLISH_FAILED, message=StatsHandlerMessage(handler_name=self._handler_name))

    @abstractmethod
    async def _start_handler(self) -> None:
        """Start the specific handler implementation."""

    @abstractmethod
    async def _stop_handler(self) -> None:
        """Stop the specific handler implementation."""

    @abstractmethod
    async def publish(self, source: str, afos: str, product_id: str, structured_data: str, subject: str = "") -> None:
        """Publish structured data to the output destination."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if the handler is connected and ready to publish."""
