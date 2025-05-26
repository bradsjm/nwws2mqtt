"""Output handlers for NWWS-OI data."""

import asyncio
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from loguru import logger

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False


@dataclass
class OutputConfig:
    """Configuration for output handlers."""
    enabled_handlers: list[str]
    mqtt_broker: str | None = None
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_topic_prefix: str = "nwws"
    mqtt_qos: int = 1
    mqtt_retain: bool = False
    mqtt_client_id: str = "nwws-oi-client"

    @classmethod
    def from_env(cls) -> "OutputConfig":
        """Create output config from environment variables."""
        # Parse enabled handlers from comma-separated string
        handlers_str = os.getenv("OUTPUT_HANDLERS", "console")
        enabled_handlers = [h.strip() for h in handlers_str.split(",") if h.strip()]

        return cls(
            enabled_handlers=enabled_handlers,
            mqtt_broker=os.getenv("MQTT_BROKER"),
            mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
            mqtt_username=os.getenv("MQTT_USERNAME"),
            mqtt_password=os.getenv("MQTT_PASSWORD"),
            mqtt_topic_prefix=os.getenv("MQTT_TOPIC_PREFIX", "nwws"),
            mqtt_qos=int(os.getenv("MQTT_QOS", "1")),
            mqtt_retain=os.getenv("MQTT_RETAIN", "false").lower() == "true",
            mqtt_client_id=os.getenv("MQTT_CLIENT_ID", "nwws-oi-client"),
        )


class OutputHandler(ABC):
    """Abstract base class for output handlers."""

    def __init__(self, config: OutputConfig) -> None:
        """Initialize the output handler."""
        self.config = config

    @abstractmethod
    async def publish(self, product_id: str, structured_data: str, subject: str = "") -> None:
        """Publish structured data to the output destination."""

    @abstractmethod
    async def start(self) -> None:
        """Start the output handler (initialize connections, etc.)."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the output handler (cleanup connections, etc.)."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if the handler is connected and ready to publish."""


class ConsoleOutputHandler(OutputHandler):
    """Output handler that prints to console."""

    async def publish(self, product_id: str, structured_data: str, subject: str = "") -> None:
        """Print structured data to console."""
        try:
            # Use logger instead of print to be consistent with the rest of the application
            logger.info(f"Product {product_id}: {structured_data}")
            logger.debug(f"Published product {product_id} to console")
        except Exception as e:
            logger.error(f"Failed to publish to console: {e}")

    async def start(self) -> None:
        """Start console handler (no-op)."""
        logger.info("Console output handler started")

    async def stop(self) -> None:
        """Stop console handler (no-op)."""
        logger.info("Console output handler stopped")

    @property
    def is_connected(self) -> bool:
        """Console is always available."""
        return True


class MQTTOutputHandler(OutputHandler):
    """Output handler that publishes to MQTT broker."""

    def __init__(self, config: OutputConfig) -> None:
        """Initialize MQTT output handler."""
        super().__init__(config)
        
        if not MQTT_AVAILABLE:
            raise ImportError("paho-mqtt is required for MQTT output handler")
        
        if not config.mqtt_broker:
            raise ValueError("MQTT_BROKER must be configured for MQTT output handler")

        self.client: mqtt.Client | None = None
        self._connected = False
        self._connect_future: asyncio.Future | None = None

    async def start(self) -> None:
        """Start MQTT client and connect to broker."""
        try:
            # Create MQTT client
            self.client = mqtt.Client(client_id=self.config.mqtt_client_id)
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish

            # Set credentials if provided
            if self.config.mqtt_username and self.config.mqtt_password:
                self.client.username_pw_set(
                    self.config.mqtt_username,
                    self.config.mqtt_password
                )

            # Connect to broker
            logger.info(f"Connecting to MQTT broker {self.config.mqtt_broker}:{self.config.mqtt_port}")
            
            # Create future for connection
            self._connect_future = asyncio.Future()
            
            # Start the client loop in a separate thread
            self.client.loop_start()
            
            # Connect
            result = self.client.connect(
                self.config.mqtt_broker,
                self.config.mqtt_port,
                keepalive=60
            )
            
            if result != mqtt.MQTT_ERR_SUCCESS:
                def _raise_connection_error():
                    raise ConnectionError(f"Failed to connect to MQTT broker: {result}")
                _raise_connection_error()

            # Wait for connection to complete
            await asyncio.wait_for(self._connect_future, timeout=30.0)
            logger.info("MQTT output handler started and connected")

        except Exception as e:
            logger.error(f"Failed to start MQTT handler: {e}")
            if self.client:
                self.client.loop_stop()
            raise

    async def stop(self) -> None:
        """Stop MQTT client and disconnect from broker."""
        if self.client:
            try:
                logger.info("Stopping MQTT output handler")
                self.client.disconnect()
                self.client.loop_stop()
                self._connected = False
                logger.info("MQTT output handler stopped")
            except Exception as e:
                logger.error(f"Error stopping MQTT handler: {e}")

    async def publish(self, product_id: str, structured_data: str, subject: str = "") -> None:
        """Publish structured data to MQTT topic."""
        if not self.client or not self._connected:
            logger.warning("MQTT client not connected, skipping publish")
            return

        try:
            # Create topic based on product ID
            topic = f"{self.config.mqtt_topic_prefix}/{product_id}"
            
            # Publish message
            result = self.client.publish(
                topic,
                structured_data,
                qos=self.config.mqtt_qos,
                retain=self.config.mqtt_retain
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published product {product_id} to MQTT topic {topic}")
            else:
                logger.warning(f"Failed to publish to MQTT: {result.rc}")

        except Exception as e:
            logger.error(f"Error publishing to MQTT: {e}")

    @property
    def is_connected(self) -> bool:
        """Return True if MQTT client is connected."""
        return self._connected

    def _on_connect(self, _client: Any, _userdata: Any, _flags: dict, rc: int) -> None:
        """Handle MQTT connection."""
        if rc == 0:
            self._connected = True
            logger.info("Connected to MQTT broker")
            if self._connect_future and not self._connect_future.done():
                self._connect_future.set_result(True)
        else:
            error_msg = f"Failed to connect to MQTT broker: {rc}"
            logger.error(error_msg)
            if self._connect_future and not self._connect_future.done():
                self._connect_future.set_exception(ConnectionError(error_msg))

    def _on_disconnect(self, _client: Any, _userdata: Any, rc: int) -> None:
        """Handle MQTT disconnection."""
        self._connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection: {rc}")
        else:
            logger.info("Disconnected from MQTT broker")

    def _on_publish(self, _client: Any, _userdata: Any, mid: int) -> None:
        """Handle MQTT publish confirmation."""
        logger.debug(f"MQTT message {mid} published successfully")


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

    async def publish(self, product_id: str, structured_data: str, subject: str = "") -> None:
        """Publish data to all enabled handlers."""
        if not self.handlers:
            logger.warning("No output handlers available")
            return

        # Publish to all handlers concurrently
        tasks = []
        for handler in self.handlers:
            if handler.is_connected:
                tasks.append(handler.publish(product_id, structured_data, subject))
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
