"""MQTT output handler for NWWS-OI data."""

import asyncio
import time
from typing import Any

from loguru import logger

from .base import OutputHandler, OutputConfig

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False


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
        self._published_topics: dict[str, float] = {}  # topic -> timestamp
        self._cleanup_task: asyncio.Task | None = None

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
                raise ConnectionError(f"Failed to connect to MQTT broker: {result}")

            # Wait for connection to complete
            await asyncio.wait_for(self._connect_future, timeout=30.0)
            
            # Start cleanup task only if retain is enabled
            if self.config.mqtt_retain:
                self._cleanup_task = asyncio.create_task(self._cleanup_expired_messages())
            
            logger.info("MQTT output handler started and connected")

        except Exception as e:
            logger.error(f"Failed to start MQTT handler: {e}")
            if self.client:
                self.client.loop_stop()
            raise

    async def stop(self) -> None:
        """Stop MQTT client and disconnect from broker."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Clean up all retained messages only if retain is enabled
        if self.config.mqtt_retain:
            await self._cleanup_all_messages()

        if self.client:
            try:
                logger.info("Stopping MQTT output handler")
                self.client.disconnect()
                self.client.loop_stop()
                self._connected = False
                logger.info("MQTT output handler stopped")
            except Exception as e:
                logger.error(f"Error stopping MQTT handler: {e}")

    async def publish(self, source: str, afos: str, product_id: str, structured_data: str, subject: str = "") -> None:
        """Publish structured data to MQTT topic."""
        if not self.client or not self._connected:
            logger.warning("MQTT client not connected, skipping publish")
            return

        try:
            # Create topic based on source, AFOS, and product ID
            topic = f"{self.config.mqtt_topic_prefix}/{source}/{afos}/{product_id}"
            
            # Create properties for message expiry only if retain is enabled
            properties = None
            if self.config.mqtt_retain:
                properties = mqtt.Properties(mqtt.PacketTypes.PUBLISH)
                expiry_seconds = self.config.mqtt_message_expiry_minutes * 60
                properties.MessageExpiryInterval = expiry_seconds
            
            # Publish message
            result = self.client.publish(
                topic,
                structured_data,
                qos=self.config.mqtt_qos,
                retain=self.config.mqtt_retain,
                properties=properties
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                # Track the published topic with timestamp only if retain is enabled
                if self.config.mqtt_retain:
                    self._published_topics[topic] = time.time()
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

    async def _cleanup_expired_messages(self) -> None:
        """Periodically clean up expired messages."""
        cleanup_interval = 60  # Check every minute
        expiry_seconds = self.config.mqtt_message_expiry_minutes * 60
        
        while True:
            try:
                await asyncio.sleep(cleanup_interval)
                
                if not self._connected or not self.client:
                    continue
                
                current_time = time.time()
                expired_topics = []
                
                # Find expired topics
                for topic, publish_time in self._published_topics.items():
                    if current_time - publish_time >= expiry_seconds:
                        expired_topics.append(topic)
                
                # Remove expired messages
                for topic in expired_topics:
                    try:
                        # Publish empty retained message to remove it
                        result = self.client.publish(topic, "", qos=0, retain=True)
                        if result.rc == mqtt.MQTT_ERR_SUCCESS:
                            del self._published_topics[topic]
                            logger.debug(f"Removed expired message from topic {topic}")
                        else:
                            logger.warning(f"Failed to remove expired message from topic {topic}: {result.rc}")
                    except Exception as e:
                        logger.error(f"Error removing expired message from topic {topic}: {e}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

    async def _cleanup_all_messages(self) -> None:
        """Remove all tracked retained messages."""
        if not self._connected or not self.client:
            return
            
        logger.info(f"Cleaning up {len(self._published_topics)} retained messages")
        
        for topic in list(self._published_topics.keys()):
            try:
                # Publish empty retained message to remove it
                result = self.client.publish(topic, "", qos=0, retain=True)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.debug(f"Removed retained message from topic {topic}")
                else:
                    logger.warning(f"Failed to remove retained message from topic {topic}: {result.rc}")
            except Exception as e:
                logger.error(f"Error removing retained message from topic {topic}: {e}")
        
        self._published_topics.clear()
