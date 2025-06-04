# pyright: strict
"""MQTT output for pipeline events."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import paho.mqtt.client as mqtt
from loguru import logger

from nwws.models.events import TextProductEventData
from nwws.models.events.xml_event_data import XmlEventData
from nwws.pipeline import Output, PipelineEvent
from nwws.utils import build_topic

if TYPE_CHECKING:
    import asyncio


@dataclass
class MQTTConfig:
    """Configuration class for output handlers."""

    # MQTT Configuration
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_topic_prefix: str = "nwws"
    mqtt_qos: int = 1
    mqtt_client_id: str = "nwws-oi-client"

    @classmethod
    def from_env(cls) -> MQTTConfig:
        """Create output config from environment variables."""
        return cls(
            mqtt_broker=os.getenv("MQTT_BROKER", "localhost"),
            mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
            mqtt_username=os.getenv("MQTT_USERNAME"),
            mqtt_password=os.getenv("MQTT_PASSWORD"),
            mqtt_topic_prefix=os.getenv("MQTT_TOPIC_PREFIX", "nwws"),
            mqtt_qos=int(os.getenv("MQTT_QOS", "1")),
            mqtt_client_id=os.getenv("MQTT_CLIENT_ID", "nwws-oi-client"),
        )


class MQTTOutput(Output):
    """Output that publishes pipeline events to MQTT broker."""

    def __init__(self, output_id: str = "mqtt", *, config: MQTTConfig | None) -> None:
        """Initialize the MQTT output.

        Args:
            output_id: Unique identifier for this output.
            config: MQTT configuration object.

        """
        super().__init__(output_id)
        self.config = config or MQTTConfig.from_env()

        self._client: mqtt.Client | None = None
        self._connected = False
        self._connect_future: asyncio.Future[bool] | None = None

        logger.info("MQTT Output initialized", output_id=self.output_id)

    async def start(self) -> None:
        """Start MQTT client and connect to broker."""
        await super().start()

        self._client = None
        self._connected = False
        self._connect_future = None

        try:
            # Create MQTT client
            self._client = mqtt.Client(client_id=self.config.mqtt_client_id)

            # Set callbacks
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect

            # Set credentials if provided
            if self.config.mqtt_username and self.config.mqtt_password:
                self._client.username_pw_set(self.config.mqtt_username, self.config.mqtt_password)

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

            # The event's __str__ method should return a valid string representation
            payload = str(event)

            # Publish message
            for topic in topics:
                result = self._client.publish(
                    topic,
                    payload,
                    qos=self.config.mqtt_qos,
                )

                if result.rc == mqtt.MQTT_ERR_SUCCESS:
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

    def get_output_metadata(self, event: PipelineEvent) -> dict[str, Any]:
        """Get metadata about the MQTT output operation."""
        metadata = super().get_output_metadata(event)

        # Add MQTT-specific metadata
        metadata[f"{self.output_id}_broker"] = self.config.mqtt_broker
        metadata[f"{self.output_id}_port"] = self.config.mqtt_port
        metadata[f"{self.output_id}_connected"] = self._connected
        metadata[f"{self.output_id}_qos"] = self.config.mqtt_qos

        if isinstance(event, (XmlEventData, TextProductEventData)):
            # Build the topic that would be used
            topic = build_topic(event=event, prefix=self.config.mqtt_topic_prefix)
            metadata[f"{self.output_id}_target_topic"] = topic
            metadata[f"{self.output_id}_event_processed"] = True
            metadata[f"{self.output_id}_payload_size"] = len(str(event))
            metadata[f"{self.output_id}_content_type"] = event.content_type
        else:
            metadata[f"{self.output_id}_event_processed"] = False
            metadata[f"{self.output_id}_skip_reason"] = "unsupported_event_type"

        return metadata
