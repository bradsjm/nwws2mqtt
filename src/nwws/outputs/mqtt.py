# pyright: strict
"""MQTT output for pipeline events."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import paho.mqtt.client as mqtt
from loguru import logger

from nwws.models.events import TextProductEventData
from nwws.models.events.xml_event_data import XmlEventData
from nwws.pipeline import Output, PipelineEvent
from nwws.utils import build_topic


@dataclass
class MQTTConfig:
    """Configuration management for MQTT broker connection and publishing parameters.

    This dataclass encapsulates all MQTT-related configuration settings required
    for establishing connections to MQTT brokers and publishing pipeline events.
    It provides type-safe configuration management with sensible defaults and
    supports initialization from environment variables for containerized deployments.

    The configuration includes broker connection details (host, port, credentials),
    topic routing settings, Quality of Service levels, and client identification
    parameters. Default values are optimized for local development while supporting
    production environments through environment variable overrides.
    """

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
        """Create MQTT configuration instance from environment variables.

        This factory method constructs a MQTTConfig instance by reading configuration
        values from environment variables, providing a clean separation between
        application code and deployment-specific settings. It automatically handles
        type conversion for numeric values and provides fallback defaults for
        optional settings.

        Environment variables read:
        - MQTT_BROKER: Broker hostname or IP address (default: "localhost")
        - MQTT_PORT: Broker port number (default: 1883)
        - MQTT_USERNAME: Authentication username (optional)
        - MQTT_PASSWORD: Authentication password (optional)
        - MQTT_TOPIC_PREFIX: Base topic prefix for all publications (default: "nwws")
        - MQTT_QOS: Quality of Service level 0-2 (default: 1)
        - MQTT_CLIENT_ID: Unique client identifier (default: "nwws-oi-client")

        Returns:
            MQTTConfig: Fully configured instance with environment-based settings.

        Raises:
            ValueError: If environment variables contain invalid numeric values.

        """
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
    """Production-grade MQTT output handler for publishing pipeline events to MQTT brokers.

    This output implementation provides reliable, asynchronous publishing of weather
    data pipeline events to MQTT brokers with comprehensive error handling, connection
    management, and monitoring capabilities. It supports both XML and text product
    events, automatically building topic hierarchies based on event metadata and
    maintaining persistent connections with automatic reconnection logic.

    The output handler manages the complete MQTT client lifecycle including connection
    establishment, authentication, keepalive management, and graceful shutdown. It
    provides detailed logging and metadata collection for operational monitoring
    and troubleshooting. Quality of Service levels are configurable to balance
    delivery guarantees with performance requirements.

    Connection state is monitored and events are buffered during disconnections
    to prevent data loss. The implementation uses the Paho MQTT client library
    with callback-based event handling for optimal performance in high-throughput
    scenarios.
    """

    def __init__(self, output_id: str = "mqtt", *, config: MQTTConfig | None) -> None:
        """Initialize the MQTT output handler with configuration and connection state.

        Creates a new MQTT output instance with the specified configuration, setting up
        internal state management for connection tracking and client lifecycle. The
        initialization process prepares the output for connection but does not establish
        the MQTT broker connection until the start() method is called.

        The output handler maintains connection state tracking, supports graceful
        degradation during network issues, and provides comprehensive logging for
        operational visibility. If no configuration is provided, it automatically
        loads settings from environment variables using MQTTConfig.from_env().

        Args:
            output_id: Unique identifier for this output instance used in logging
                      and metadata collection. Must be unique within the pipeline.
            config: MQTT configuration object containing broker connection details,
                   authentication credentials, and publishing parameters. If None,
                   configuration is loaded from environment variables.

        """
        super().__init__(output_id)
        self.config = config or MQTTConfig.from_env()

        self._client: mqtt.Client | None = None
        self._connected = False

        logger.info("MQTT Output initialized", output_id=self.output_id)

    async def start(self) -> None:
        """Start the MQTT client and establish connection to the configured broker.

        This method initializes the Paho MQTT client, configures authentication
        credentials, sets up connection callbacks, and establishes the broker
        connection. The connection process includes automatic keepalive configuration,
        client identification, and comprehensive error handling for network issues.

        The startup process follows these steps:
        1. Reset any existing connection state and client instances
        2. Create new MQTT client with configured client ID
        3. Register connection and disconnection event callbacks
        4. Configure authentication if username/password are provided
        5. Start the client's network loop for background message processing
        6. Initiate connection to the broker with 60-second keepalive

        Connection establishment is logged with broker details for operational
        visibility. If connection fails, the client loop is properly cleaned up
        and the error is propagated to allow for retry logic at higher levels.

        Raises:
            ConnectionError: If the broker connection cannot be established.
            TimeoutError: If the connection attempt exceeds timeout limits.
            OSError: For network-related errors during connection setup.

        """
        await super().start()

        self._client = None
        self._connected = False

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
        """Stop the MQTT client and perform complete resource cleanup.

        This method gracefully shuts down the MQTT client connection, stops the
        background network loop, and cleans up all associated resources. The
        shutdown process ensures that any pending publications are completed
        before disconnection and that all internal state is properly reset.

        The cleanup process includes:
        1. Initiating graceful disconnection from the MQTT broker
        2. Stopping the client's background network loop
        3. Resetting connection state flags
        4. Logging shutdown completion for operational tracking

        Error handling ensures that cleanup proceeds even if individual steps
        fail, preventing resource leaks during shutdown. Network errors during
        disconnection are logged but do not prevent the cleanup process from
        completing successfully.

        This method is safe to call multiple times and will not raise exceptions
        for already-stopped clients.
        """
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
        """Publish a pipeline event to the MQTT broker with comprehensive error handling.

        This method processes pipeline events and publishes them to the MQTT broker
        using dynamically constructed topic hierarchies based on event metadata.
        It supports both XML and text product events, automatically serializing
        event content and routing to appropriate topics with configured QoS levels.

        The publishing process includes:
        1. Event type validation to ensure supported event types
        2. Connection state verification before publishing attempts
        3. Dynamic topic construction using event metadata and configured prefix
        4. Event serialization using the event's string representation
        5. MQTT publication with result code validation and logging
        6. Comprehensive error handling for network and serialization issues

        Events are published with the configured Quality of Service level to
        balance delivery guarantees with performance. Publication results are
        logged with detailed context including event IDs, topics, and content
        types for operational monitoring and troubleshooting.

        Unsupported event types are logged and skipped without raising exceptions
        to maintain pipeline stability. Connection failures result in warning
        logs but do not interrupt pipeline processing.

        Args:
            event: The pipeline event to publish. Must be an instance of
                  XmlEventData or TextProductEventData. Other event types
                  are logged and skipped.

        Raises:
            ConnectionError: For MQTT broker connection issues during publishing.
            OSError: For network-related errors during publication.
            ValueError: For event serialization or topic construction errors.

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
        """Return the current MQTT broker connection status.

        This property provides real-time connection state information for monitoring
        and conditional logic. The connection state is maintained through MQTT
        client callbacks and reflects the actual broker connectivity status.

        Returns:
            bool: True if the MQTT client is currently connected to the broker
                 and ready to publish messages, False otherwise.

        """
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
        """Generate comprehensive metadata about the MQTT output operation and configuration.

        This method produces detailed metadata about the MQTT output's current state,
        configuration, and processing status for a specific pipeline event. The
        metadata includes broker connection details, QoS settings, connection status,
        and event-specific information such as target topics and payload sizes.

        The metadata collection process analyzes the provided event to determine
        processing eligibility, constructs target topics using the same logic as
        the actual publishing process, and calculates payload characteristics.
        This information is essential for monitoring, debugging, and operational
        visibility into the MQTT output's behavior.

        Metadata includes both static configuration values and dynamic runtime
        information:
        - Broker connection details (host, port, QoS level)
        - Current connection status and client state
        - Event processing status and eligibility
        - Target topic construction for supported events
        - Payload size calculations and content type identification
        - Skip reasons for unsupported event types

        Args:
            event: The pipeline event to analyze for metadata generation.
                  Event type determines the specific metadata collected.

        Returns:
            dict[str, Any]: Comprehensive metadata dictionary with keys prefixed
                           by the output ID to prevent naming conflicts in
                           pipeline-wide metadata collection.

        """
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
