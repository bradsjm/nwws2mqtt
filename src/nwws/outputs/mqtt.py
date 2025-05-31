# pyright: strict
"""MQTT output for pipeline events."""

from __future__ import annotations

import asyncio
import contextlib
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import paho.mqtt.client as mqtt
from loguru import logger
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from nwws.models.events import TextProductEventData
from nwws.pipeline import Output, PipelineEvent

if TYPE_CHECKING:
    from models.mqtt_config import MqttConfig


@dataclass
class MQTTOutputConfig:
    """Configuration for MQTT output."""

    broker: str
    port: int = 1883
    username: str | None = None
    password: str | None = None
    topic_prefix: str = "nwws"
    topic_pattern: str = "{prefix}/{cccc}/{product_type}/{awipsid}/{product_id}"
    qos: int = 1
    retain: bool = False
    client_id: str = "nwws-oi-pipeline-client"
    message_expiry_minutes: int = 60


class MQTTOutput(Output):
    """Output that publishes pipeline events to MQTT broker."""

    def __init__(self, output_id: str = "mqtt", *, config: MQTTOutputConfig) -> None:
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

    @classmethod
    def from_config(cls, output_id: str, config: MqttConfig) -> MQTTOutput:
        """Create MQTT output from configuration.

        Args:
            output_id: Unique identifier for this output.
            config: MQTT configuration object.

        Returns:
            Configured MQTT output instance.

        Raises:
            MQTTConfigurationError: If broker is not configured.

        """
        mqtt_config = MQTTOutputConfig(
            broker=config.mqtt_broker or "localhost",
            port=config.mqtt_port or 1883,
            username=config.mqtt_username,
            password=config.mqtt_password,
            topic_prefix=config.mqtt_topic_prefix,
            topic_pattern=getattr(
                config,
                "mqtt_topic_pattern",
                "{prefix}/{cccc}/{product_type}/{awipsid}/{product_id}",
            ),
            qos=config.mqtt_qos,
            retain=config.mqtt_retain,
            client_id=config.mqtt_client_id,
            message_expiry_minutes=config.mqtt_message_expiry_minutes,
        )
        return cls(output_id=output_id, config=mqtt_config)

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
            self._client = mqtt.Client(client_id=self.config.client_id)

            # Set callbacks
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect

            # Set credentials if provided
            if self.config.username and self.config.password:
                self._client.username_pw_set(self.config.username, self.config.password)

            # Start the client loop
            self._client.loop_start()

            # Connect to broker
            logger.info(
                "Connecting to MQTT broker",
                output_id=self.output_id,
                broker=self.config.broker,
                port=self.config.port,
            )

            self._client.connect(self.config.broker, self.config.port, 60)

            # Start cleanup task if retention is enabled
            if self.config.retain:
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
        if self.config.retain:
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
        if not isinstance(event, TextProductEventData):
            logger.debug(
                "Skipping non-text product event",
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
            topic = self._build_topic(event)

            # Create properties for message expiry only if retain is enabled
            properties = None
            if self.config.retain:
                properties = Properties(PacketTypes.PUBLISH)
                expiry_seconds = self.config.message_expiry_minutes * 60
                properties.MessageExpiryInterval = expiry_seconds

            payload = event.product.model_dump_json(
                exclude_defaults=True,
                by_alias=True,
            )

            # Publish message
            result = self._client.publish(
                topic,
                payload,
                qos=self.config.qos,
                retain=self.config.retain,
                properties=properties,
            )

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                # Track the published topic with timestamp only if retain is enabled
                if self.config.retain:
                    self._published_topics[topic] = time.time()
                logger.info(
                    "Published to MQTT",
                    output_id=self.output_id,
                    event_id=event.metadata.event_id,
                    product_id=event.id,
                    topic=topic,
                )
            else:
                logger.warning(
                    "Failed to publish to MQTT",
                    output_id=self.output_id,
                    event_id=event.metadata.event_id,
                    return_code=result.rc,
                    topic=topic,
                    product_id=event.id,
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
        expiry_seconds = self.config.message_expiry_minutes * 60

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

    def _get_product_type_indicator(self, event: TextProductEventData) -> str:
        """Determine the product type indicator for topic structure.

        Uses VTEC phenomena.significance if available, otherwise first 3 letters of AWIPS ID.

        Args:
            event: The text product event data.

        Returns:
            Product type indicator string for topic construction.

        """
        # Check for VTEC codes in product segments
        if event.product.segments:
            for segment in event.product.segments:
                if segment.vtec:
                    # Use the first VTEC record's phenomena and significance
                    first_vtec = segment.vtec[0]
                    return f"{first_vtec.phenomena}.{first_vtec.significance}"

        # Fallback to first 3 letters of AWIPS ID for non-VTEC products
        if event.awipsid and len(event.awipsid) >= 3:
            return event.awipsid[:3].upper()

        # Final fallback for products without VTEC or sufficient AWIPS ID
        return "GENERAL"

    def _build_topic(self, event: TextProductEventData) -> str:
        """Build MQTT topic using configured pattern and event data.

        Args:
            event: The text product event data.

        Returns:
            Formatted MQTT topic string.

        """
        # Get dynamic components
        product_type = self._get_product_type_indicator(event)
        awipsid = event.awipsid if event.awipsid else "NO_AWIPSID"

        # Build topic components dictionary for pattern substitution
        topic_components = {
            "prefix": self.config.topic_prefix.strip(),
            "cccc": event.cccc.strip(),
            "product_type": product_type,
            "awipsid": awipsid.strip(),
            "product_id": event.id.strip(),
        }

        # Format topic using configured pattern
        return self.config.topic_pattern.format(**topic_components)


def mqtt_factory_create(output_id: str, **config: Any) -> MQTTOutput:
    """Create MQTT output from configuration.

    Args:
        output_id: Unique identifier for the output.
        **config: Configuration parameters for the MQTT output.

    Returns:
        Configured MQTT output instance.

    """
    broker = config.pop("broker", "localhost")
    topic_pattern = config.pop(
        "topic_pattern", "{prefix}/{cccc}/{product_type}/{awipsid}/{product_id}"
    )
    mqtt_config = MQTTOutputConfig(broker=broker, topic_pattern=topic_pattern, **config)
    return MQTTOutput(output_id=output_id, config=mqtt_config)
