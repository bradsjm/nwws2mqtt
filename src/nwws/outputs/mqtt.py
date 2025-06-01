# pyright: strict
"""MQTT output for pipeline events."""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING

import paho.mqtt.client as mqtt
from loguru import logger
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from nwws.models.events import TextProductEventData
from nwws.models.events.xml_event_data import XmlEventData
from nwws.pipeline import Output, PipelineEvent
from nwws.utils import build_topic

if TYPE_CHECKING:
    from models.mqtt_config import MqttConfig


class MQTTOutput(Output):
    """Output that publishes pipeline events to MQTT broker."""

    def __init__(self, output_id: str = "mqtt", *, config: MqttConfig) -> None:
        """Initialize the MQTT output.

        Args:
            output_id: Unique identifier for this output.
            config: MQTT configuration object.

        """
        super().__init__(output_id)
        self.config = config

        self._client: mqtt.Client | None = None
        self._connected = False
        self._connect_future: asyncio.Future[bool] | None = None
        self._published_topics: dict[str, float] = {}  # topic -> timestamp
        self._cleanup_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start MQTT client and connect to broker."""
        await super().start()

        self._client = None
        self._connected = False
        self._connect_future = None
        self._published_topics = {}
        self._cleanup_task = None

        try:
            # Create MQTT client
            self._client = mqtt.Client(client_id=self.config.mqtt_client_id)

            # Set callbacks
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect

            # Set credentials if provided
            if self.config.mqtt_username and self.config.mqtt_password:
                self._client.username_pw_set(
                    self.config.mqtt_username, self.config.mqtt_password
                )

            # Start the client loop
            self._client.loop_start()

            # Connect to broker
            logger.info(
                "Connecting to MQTT broker",
                output_id=self.output_id,
                broker=self.config.mqtt_broker,
                port=self.config.mqtt_port,
            )

            self._client.connect(self.config.mqtt_broker, self.config.mqtt_port, 60)

            # Start cleanup task if retention is enabled
            if self.config.mqtt_retain:
                self._cleanup_task = asyncio.create_task(
                    self._cleanup_expired_messages(),
                )

        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error(
                "Failed to start MQTT output",
                output_id=self.output_id,
                error=str(e),
            )
            if self._client:
                self._client.loop_stop()
                self._client = None
            raise

    async def stop(self) -> None:
        """Stop MQTT client and cleanup."""
        logger.info("Stopping MQTT output", output_id=self.output_id)

        # Stop cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task

        # Cleanup retained messages if configured
        if self.config.mqtt_retain:
            await self._cleanup_all_messages()

        if self._client:
            try:
                self._client.disconnect()
                self._client.loop_stop()
                self._connected = False
                logger.info("MQTT output stopped", output_id=self.output_id)
            except OSError as e:
                logger.error(
                    "Error stopping MQTT output",
                    output_id=self.output_id,
                    error=str(e),
                )

        await super().stop()

    async def send(self, event: PipelineEvent) -> None:
        """Send the event to MQTT broker.

        Args:
            event: The pipeline event to send.

        """
        if not (isinstance(event, (XmlEventData, TextProductEventData))):
            logger.debug(
                "Skipping unknown event",
                output_id=self.output_id,
                event_type=type(event).__name__,
            )
            return

        if not self._client or not self._connected:
            logger.warning(
                "MQTT client not connected, skipping publish",
                output_id=self.output_id,
                event_id=event.metadata.event_id,
            )
            return

        try:
            # Create topic using configured pattern and dynamic component resolution
            topics = [build_topic(event=event, prefix=self.config.mqtt_topic_prefix)]

            # Create properties for message expiry only if retain is enabled
            properties = None
            if self.config.mqtt_retain:
                properties = Properties(PacketTypes.PUBLISH)
                expiry_seconds = self.config.mqtt_message_expiry_minutes * 60
                properties.MessageExpiryInterval = expiry_seconds

            # The event's __str__ method should return a valid string representation
            payload = str(event)

            # Publish message
            for topic in topics:
                result = self._client.publish(
                    topic,
                    payload,
                    qos=self.config.mqtt_qos,
                    retain=self.config.mqtt_retain,
                    properties=properties,
                )

                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    # Track the published topic with timestamp only if retain is enabled
                    if self.config.mqtt_retain:
                        self._published_topics[topic] = time.time()
                    logger.info(
                        "Published to MQTT",
                        output_id=self.output_id,
                        event_id=event.metadata.event_id,
                        product_id=event.id,
                        topic=topic,
                        content_type=event.content_type,
                    )
                else:
                    logger.warning(
                        "Failed to publish to MQTT",
                        output_id=self.output_id,
                        event_id=event.metadata.event_id,
                        return_code=result.rc,
                        topic=topic,
                        product_id=event.id,
                        content_type=event.content_type,
                    )

        except (ConnectionError, OSError, ValueError) as e:
            logger.error(
                "Error publishing to MQTT",
                output_id=self.output_id,
                event_id=event.metadata.event_id,
                error=str(e),
            )

    @property
    def is_connected(self) -> bool:
        """Return True if MQTT client is connected."""
        return self._connected

    def _on_connect(
        self,
        _client: mqtt.Client,
        _userdata: object,
        _flags: dict[str, int],
        rc: int,
    ) -> None:
        """Handle MQTT connection."""
        if rc == 0:
            self._connected = True
            logger.info("Connected to MQTT broker", output_id=self.output_id)
        else:
            error_msg = f"Failed to connect to MQTT broker: {rc}"
            logger.error(error_msg, output_id=self.output_id)

    def _on_disconnect(self, _client: mqtt.Client, _userdata: object, rc: int) -> None:
        """Handle MQTT disconnection."""
        self._connected = False
        if rc != 0:
            logger.warning(
                "Unexpected MQTT disconnection",
                output_id=self.output_id,
                return_code=rc,
            )
        else:
            logger.info("Disconnected from MQTT broker", output_id=self.output_id)

    async def _cleanup_expired_messages(self) -> None:
        """Periodically clean up expired messages."""
        cleanup_interval = 60  # Check every minute
        expiry_seconds = self.config.mqtt_message_expiry_minutes * 60

        while True:
            try:
                await asyncio.sleep(cleanup_interval)

                if not self._connected or not self._client:
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
                        result = self._client.publish(topic, "", qos=0, retain=True)
                        if result.rc == mqtt.MQTT_ERR_SUCCESS:
                            del self._published_topics[topic]
                            logger.debug(
                                "Removed expired message from topic",
                                output_id=self.output_id,
                                topic=topic,
                            )
                        else:
                            logger.warning(
                                "Failed to remove expired message from topic",
                                output_id=self.output_id,
                                topic=topic,
                                return_code=result.rc,
                            )
                    except (ConnectionError, OSError) as e:
                        logger.error(
                            "Error removing expired message from topic",
                            output_id=self.output_id,
                            topic=topic,
                            error=str(e),
                        )

            except asyncio.CancelledError:
                break
            except (ConnectionError, OSError) as e:
                logger.error(
                    "Error in cleanup task",
                    output_id=self.output_id,
                    error=str(e),
                )

    async def _cleanup_all_messages(self) -> None:
        """Remove all tracked retained messages."""
        if not self._connected or not self._client:
            return

        logger.info(
            "Cleaning up retained messages",
            output_id=self.output_id,
            count=len(self._published_topics),
        )

        for topic in list(self._published_topics.keys()):
            try:
                # Publish empty retained message to remove it
                result = self._client.publish(topic, "", qos=0, retain=True)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.debug(
                        "Removed retained message from topic",
                        output_id=self.output_id,
                        topic=topic,
                    )
                else:
                    logger.warning(
                        "Failed to remove retained message from topic",
                        output_id=self.output_id,
                        topic=topic,
                        return_code=result.rc,
                    )
            except (ConnectionError, OSError) as e:
                logger.error(
                    "Error removing retained message from topic",
                    output_id=self.output_id,
                    topic=topic,
                    error=str(e),
                )

        self._published_topics.clear()
