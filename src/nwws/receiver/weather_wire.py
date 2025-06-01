# pyright: strict
"""NWWS-OI XMPP client implementation using slixmpp."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import slixmpp
from loguru import logger
from pydantic import BaseModel, Field
from slixmpp import JID
from slixmpp.exceptions import XMPPError
from slixmpp.stanza import Message

from nwws.receiver.stats import WeatherWireStatsCollector

from .config import WeatherWireConfig

# Configuration constants
MUC_ROOM = "nwws@conference.nwws-oi.weather.gov"
IDLE_TIMEOUT = 90  # 90 seconds of inactivity before reconnecting
MAX_HISTORY = 5  # Maximum history messages to retrieve when joining MUC


class WeatherWireMessage(BaseModel):
    """Represents content of a received weathermessage."""

    subject: str = Field(description="Subject of the message")
    noaaport: str = Field(description="NOAAPort formatted text of the product message.")
    id: str = Field(
        description="Unique identifier for the product (server process ID and sequence number)."
    )
    issue: datetime = Field(
        description="Issue time of the product as a datetime object."
    )
    ttaaii: str = Field(
        description="TTAAII code representing the WMO product type and time."
    )
    cccc: str = Field(
        description="CCCC code representing the issuing office or center."
    )
    awipsid: str = Field(
        description="AWIPS ID (AFOS PIL) of the product if available.", default="NONE"
    )
    delay_stamp: datetime | None = Field(
        description="Delay stamp if the message was delayed, otherwise None.",
    )


class WeatherWire(slixmpp.ClientXMPP):
    """NWWS-OI XMPP client using slixmpp."""

    def __init__(
        self,
        config: WeatherWireConfig,
        callback: Callable[[WeatherWireMessage], Awaitable[None]],
        *,
        stats_collector: WeatherWireStatsCollector | None = None,
    ) -> None:
        """Initialize the XMPP client with configuration and callback.

        Args:
            config: XMPP configuration containing username, password, server details
            callback: Async function to call when a WeatherWireEvent is received
            stats_collector: Optional stats collector for monitoring receiver metrics

        The client is configured with:
        - Service Discovery (XEP-0030) for capability negotiation
        - Multi-User Chat (XEP-0045) for joining the NWWS room
        - XMPP Ping (XEP-0199) for connection keep-alive
        - Delayed Delivery (XEP-0203) for handling delayed messages
        - Idle timeout monitoring to detect connection issues

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
        self.callback = callback
        self.nickname = f"{datetime.now(UTC):%Y%m%d%H%M}"
        self.stats_collector = stats_collector

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
        self._connection_start_time: float | None = None

        logger.info(
            "Initializing NWWS-OI XMPP client",
            username=config.username,
            server=config.server,
        )

    def _add_event_handlers(self) -> None:
        """Add comprehensive event handlers for all relevant XMPP events."""
        # Connection lifecycle events
        self.add_event_handler("connecting", self._on_connecting)
        self.add_event_handler("connected", self._on_connected)
        self.add_event_handler("disconnected", self._on_disconnected)
        self.add_event_handler("connection_failed", self._on_connection_failed)
        self.add_event_handler("reconnect_delay", self._on_reconnect_delay)
        self.add_event_handler("killed", self._on_killed)

        # Session events
        self.add_event_handler("session_start", self._on_session_start)
        self.add_event_handler("session_end", self._on_session_end)
        self.add_event_handler("failed_auth", self._on_failed_auth)

        # TLS/SSL events
        self.add_event_handler("ssl_invalid_chain", self._on_ssl_invalid_chain)

        # Message and stanza events
        self.add_event_handler("groupchat_message", self._on_groupchat_message)
        self.add_event_handler("stanza_not_sent", self._on_stanza_not_sent)

        # MUC events
        self.add_event_handler("muc::*::presence", self._on_muc_presence)

    def start(self) -> asyncio.Future[bool]:
        """Connect to the XMPP server."""
        logger.info(
            "Connecting to NWWS-OI server",
            host=self.config.server,
            port=self.config.port,
        )

        if self.stats_collector:
            self.stats_collector.record_connection_attempt()

        return super().connect(host=self.config.server, port=self.config.port)  # type: ignore  # noqa: PGH003

    def is_client_connected(self) -> bool:
        """Check if the XMPP client is connected."""
        return self.is_connected() and not self.is_shutting_down

    # Event handlers for connection lifecycle
    async def _on_connecting(self, _event: object) -> None:
        """Handle connection initiation."""
        logger.info("Starting connection attempt to NWWS-OI server")
        self._connection_start_time = time.time()

        if self.stats_collector:
            self.stats_collector.record_connection_attempt()

    # TLS/SSL event handlers
    async def _on_ssl_invalid_chain(self, error: Exception) -> None:
        """Handle SSL certificate chain validation failure."""
        logger.error("SSL certificate chain validation failed", error=str(error))
        if self.stats_collector:
            event = self.stats_collector.receiver_id
            labels = {"receiver": event, "error": str(error)}
            self.stats_collector.collector.record_error(
                "ssl_invalid_chain",
                operation="tls_handshake",
                labels=labels,
            )

    async def _on_reconnect_delay(self, delay_time: float) -> None:
        """Handle reconnection delay notification."""
        logger.info("Reconnection delayed", delay_seconds=delay_time)
        if self.stats_collector:
            # Record reconnection delay for monitoring
            event = self.stats_collector.receiver_id
            labels = {"receiver": event}
            self.stats_collector.collector.observe_histogram(
                "reconnect_delay_seconds",
                delay_time,
                labels=labels,
                help_text="Duration of reconnection delays in seconds",
            )

    async def _on_failed_auth(self, _event: object) -> None:
        """Handle authentication failure."""
        logger.error("Authentication failed for NWWS-OI client")

        if self.stats_collector:
            self.stats_collector.record_authentication_failure()

    async def _on_connection_failed(self, reason: str | Exception) -> None:
        """Handle connection failure."""
        logger.error("Connection to NWWS-OI server failed" + str(reason), reason=reason)

        if self.stats_collector:
            self.stats_collector.record_connection_failure(str(reason))

    async def _on_connected(self, _event: object) -> None:
        """Handle successful connection."""
        logger.info("Connected to NWWS-OI server")

        if self.stats_collector:
            self.stats_collector.update_connection_status(is_connected=True)

            if self._connection_start_time:
                duration_ms = (time.time() - self._connection_start_time) * 1000
                self.stats_collector.record_connection_success(duration_ms)

    async def _monitor_idle_timeout(self) -> None:
        """Monitor for idle timeout and force reconnect if needed."""
        while not self.is_shutting_down:
            await asyncio.sleep(10)
            now = time.time()
            if now - self.last_message_time > IDLE_TIMEOUT:
                idle_duration = now - self.last_message_time
                logger.warning(
                    "No messages received in {timeout} seconds, reconnecting...",
                    timeout=IDLE_TIMEOUT,
                )

                if self.stats_collector:
                    self.stats_collector.record_idle_timeout(idle_duration)
                    self.stats_collector.record_reconnection()

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
                self.stats_collector.record_connection_failure(str(err))

    async def _start_background_services(self) -> None:
        """Start necessary services after session start."""
        if self._idle_monitor_task is None or self._idle_monitor_task.done():
            self._idle_monitor_task = asyncio.create_task(
                self._monitor_idle_timeout(),
                name="idle_timeout_monitor",
            )
            logger.info("Idle timeout monitoring enabled", timeout=IDLE_TIMEOUT)

        # Start periodic stats updates if stats collector is available
        if self.stats_collector and (
            self._stats_update_task is None or self._stats_update_task.done()
        ):
            self._stats_update_task = asyncio.create_task(
                self._update_stats_periodically(),
                name="periodic_stats_update",
            )
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
        except XMPPError as err:
            logger.error(
                "Failed to join NWWS room",
                room=MUC_ROOM,
                nickname=self.nickname,
                error=str(err),
            )
            if self.stats_collector:
                self.stats_collector.record_connection_failure(str(err))

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

        # Record successful MUC join
        if self.stats_collector:
            event = self.stats_collector.receiver_id
            labels = {"receiver": event}
            self.stats_collector.collector.record_operation(
                "muc_join",
                success=True,
                labels=labels,
            )

    # Stanza event handlers
    async def _on_stanza_not_sent(self, stanza: object) -> None:
        """Handle stanza send failure."""
        logger.warning("Stanza not sent", stanza_type=type(stanza).__name__)
        if self.stats_collector:
            event = self.stats_collector.receiver_id
            labels = {"receiver": event, "stanza_type": type(stanza).__name__}
            self.stats_collector.collector.increment_counter(
                "stanzas_not_sent_total",
                labels=labels,
                help_text="Total number of stanzas that failed to send",
            )

    async def _on_groupchat_message(self, msg: Message) -> None:
        """Process incoming groupchat message."""
        message_start_time = time.time()
        self.last_message_time = message_start_time

        if self.is_shutting_down:
            logger.info("Client is shutting down, ignoring message")
            return

        if self.stats_collector:
            # Update the age of last message (should be near 0 for new messages)
            self.stats_collector.update_last_message_age(0.0)

        # Check if the message is from the expected MUC room
        if msg.get_mucroom() != JID(MUC_ROOM).bare:
            logger.warning(
                f"Message not from {MUC_ROOM} room, skipping",
                from_jid=msg["from"].bare,
            )
            return

        try:
            await self._on_nwws_message(msg)

            if self.stats_collector:
                duration_ms = (time.time() - message_start_time) * 1000
                self.stats_collector.record_message_received(duration_ms)

        except ValueError as e:
            logger.error(
                "Error processing NWWS message",
                error=str(e),
                msg_id=msg.get_id(),
            )
            if self.stats_collector:
                self.stats_collector.record_message_error("processing_error")

    async def _on_nwws_message(self, msg: Message) -> None:
        """Process group chat message containing weather data."""
        # Check for NWWS-OI namespace in the message
        x = msg.xml.find("{nwws-oi}x")
        if x is None:
            logger.warning(
                "No NWWS-OI namespace in group message, skipping",
                msg_id=msg.get_id(),
            )
            if self.stats_collector:
                self.stats_collector.record_message_error("missing_namespace")
            return

        # Get the message subject from the body or subject field
        subject = str(msg.get("body", "")) or str(msg.get("subject", ""))

        # Get delay stamp if available
        delay_stamp: datetime | None = msg["delay"]["stamp"] if "delay" in msg else None
        delay_ms = self._calculate_delay_ms(delay_stamp) if delay_stamp else None

        # Calculate and record delay if present
        if self.stats_collector and delay_ms is not None:
            self.stats_collector.record_delayed_message(delay_ms)

        # Get the message body which should contain the weather data
        body = (x.text or "").strip()
        if not body:
            logger.warning(
                "No body text in NWWS-OI namespace, skipping",
                msg_id=msg.get_id(),
            )
            if self.stats_collector:
                self.stats_collector.record_message_error("empty_body")
            return

        # Get the metadata from the NWWS-OI namespace
        event = WeatherWireMessage(
            subject=subject,
            noaaport=self._convert_to_noaaport(body),
            id=x.get("id", ""),
            issue=self._parse_issue_timestamp(x.get("issue", "")),
            ttaaii=x.get("ttaaii", ""),
            cccc=x.get("cccc", ""),
            awipsid=x.get("awipsid", "") or "NONE",
            delay_stamp=delay_stamp,
        )

        logger.info(
            "Received Event",
            subject=event.subject,
            id=event.id,
            issue=event.issue,
            ttaaii=event.ttaaii,
            cccc=event.cccc,
            awipsid=event.awipsid,
            delay_ms=delay_ms,
        )
        await self.callback(event)

    async def _on_session_end(self, _event: object) -> None:
        """Handle session end."""
        logger.warning("Session ended")

        # Cancel all monitoring tasks
        self._stop_background_services()

    async def _on_disconnected(self, reason: str | Exception) -> None:
        """Handle disconnection."""
        logger.warning("Disconnected from NWWS-OI server", reason=reason)

        if self.stats_collector:
            self.stats_collector.update_connection_status(is_connected=False)
            self.stats_collector.record_disconnection(str(reason))

    async def _on_killed(self, _event: object) -> None:
        """Handle forceful connection termination."""
        logger.warning("Connection forcefully terminated")
        if self.stats_collector:
            # Record killed connection event
            event = self.stats_collector.receiver_id
            labels = {"receiver": event}
            self.stats_collector.collector.increment_counter(
                "connections_killed_total",
                labels=labels,
                help_text="Total number of forcefully terminated connections",
            )

    async def _update_stats_periodically(self) -> None:
        """Periodically update gauge metrics that need regular refresh."""
        while not self.is_shutting_down:
            try:
                if self.stats_collector:
                    # Update last message age
                    age_seconds = time.time() - self.last_message_time
                    self.stats_collector.update_last_message_age(age_seconds)

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
        """Gracefully shutdown the XMPP client."""
        if self.is_shutting_down:
            return

        logger.info("Shutting down NWWS-OI client")
        self.is_shutting_down = True

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
        tasks_to_cancel = [
            self._idle_monitor_task,
            self._stats_update_task,
        ]

        for task in tasks_to_cancel:
            if task is not None and not task.done():
                logger.info("Stopping background task", task_name=task.get_name())
                task.cancel()

        # Reset task references
        self._idle_monitor_task = None
        self._stats_update_task = None

    def _leave_muc_room(self) -> None:
        """Leave the MUC room gracefully."""
        try:
            muc_room_jid = JID(MUC_ROOM)
            self.plugin["xep_0045"].leave_muc(muc_room_jid, self.nickname)
            logger.info("Unsubscribing from MUC room", room=MUC_ROOM)
        except XMPPError as err:
            logger.warning("Failed to leave MUC room gracefully", error=str(err))

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

    def _calculate_delay_ms(self, delay_stamp: datetime) -> float | None:
        """Calculate delay in milliseconds from delay stamp."""
        # Get current time in UTC
        current_time = datetime.now(UTC)

        # Calculate delay
        delay_delta = current_time - delay_stamp
        delay_ms = delay_delta.total_seconds() * 1000

        # Return positive delay only (ignore future timestamps)
        if delay_ms > 0:
            return delay_ms

        return None

    def _convert_to_noaaport(self, text: str) -> str:
        """Convert text to NOAAPort format."""
        # Replace double newlines with carriage returns and ensure proper termination
        noaaport = f"\x01{text.replace('\n\n', '\r\r\n')}"
        if not noaaport.endswith("\n"):
            noaaport = f"{noaaport}\r\r\n"
        return f"{noaaport}\x03"
