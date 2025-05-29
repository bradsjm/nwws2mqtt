"""MQTT output handler for NWWS-OI data."""

import asyncio
import contextlib
import time

import paho.mqtt.client as mqtt
from loguru import logger
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from models.product import TextProductModel
from utils import product_to_json

from .base import OutputHandler


class MQTTConfigurationError(ValueError):
    """MQTT broker configuration is missing or invalid."""

    def __init__(self) -> None:
        """Initialize the error with a message."""
        super().__init__("MQTT_BROKER must be configured for MQTT output handler")


class MQTTOutputHandler(OutputHandler):
    """output handler that publishes to MQTT broker."""

    async def _start_handler(self) -> None:
        """Start MQTT client and connect to broker."""
        if not self.config.mqtt_broker:
            raise MQTTConfigurationError

        self.client: mqtt.Client | None = None
        self._connected = False
        self._connect_future: asyncio.Future[bool] | None = None
        self._published_topics: dict[str, float] = {}  # topic -> timestamp
        self._cleanup_task: asyncio.Task[None] | None = None

        try:
            # Create MQTT client
            self.client = mqtt.Client(client_id=self.config.mqtt_client_id)

            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish

            # Set credentials if provided
            if self.config.mqtt_username and self.config.mqtt_password:
                self.client.username_pw_set(self.config.mqtt_username, self.config.mqtt_password)

            # Start the client loop
            self.client.loop_start()

            # Connect to broker
            self._connect_future = asyncio.Future()
            logger.info(
                "Connecting to MQTT broker",
                handler="mqtt",
                broker=self.config.mqtt_broker,
                port=self.config.mqtt_port,
            )

            self.client.connect(self.config.mqtt_broker, self.config.mqtt_port, 60)

            # Wait for connection with timeout
            await asyncio.wait_for(self._connect_future, timeout=30.0)
            logger.info("MQTT handler connected successfully", handler="mqtt")

            # Start cleanup task if retention is enabled
            if self.config.mqtt_retain:
                self._cleanup_task = asyncio.create_task(self._cleanup_expired_messages())

        except (ConnectionError, TimeoutError) as e:
            logger.error("Failed to start MQTT handler", handler="mqtt", error=str(e))
            if self.client:
                self.client.loop_stop()
                self.client = None
            raise

    async def _stop_handler(self) -> None:
        """Stop MQTT client and cleanup."""
        logger.info("Stopping MQTT handler", handler="mqtt")

        # Stop cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task

        # Cleanup retained messages if configured
        if self.config.mqtt_retain:
            await self._cleanup_all_messages()

        if self.client:
            try:
                self.client.disconnect()
                self.client.loop_stop()
                self._connected = False
                logger.info("MQTT handler stopped", handler="mqtt")
            except OSError as e:
                logger.error("Error stopping MQTT handler", handler="mqtt", error=str(e))

    async def publish(self, source: str, afos: str, product_id: str, text_product: TextProductModel, subject: str = "") -> None:
        """Publish structured data to MQTT topic."""
        if not self.client or not self._connected:
            logger.warning("MQTT client not connected, skipping publish", handler="mqtt", subject=subject)
            return

        try:
            # Create topic based on source, AFOS, and product ID
            topic = f"{self.config.mqtt_topic_prefix}/{source}/{afos}/{product_id}"

            # Create properties for message expiry only if retain is enabled
            properties = None
            if self.config.mqtt_retain:
                properties = Properties(PacketTypes.PUBLISH)
                expiry_seconds = self.config.mqtt_message_expiry_minutes * 60
                properties.MessageExpiryInterval = expiry_seconds

            json_data = product_to_json(text_product)

            # Publish message
            result = self.client.publish(
                topic,
                json_data,
                qos=self.config.mqtt_qos,
                retain=self.config.mqtt_retain,
                properties=properties,
            )

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                # Track the published topic with timestamp only if retain is enabled
                if self.config.mqtt_retain:
                    self._published_topics[topic] = time.time()
                logger.debug(
                    "Published product to MQTT topic",
                    handler="mqtt",
                    product_id=product_id,
                    topic=topic,
                )
            else:
                error_msg = f"Failed to publish to MQTT: {result.rc}"
                logger.warning(
                    error_msg,
                    handler="mqtt",
                    return_code=result.rc,
                    topic=topic,
                    source=source,
                    afos=afos,
                    product_id=product_id,
                    subject=subject,
                )

        except (ConnectionError, OSError, ValueError) as e:
            logger.error("Error publishing to MQTT", handler="mqtt", error=str(e))

    @property
    def is_connected(self) -> bool:
        """Return True if MQTT client is connected."""
        return self._connected

    def _on_connect(self, _client: mqtt.Client, _userdata: object, _flags: dict[str, int], rc: int) -> None:
        """Handle MQTT connection."""
        if rc == 0:
            self._connected = True
            logger.info("Connected to MQTT broker", handler="mqtt")
            if self._connect_future and not self._connect_future.done():
                self._connect_future.set_result(True)
        else:
            error_msg = f"Failed to connect to MQTT broker: {rc}"
            logger.error(error_msg, handler="mqtt")
            if self._connect_future and not self._connect_future.done():
                self._connect_future.set_exception(ConnectionError(error_msg))

    def _on_disconnect(self, _client: mqtt.Client, _userdata: object, rc: int) -> None:
        """Handle MQTT disconnection."""
        self._connected = False
        if rc != 0:
            logger.warning("Unexpected MQTT disconnection", handler="mqtt", return_code=rc)
        else:
            logger.info("Disconnected from MQTT broker", handler="mqtt")

    def _on_publish(self, _client: mqtt.Client, _userdata: object, mid: int) -> None:
        """Handle MQTT publish confirmation."""
        logger.debug("MQTT message published successfully", handler="mqtt", message_id=mid)

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
                expired_topics: list[str] = []

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
                            logger.debug("Removed expired message from topic", handler="mqtt", topic=topic)
                        else:
                            logger.warning(
                                "Failed to remove expired message from topic",
                                handler="mqtt",
                                topic=topic,
                                return_code=result.rc,
                            )
                    except (ConnectionError, OSError) as e:
                        logger.error(
                            "Error removing expired message from topic",
                            handler="mqtt",
                            topic=topic,
                            error=str(e),
                        )

            except asyncio.CancelledError:
                break
            except (ConnectionError, OSError) as e:
                logger.error("Error in cleanup task", handler="mqtt", error=str(e))

    async def _cleanup_all_messages(self) -> None:
        """Remove all tracked retained messages."""
        if not self._connected or not self.client:
            return

        logger.info("Cleaning up retained messages", handler="mqtt", count=len(self._published_topics))

        for topic in list(self._published_topics.keys()):
            try:
                # Publish empty retained message to remove it
                result = self.client.publish(topic, "", qos=0, retain=True)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.debug("Removed retained message from topic", handler="mqtt", topic=topic)
                else:
                    logger.warning(
                        "Failed to remove retained message from topic",
                        handler="mqtt",
                        topic=topic,
                        return_code=result.rc,
                    )
            except (ConnectionError, OSError) as e:
                logger.error(
                    "Error removing retained message from topic",
                    handler="mqtt",
                    topic=topic,
                    error=str(e),
                )

        self._published_topics.clear()
