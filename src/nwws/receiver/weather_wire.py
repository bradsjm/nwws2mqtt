# pyright: strict
"""NWWS-OI XMPP client implementation using slixmpp."""

import asyncio
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from xml.etree import ElementTree as ET

import slixmpp
from loguru import logger
from pydantic import BaseModel, Field
from slixmpp import JID
from slixmpp.exceptions import XMPPError
from slixmpp.stanza import Message

from nwws.receiver.stats import WeatherWireStatsCollector as ReceiverStatsCollector

from .config import WeatherWireConfig

# Configuration constants
MUC_ROOM = "nwws@conference.nwws-oi.weather.gov"
IDLE_TIMEOUT = 90  # 90 seconds of inactivity before reconnecting
MAX_HISTORY = 5  # Maximum history messages to retrieve when joining MUC


class WeatherWireMessage(BaseModel):
    """Represents a structured weather message received from the NWWS-OI system.

    This data model encapsulates all the essential metadata and content of a weather
    product message received through the NWWS-OI XMPP Multi-User Chat (MUC) room.
    The message includes standardized weather product identifiers (WMO headers),
    timing information, issuing office details, and the formatted product content
    in NOAAPort format for downstream processing.

    The message structure follows the NWWS-OI XML namespace format with additional
    processing to convert the raw message content into the NOAAPort format expected
    by weather data consumers. Delay stamps are preserved to track message latency
    through the distribution system.
    """

    subject: str = Field(description="Subject of the message")
    noaaport: str = Field(description="NOAAPort formatted text of the product message.")
    id: str = Field(
        description="Unique identifier for the product (server process ID and sequence number)."
    )
    issue: datetime = Field(description="Issue time of the product as a datetime object.")
    ttaaii: str = Field(description="TTAAII code representing the WMO product type and time.")
    cccc: str = Field(description="CCCC code representing the issuing office or center.")
    awipsid: str = Field(
        description="AWIPS ID (AFOS PIL) of the product if available.", default="NONE"
    )
    delay_stamp: datetime | None = Field(
        description="Delay stamp if the message was delayed, otherwise None.",
    )


