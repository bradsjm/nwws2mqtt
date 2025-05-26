"""Statistics collector for NWWS2MQTT application."""

import threading
from datetime import datetime
from typing import Optional

from loguru import logger

from .models import ApplicationStats, ConnectionStats, MessageStats, OutputHandlerStats


class StatsCollector:
    """Thread-safe statistics collector."""

    def __init__(self):
        """Initialize the stats collector."""
        self._lock = threading.Lock()
        self._stats = ApplicationStats()
        logger.debug("Statistics collector initialized")

    def get_stats(self) -> ApplicationStats:
        """Get a copy of current statistics."""
        with self._lock:
            # Create a deep copy to avoid race conditions
            return ApplicationStats(
                start_time=self._stats.start_time,
                connection=ConnectionStats(
                    start_time=self._stats.connection.start_time,
                    connected_at=self._stats.connection.connected_at,
                    disconnected_at=self._stats.connection.disconnected_at,
                    total_connections=self._stats.connection.total_connections,
                    total_disconnections=self._stats.connection.total_disconnections,
                    reconnect_attempts=self._stats.connection.reconnect_attempts,
                    auth_failures=self._stats.connection.auth_failures,
                    connection_errors=self._stats.connection.connection_errors,
                    is_connected=self._stats.connection.is_connected,
                    last_ping_sent=self._stats.connection.last_ping_sent,
                    last_pong_received=self._stats.connection.last_pong_received,
                    outstanding_pings=self._stats.connection.outstanding_pings,
                ),
                messages=MessageStats(
                    total_received=self._stats.messages.total_received,
                    total_processed=self._stats.messages.total_processed,
                    total_failed=self._stats.messages.total_failed,
                    total_published=self._stats.messages.total_published,
                    last_message_time=self._stats.messages.last_message_time,
                    last_groupchat_message_time=self._stats.messages.last_groupchat_message_time,
                    product_types=self._stats.messages.product_types.copy(),
                    sources=self._stats.messages.sources.copy(),
                    afos_codes=self._stats.messages.afos_codes.copy(),
                    processing_errors=self._stats.messages.processing_errors.copy(),
                ),
                output_handlers={
                    name: OutputHandlerStats(
                        handler_type=handler.handler_type,
                        total_published=handler.total_published,
                        total_failed=handler.total_failed,
                        is_connected=handler.is_connected,
                        connected_at=handler.connected_at,
                        disconnected_at=handler.disconnected_at,
                        connection_errors=handler.connection_errors,
                        last_publish_time=handler.last_publish_time,
                    )
                    for name, handler in self._stats.output_handlers.items()
                },
            )

    # Connection tracking methods
    def on_connection_attempt(self) -> None:
        """Record a connection attempt."""
        with self._lock:
            logger.debug("Recording connection attempt")

    def on_connected(self) -> None:
        """Record successful connection."""
        with self._lock:
            now = datetime.utcnow()
            self._stats.connection.connected_at = now
            self._stats.connection.disconnected_at = None
            self._stats.connection.total_connections += 1
            self._stats.connection.is_connected = True
            logger.debug("Connection established recorded")

    def on_disconnected(self) -> None:
        """Record disconnection."""
        with self._lock:
            now = datetime.utcnow()
            self._stats.connection.disconnected_at = now
            self._stats.connection.total_disconnections += 1
            self._stats.connection.is_connected = False
            logger.debug("Disconnection recorded")

    def on_reconnect_attempt(self) -> None:
        """Record reconnection attempt."""
        with self._lock:
            self._stats.connection.reconnect_attempts += 1
            logger.debug("Reconnection attempt recorded")

    def on_auth_failure(self) -> None:
        """Record authentication failure."""
        with self._lock:
            self._stats.connection.auth_failures += 1
            logger.debug("Authentication failure recorded")

    def on_connection_error(self) -> None:
        """Record connection error."""
        with self._lock:
            self._stats.connection.connection_errors += 1
            logger.debug("Connection error recorded")

    def on_ping_sent(self) -> None:
        """Record ping sent."""
        with self._lock:
            self._stats.connection.last_ping_sent = datetime.utcnow()
            self._stats.connection.outstanding_pings += 1
            logger.debug("Ping sent recorded")

    def on_pong_received(self) -> None:
        """Record pong received."""
        with self._lock:
            self._stats.connection.last_pong_received = datetime.utcnow()
            if self._stats.connection.outstanding_pings > 0:
                self._stats.connection.outstanding_pings -= 1
            logger.debug("Pong received recorded")

    # Message tracking methods
    def on_message_received(self) -> None:
        """Record message received."""
        with self._lock:
            self._stats.messages.total_received += 1
            self._stats.messages.last_message_time = datetime.utcnow()
            logger.debug("Message received recorded")

    def on_groupchat_message_received(self) -> None:
        """Record groupchat message received."""
        with self._lock:
            self._stats.messages.last_groupchat_message_time = datetime.utcnow()
            logger.debug("Groupchat message received recorded")

    def on_message_processed(self, source: str, afos: str, product_id: Optional[str] = None) -> None:
        """Record successful message processing."""
        with self._lock:
            self._stats.messages.total_processed += 1
            if source:
                self._stats.messages.sources[source] += 1
            if afos:
                self._stats.messages.afos_codes[afos] += 1
            if product_id:
                # Extract product type from product_id (e.g., FXUS61 from FXUS61KBOU)
                product_type = product_id[:6] if len(product_id) >= 6 else product_id
                self._stats.messages.product_types[product_type] += 1
            logger.debug("Message processed recorded", source=source, afos=afos, product_id=product_id)

    def on_message_failed(self, error_type: str) -> None:
        """Record message processing failure."""
        with self._lock:
            self._stats.messages.total_failed += 1
            self._stats.messages.processing_errors[error_type] += 1
            logger.debug("Message processing failure recorded", error_type=error_type)

    def on_message_published(self) -> None:
        """Record message published to output handlers."""
        with self._lock:
            self._stats.messages.total_published += 1
            logger.debug("Message published recorded")

    # Output handler tracking methods
    def register_output_handler(self, handler_name: str, handler_type: str) -> None:
        """Register an output handler for tracking."""
        with self._lock:
            if handler_name not in self._stats.output_handlers:
                self._stats.output_handlers[handler_name] = OutputHandlerStats(
                    handler_type=handler_type
                )
                logger.debug("Output handler registered", handler_name=handler_name, handler_type=handler_type)

    def on_handler_connected(self, handler_name: str) -> None:
        """Record output handler connection."""
        with self._lock:
            if handler_name in self._stats.output_handlers:
                handler_stats = self._stats.output_handlers[handler_name]
                handler_stats.connected_at = datetime.utcnow()
                handler_stats.disconnected_at = None
                handler_stats.is_connected = True
                logger.debug("Output handler connected", handler_name=handler_name)

    def on_handler_disconnected(self, handler_name: str) -> None:
        """Record output handler disconnection."""
        with self._lock:
            if handler_name in self._stats.output_handlers:
                handler_stats = self._stats.output_handlers[handler_name]
                handler_stats.disconnected_at = datetime.utcnow()
                handler_stats.is_connected = False
                logger.debug("Output handler disconnected", handler_name=handler_name)

    def on_handler_publish_success(self, handler_name: str) -> None:
        """Record successful publish to output handler."""
        with self._lock:
            if handler_name in self._stats.output_handlers:
                handler_stats = self._stats.output_handlers[handler_name]
                handler_stats.total_published += 1
                handler_stats.last_publish_time = datetime.utcnow()
                logger.debug("Handler publish success recorded", handler_name=handler_name)

    def on_handler_publish_failed(self, handler_name: str) -> None:
        """Record failed publish to output handler."""
        with self._lock:
            if handler_name in self._stats.output_handlers:
                handler_stats = self._stats.output_handlers[handler_name]
                handler_stats.total_failed += 1
                logger.debug("Handler publish failure recorded", handler_name=handler_name)

    def on_handler_connection_error(self, handler_name: str) -> None:
        """Record output handler connection error."""
        with self._lock:
            if handler_name in self._stats.output_handlers:
                handler_stats = self._stats.output_handlers[handler_name]
                handler_stats.connection_errors += 1
                logger.debug("Handler connection error recorded", handler_name=handler_name)

    def reset_stats(self) -> None:
        """Reset all statistics."""
        with self._lock:
            self._stats = ApplicationStats()
            logger.info("Statistics reset")