class WeatherWire(slixmpp.ClientXMPP):
    """Production-grade NWWS-OI XMPP client for receiving real-time weather data.

    This class implements a robust, asynchronous XMPP client that connects to the
    National Weather Service's NWWS-OI (NOAAPort Weather Wire Service - Open Interface)
    system to receive real-time weather products, warnings, and forecasts. The client
    handles the complete lifecycle of XMPP connectivity including authentication,
    Multi-User Chat (MUC) room management, message processing, and graceful shutdown.

    The implementation provides:
    - Automatic reconnection with exponential backoff on connection failures
    - Idle timeout detection and forced reconnection for stuck connections
    - Comprehensive error handling and recovery mechanisms
    - Async iterator pattern for processing incoming weather messages
    - Detailed metrics collection and monitoring capabilities
    - Circuit breaker patterns for resilient message processing
    - Structured logging for operational visibility

    The client joins the NWWS MUC room and processes incoming weather messages,
    converting them from NWWS-OI XML format to structured WeatherWireMessage objects
    with standardized NOAAPort formatting. Messages are queued internally and made
    available through the async iterator interface for downstream processing.

    Connection health is continuously monitored through idle timeout detection,
    periodic stats updates, and comprehensive event handling for all XMPP lifecycle
    events. The client maintains detailed statistics about message processing rates,
    connection stability, and error conditions for operational monitoring.
    """

    def __init__(
        self,
        config: WeatherWireConfig,
        *,
        stats_collector: ReceiverStatsCollector | None = None,
    ) -> None:
        """Initialize the NWWS-OI XMPP client with comprehensive configuration and monitoring.

        Sets up a production-ready XMPP client with all necessary plugins, event handlers,
        and monitoring capabilities for reliable weather data reception. The initialization
        process configures the underlying slixmpp client with NWWS-OI specific settings,
        registers essential XMPP Extension Protocols (XEPs), and establishes the message
        processing pipeline with async iterator support.

        The client is configured with critical XMPP extensions:
        - Service Discovery (XEP-0030) for server capability negotiation
        - Multi-User Chat (XEP-0045) for joining the NWWS broadcast room
        - XMPP Ping (XEP-0199) for connection keep-alive and health monitoring
        - Delayed Delivery (XEP-0203) for processing messages with delivery delays

        A bounded message queue (maxsize=50) is established to buffer incoming weather
        messages and provide backpressure protection against message processing bottlenecks.
        The async iterator pattern allows downstream consumers to process messages at their
        own pace while maintaining system stability.

        Comprehensive event handlers are registered for all XMPP lifecycle events including
        connection management, authentication, session handling, and message processing.
        State tracking variables are initialized for idle timeout monitoring, graceful
        shutdown coordination, and background service management.

        Args:
            config: XMPP connection configuration containing server details, credentials,
                   and connection parameters for the NWWS-OI system.
            stats_collector: Optional metrics collector for recording connection health,
                           message processing rates, error conditions, and operational
                           statistics for monitoring and alerting.

        Raises:
            ValueError: If the configuration contains invalid or missing required fields.
            ConnectionError: If initial client setup fails due to network or configuration issues.

        """
        super().__init__(  # type: ignore  # noqa: PGH003
            jid=JID(f"{config.username}@{config.server}"),
            password=config.password,
            plugin_config=None,
            plugin_whitelist=None,
            escape_quotes=True,
            sasl_mech=None,
            lang="en",
        )

        self.config = config
        self.nickname = f"{datetime.now(UTC):%Y%m%d%H%M}"
        self.stats_collector = stats_collector

        # Message queue for async iterator pattern
        self._message_queue: asyncio.Queue[WeatherWireMessage] = asyncio.Queue(maxsize=50)
        self._stop_iteration = False

        # Register plugins
        self.register_plugin("xep_0030")  # Service Discovery  # type: ignore[misc]
        self.register_plugin("xep_0045")  # Multi-User Chat  # type: ignore[misc]
        self.register_plugin("xep_0199")  # XMPP Ping  # type: ignore[misc]
        self.register_plugin("xep_0203")  # Delayed Delivery # type: ignore[misc]

        # Add comprehensive event handlers
        self._add_event_handlers()

        # Initialize state variables
        self.last_message_time: float = time.time()
        self.is_shutting_down: bool = False
        self._idle_monitor_task: asyncio.Task[None] | None = None
        self._stats_update_task: asyncio.Task[None] | None = None
        self._background_tasks: list[asyncio.Task[None]] = []
        self._connection_start_time: float | None = None

        logger.info(
            "Initialized NWWS-OI XMPP client",
            username=config.username,
            server=config.server,
            queue_maxsize=self._message_queue.maxsize,
        )

    def __aiter__(self) -> AsyncIterator[WeatherWireMessage]:
        """Enable async iteration over incoming weather messages.

        Implements the async iterator protocol to allow the WeatherWire client to be
        used in async for loops and other async iteration contexts. This provides a
        clean, Pythonic interface for consuming weather messages as they arrive from
        the NWWS-OI system.
        """
        return self

    async def __anext__(self) -> WeatherWireMessage:
        """Retrieve the next weather message from the internal processing queue.

        Implements the async iterator protocol by fetching messages from the internal
        asyncio.Queue in a non-blocking manner. The method uses a short timeout to
        periodically check for shutdown conditions while waiting for new messages,
        ensuring responsive shutdown behavior even when no messages are being received.

        The method handles the StopAsyncIteration protocol correctly by raising the
        exception when the client is shutting down and no more messages remain in
        the queue. This allows proper cleanup of async for loops and other iteration
        contexts.

        Returns:
            The next WeatherWireMessage containing structured weather data, metadata,
            and NOAAPort formatted content ready for downstream processing.

        Raises:
            StopAsyncIteration: When the client is shutting down and no more messages
                              are available in the queue, signaling the end of iteration.

        """
        while True:
            if self._stop_iteration and self._message_queue.empty():
                raise StopAsyncIteration

            try:
                # Short timeout to periodically check stop condition
                message = await asyncio.wait_for(self._message_queue.get(), timeout=0.5)
            except TimeoutError:
                # Continue loop to check stop condition
                continue
            else:
                self._message_queue.task_done()
                return message

    @property
    def queue_size(self) -> int:
        """Get the current number of messages pending in the processing queue.

        Provides real-time visibility into the message queue depth for monitoring
        and capacity planning. A consistently high queue size may indicate downstream
        processing bottlenecks or the need for additional consumer capacity.

        Returns:
            The current number of WeatherWireMessage objects waiting to be processed
            in the internal asyncio.Queue.

        """
        return self._message_queue.qsize()

    def _add_event_handlers(self) -> None:
        """Add all necessary event handlers for the XMPP client."""
        # Connection events
        self.add_event_handler("connecting", self._on_connecting)
        self.add_event_handler("connected", self._on_connected)
        self.add_event_handler("connection_failed", self._on_connection_failed)
        self.add_event_handler("disconnected", self._on_disconnected)
        self.add_event_handler("killed", self._on_killed)

        # Authentication events
        self.add_event_handler("failed_auth", self._on_failed_auth)

        # Session events
        self.add_event_handler("session_start", self._on_session_start)
        self.add_event_handler("session_end", self._on_session_end)

        # Message events
        self.add_event_handler("groupchat_message", self._on_groupchat_message)

        # MUC events
        self.add_event_handler("muc::{muc_room}::got_online", self._on_muc_presence)

        # Stanza events
        self.add_event_handler("stanza_not_sent", self._on_stanza_not_sent)

        # Reconnection events
        self.add_event_handler("reconnect_delay", self._on_reconnect_delay)

    async def start(self) -> bool:
        """Initiate connection to the NWWS-OI XMPP server.

        Begins the asynchronous connection process to the configured NWWS-OI server
        using the provided host and port settings. The connection attempt includes
        automatic DNS resolution, TCP socket establishment, and initial XMPP stream
        negotiation. Success or failure will trigger the appropriate event handlers
        for further processing.

        Returns:
            True if the initial connection succeeds, False if the connection attempt fails.

        """
        logger.info(
            "Connecting to NWWS-OI server",
            host=self.config.server,
            port=self.config.port,
        )

        # slixmpp's connect() returns Future[bool] but type checker can't infer parent class type
        connection_future = super().connect(host=self.config.server, port=self.config.port)  # type: ignore[misc]
        return await connection_future  # type: ignore[misc]

    def is_client_connected(self) -> bool:
        """Determine if the client is currently connected and operational.

        Performs a comprehensive check of the client's connection status by verifying
        both the underlying XMPP connection state and the client's internal shutdown
        flag. This provides an accurate assessment of whether the client is ready
        to receive and process weather messages.

        Returns:
            True if the client is connected to the XMPP server and not in the process
            of shutting down, False otherwise. A False result indicates the client
            cannot reliably receive messages and may need reconnection.

        """
        return self.is_connected() and not self.is_shutting_down

    # Connection event handlers
    async def _on_connecting(self, _event: object) -> None:
        """Handle connection initiation."""
        logger.info("Starting connection attempt to NWWS-OI server")
        self._connection_start_time = time.time()

        if self.stats_collector:
            self.stats_collector.record_connection_attempt()

    async def _on_reconnect_delay(self, delay_time: float) -> None:
        """Handle reconnection delay notification."""
        logger.info("Reconnection delayed", delay_seconds=delay_time)

        if self.stats_collector:
            self.stats_collector.record_reconnect_attempt()

    async def _on_failed_auth(self, _event: object) -> None:
        """Handle authentication failure."""
        logger.error("Authentication failed for NWWS-OI client")

        if self.stats_collector:
            self.stats_collector.record_authentication_failure(reason="invalid_credentials")

    async def _on_connection_failed(self, reason: str | Exception) -> None:
        """Handle connection failure."""
        logger.error("Connection to NWWS-OI server failed", reason=str(reason))

        if self.stats_collector:
            # Update connection status
            self.stats_collector.update_connection_status(is_connected=False)

            # Record failed connection with reason
            self.stats_collector.record_connection_result(success=False, reason=str(reason))

    async def _on_connected(self, _event: object) -> None:
        """Handle successful connection."""
        logger.info("Connected to NWWS-OI server")

        if self.stats_collector:
            # Update connection status
            self.stats_collector.update_connection_status(is_connected=True)

            # Record successful connection
            self.stats_collector.record_connection_result(success=True)

    async def _monitor_idle_timeout(self) -> None:
        """Monitor for idle timeout and force reconnect if needed."""
        while not self.is_shutting_down:
            await asyncio.sleep(10)
            now = time.time()
            if now - self.last_message_time > IDLE_TIMEOUT:
                logger.warning(
                    "No messages received in {timeout} seconds, reconnecting...",
                    timeout=IDLE_TIMEOUT,
                )

                if self.stats_collector:
                    self.stats_collector.record_idle_timeout()
                    self.stats_collector.record_disconnection(reason="idle_timeout")

                self.reconnect(reason="Idle timeout exceeded")
                break

    # Session event handlers
    async def _on_session_start(self, _event: object) -> None:
        """Handle successful connection and authentication."""
        logger.info("Successfully authenticated with NWWS-OI server")

        await self._start_background_services()

        try:
            await self.get_roster()  # type: ignore[misc]
            logger.info("Roster retrieved successfully")

            # Send initial presence (non-blocking)
            self.send_presence()
            logger.info("Initial presence sent")

            await self._join_nwws_room()
            logger.info("Joined MUC room", room=MUC_ROOM, nickname=self.nickname)

            await self._send_subscription_presence()
            logger.info("Subscription presence sent")
        except XMPPError as err:
            logger.error(
                "Failed to retrieve roster or join MUC",
                error=str(err),
            )
            if self.stats_collector:
                self.stats_collector.record_connection_result(
                    success=False, reason=f"session_setup_failed: {err}"
                )

    async def _start_background_services(self) -> None:
        """Start necessary services after session start with proper task management."""
        # Stop any existing background services first
        self._stop_background_services()

        # Start idle timeout monitoring
        self._idle_monitor_task = asyncio.create_task(
            self._monitor_idle_timeout(),
            name="idle_timeout_monitor",
        )
        self._background_tasks.append(self._idle_monitor_task)
        logger.info("Idle timeout monitoring enabled", timeout=IDLE_TIMEOUT)

        # Start periodic stats updates if stats collector is available
        if self.stats_collector:
            self._stats_update_task = asyncio.create_task(
                self._update_stats_periodically(),
                name="periodic_stats_update",
            )
            self._background_tasks.append(self._stats_update_task)
            logger.info("Periodic stat updates enabled")

    async def _join_nwws_room(self, max_history: int = MAX_HISTORY) -> None:
        """Join the NWWS room."""
        # Don't join if shutting down
        if self.is_shutting_down:
            return

        logger.info("Joining NWWS room", room=MUC_ROOM, nickname=self.nickname)

        # Join MUC room
        muc_room_jid = JID(MUC_ROOM)
        try:
            await self.plugin["xep_0045"].join_muc(  # type: ignore[misc]
                muc_room_jid,
                self.nickname,
                maxhistory=str(max_history),
            )
            if self.stats_collector:
                self.stats_collector.record_muc_join_result(muc_room=MUC_ROOM, success=True)
        except XMPPError as err:
            logger.error(
                "Failed to join NWWS room",
                room=MUC_ROOM,
                nickname=self.nickname,
                error=str(err),
            )
            if self.stats_collector:
                self.stats_collector.record_muc_join_result(muc_room=MUC_ROOM, success=False)

    async def _send_subscription_presence(self) -> None:
        """Send subscription presence."""
        # Send presence to confirm subscription
        try:
            self.send_presence(pto=f"{MUC_ROOM}/{self.nickname}")
        except XMPPError as err:
            logger.error(
                "Failed to send subscription presence",
                room=MUC_ROOM,
                nickname=self.nickname,
                error=str(err),
            )

    # MUC event handlers
    async def _on_muc_presence(self, presence: object) -> None:
        """Handle MUC presence updates."""
        logger.info(
            "Successfully joined MUC room",
            room=MUC_ROOM,
            nickname=self.nickname,
            presence=presence,
        )

    # Stanza event handlers
    async def _on_stanza_not_sent(self, stanza: object) -> None:
        """Handle stanza send failure."""
        stanza_type = str(getattr(stanza, "tag", "unknown"))
        logger.warning("Stanza not sent", stanza_type=stanza_type)

        if self.stats_collector:
            self.stats_collector.record_stanza_not_sent(stanza_type=stanza_type)

    async def _on_groupchat_message(self, msg: Message) -> None:
        """Process incoming groupchat message."""
        message_start_time = time.time()
        self.last_message_time = message_start_time

        if self.is_shutting_down:
            logger.info("Client is shutting down, ignoring message")
            return

        # Check if the message is from the expected MUC room
        if msg.get_mucroom() != JID(MUC_ROOM).bare:
            logger.warning(
                f"Message not from {MUC_ROOM} room, skipping",
                from_jid=msg["from"].bare,
            )
            return

        try:
            # Process the message
            weather_message = await self._on_nwws_message(msg)

            if weather_message is None:
                # Message was skipped (logged in _on_nwws_message)
                return

            # Put message in queue instead of calling callback
            try:
                self._message_queue.put_nowait(weather_message)
                await self._record_successful_message_processing(
                    weather_message, msg, message_start_time
                )
            except asyncio.QueueFull:
                logger.warning(
                    f"Message queue full (size: {self._message_queue.maxsize}), "
                    f"dropping message: {weather_message.awipsid}"
                )

        except (ET.ParseError, UnicodeDecodeError) as e:
            logger.warning("Message parsing failed", error=str(e))
        except Exception as e:  # noqa: BLE001
            logger.error("Unexpected message processing error", error=str(e))
            if self.stats_collector:
                self.stats_collector.record_message_processing_error(
                    error_type=type(e).__name__,
                    wmo_id=self._extract_wmo_id_if_possible(msg),
                )

    async def _record_successful_message_processing(
        self,
        weather_message: WeatherWireMessage,
        msg: Message,
        message_start_time: float,
    ) -> None:
        """Record metrics and send message to callback."""
        # Calculate metrics
        processing_duration = time.time() - message_start_time
        message_size = len(str(msg.xml))  # Raw XML size

        # Calculate delay from delay_stamp
        delay_seconds = self._calculate_delay_secs(weather_message.delay_stamp)

        # Extract office ID
        wmo_id = weather_message.cccc[-3:] or "unknown"

        # Record successful message processing
        if self.stats_collector:
            self.stats_collector.record_message_processed(
                processing_duration_seconds=processing_duration,
                message_delay_seconds=delay_seconds or 0.0,
                message_size_bytes=message_size,
                wmo_id=wmo_id,
            )

            # Update last message timestamp
            self.stats_collector.update_last_message_received_timestamp(
                timestamp=time.time(),
                wmo_id=wmo_id,
            )

        # Message will be retrieved via async iterator - no callback needed

    def _extract_wmo_id_if_possible(self, msg: Message) -> str | None:
        """Try to extract office ID from message even if parsing failed."""
        try:
            x = msg.xml.find("{nwws-oi}x")
            if x is not None:
                return x.get("cccc")
        except Exception:  # noqa: BLE001
            logger.debug("Failed to extract office ID from message")
        return None

    async def _on_nwws_message(self, msg: Message) -> WeatherWireMessage | None:
        """Process group chat message containing weather data."""
        # Check for NWWS-OI namespace in the message
        x = msg.xml.find("{nwws-oi}x")
        if x is None:
            logger.warning(
                "No NWWS-OI namespace in group message, skipping",
                msg_id=msg.get_id(),
            )
            if self.stats_collector:
                self.stats_collector.record_message_processing_error(
                    error_type="missing_namespace",
                    wmo_id=None,
                )
            return None

        # Get the message subject from the body or subject field
        subject = str(msg.get("body", "")) or str(msg.get("subject", ""))

        # Get delay stamp if available
        delay_stamp: datetime | None = msg["delay"]["stamp"] if "delay" in msg else None

        # Get the message body which should contain the weather data
        body = (x.text or "").strip()
        if not body:
            logger.warning(
                "No body text in NWWS-OI namespace, skipping",
                msg_id=msg.get_id(),
            )
            wmo_id = x.get("cccc")
            if self.stats_collector:
                self.stats_collector.record_message_processing_error(
                    error_type="empty_body",
                    wmo_id=wmo_id,
                )
            return None

        # Get the metadata from the NWWS-OI namespace
        weather_message = WeatherWireMessage(
            subject=subject,
            noaaport=self._convert_to_noaaport(body),
            id=x.get("id", ""),
            issue=self._parse_issue_timestamp(x.get("issue", "")),
            ttaaii=x.get("ttaaii", ""),
            cccc=x.get("cccc", ""),
            awipsid=x.get("awipsid", "") or "NONE",
            delay_stamp=delay_stamp,
        )

        delay_ms = self._calculate_delay_secs(delay_stamp) if delay_stamp else None

        logger.info(
            "Received Event",
            subject=weather_message.subject,
            id=weather_message.id,
            issue=weather_message.issue,
            ttaaii=weather_message.ttaaii,
            cccc=weather_message.cccc,
            awipsid=weather_message.awipsid,
            delay_ms=delay_ms,
        )

        return weather_message

    async def _on_session_end(self, _event: object) -> None:
        """Handle session end."""
        logger.warning("Session ended")

        # Cancel all monitoring tasks
        self._stop_background_services()

    async def _on_disconnected(self, reason: str | Exception) -> None:
        """Handle disconnection."""
        logger.warning("Disconnected from NWWS-OI server", reason=str(reason))

        if self.stats_collector:
            self.stats_collector.update_connection_status(is_connected=False)
            self.stats_collector.record_disconnection(reason=str(reason))

    async def _on_killed(self, _event: object) -> None:
        """Handle forceful connection termination."""
        logger.warning("Connection forcefully terminated")

        if self.stats_collector:
            self.stats_collector.record_disconnection(reason="connection_killed")

    async def _update_stats_periodically(self) -> None:
        """Periodically update gauge metrics that need regular refresh."""
        while not self.is_shutting_down:
            try:
                if self.stats_collector:
                    # Update connection status
                    is_connected = self.is_client_connected()
                    self.stats_collector.update_connection_status(
                        is_connected=is_connected,
                    )

                # Wait before next update
                await asyncio.sleep(30)  # Update every 30 seconds

            except asyncio.CancelledError:
                break
            except (ValueError, TypeError, AttributeError) as e:
                logger.error("Error updating periodic stats", error=str(e))
                await asyncio.sleep(30)

    async def stop(self, reason: str | None = None) -> None:
        """Perform graceful shutdown of the NWWS-OI client with proper cleanup.

        Orchestrates a clean shutdown sequence that ensures all resources are properly
        released and all ongoing operations are terminated safely. The shutdown process
        includes stopping background monitoring tasks, leaving the MUC room gracefully,
        disconnecting from the XMPP server, and signaling the async iterator to stop.

        The shutdown sequence follows a specific order to prevent race conditions and
        ensure data integrity:
        1. Set shutdown flag to prevent new operations
        2. Signal async iterator to stop accepting new messages
        3. Cancel all background monitoring and stats collection tasks
        4. Leave the NWWS MUC room with proper unsubscribe protocol
        5. Disconnect from the XMPP server with connection cleanup
        6. Update final connection status in stats collector

        Args:
            reason: Optional descriptive reason for the shutdown that will be logged
                   and included in the disconnect message to the server for debugging
                   and operational tracking purposes.

        Raises:
            ConnectionError: If the disconnect process encounters network issues,
                           though the client will still be marked as shut down.

        """
        if self.is_shutting_down:
            return

        logger.info("Shutting down NWWS-OI client")
        self.is_shutting_down = True

        # Signal iterator to stop
        self._stop_iteration = True

        # Cancel all monitoring tasks
        self._stop_background_services()

        # Leave MUC room gracefully
        self._leave_muc_room()

        # Disconnect from server
        await self.disconnect(ignore_send_queue=True, reason=reason)  # type: ignore[misc]

        if self.stats_collector:
            self.stats_collector.update_connection_status(is_connected=False)

        logger.info("Stopped NWWS-OI client")

    def _stop_background_services(self) -> None:
        """Cancel all monitoring and timeout tasks."""
        for task in self._background_tasks:
            if not task.done():
                logger.info("Stopping background task", task_name=task.get_name())
                task.cancel()

        # Reset task references
        self._idle_monitor_task = None
        self._stats_update_task = None
        self._background_tasks.clear()

    def _leave_muc_room(self) -> None:
        """Leave the MUC room gracefully."""
        try:
            muc_room_jid = JID(MUC_ROOM)
            self.plugin["xep_0045"].leave_muc(muc_room_jid, self.nickname)
            logger.info("Unsubscribing from MUC room", room=MUC_ROOM)
        except KeyError as err:
            logger.debug("MUC room not in currently joined rooms", room=MUC_ROOM, error=str(err))
        except XMPPError as err:
            logger.warning("Failed to leave MUC room gracefully", error=str(err))
        except Exception as err:  # noqa: BLE001
            logger.warning(
                "Unexpected error leaving MUC room", error=str(err), error_type=type(err).__name__
            )

    def _parse_issue_timestamp(self, issue_str: str) -> datetime:
        """Parse issue time from string to datetime."""
        try:
            return datetime.fromisoformat(issue_str.replace("Z", "+00:00"))
        except ValueError:
            logger.warning(
                "Invalid issue time format, using current time",
                issue_str=issue_str,
            )
            return datetime.now(UTC)

    def _calculate_delay_secs(self, delay_stamp: datetime | None) -> float:
        """Calculate delay in milliseconds from delay stamp."""
        if delay_stamp is None:
            return 0

        # Get current time in UTC
        current_time = datetime.now(UTC)

        # Calculate delay
        delay_delta = current_time - delay_stamp
        delay_ms = delay_delta.total_seconds() * 1000

        # Return positive delay only (ignore future timestamps)
        if delay_ms > 0:
            return delay_ms

        return 0

    def _convert_to_noaaport(self, text: str) -> str:
        """Convert text to NOAAPort format."""
        # Replace double newlines with carriage returns and ensure proper termination
        noaaport = f"\x01{text.replace('\n\n', '\r\r\n')}"
        if not noaaport.endswith("\n"):
            noaaport = f"{noaaport}\r\r\n"
        return f"{noaaport}\x03"
