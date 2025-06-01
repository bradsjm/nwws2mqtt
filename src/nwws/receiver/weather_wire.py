# pyright: strict
"""NWWS-OI XMPP client implementation using slixmpp with event-driven architecture."""

import asyncio
import time
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import slixmpp
from loguru import logger
from slixmpp import JID
from slixmpp.stanza import Message

from .config import WeatherWireConfig
from .stats import WeatherWireStatsCollector

# Configuration constants
MUC_ROOM = "nwws@conference.nwws-oi.weather.gov"
IDLE_TIMEOUT = 5 * 60  # 5 minutes
MAX_HISTORY = 5  # Maximum history messages to retrieve when joining MUC
MUC_JOIN_TIMEOUT = 30  # 30 seconds timeout for MUC join operation
SUBSCRIPTION_VERIFY_TIMEOUT = 60  # 60 seconds to verify subscription is working
PRESENCE_SEND_TIMEOUT = 10  # 10 seconds timeout for presence operations


@dataclass
class WeatherWireMessage:
    """Event representing a received weathermessage."""

    subject: str
    """Subject of the message, typically the product type or title."""
    noaaport: str
    """NOAAPort formatted text of the product message."""
    id: str
    """Unique identifier for the product (server process ID and sequence number)."""
    issue: datetime
    """Issue time of the product as a datetime object."""
    ttaaii: str
    """TTAAII code representing the WMO product type and time."""
    cccc: str
    """CCCC code representing the issuing office or center."""
    awipsid: str
    """The six character AWIPS ID, sometimes called AFOS PIL; if available otherwise 'NONE'."""
    delay_stamp: datetime | None
    """Delay stamp if the message was delayed, otherwise None."""


class WeatherWire(slixmpp.ClientXMPP):
    """NWWS-OI XMPP client using slixmpp with event-driven architecture."""

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
        - Comprehensive event handling for reliability monitoring
        - Timeout-based recovery mechanisms

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
        self.is_shutting_down: bool = False
        self.last_message_time: float = time.time()
        self._connection_start_time: float | None = None
        self._idle_monitor_task: asyncio.Task[object] | None = None
        self._muc_join_start_time: float | None = None
        self._muc_join_timeout_task: asyncio.Task[None] | None = None
        self._muc_joined: bool = False
        self._subscription_verified: bool = False
        self._subscription_verify_task: asyncio.Task[None] | None = None
        self._stats_update_task: asyncio.Task[None] | None = None
        self._background_tasks: set[asyncio.Task[Any]] = set()

        logger.info(
            "Initializing NWWS-OI XMPP client",
            username=config.username,
            server=config.server,
        )

    def _add_event_handlers(self) -> None:
        """Add comprehensive event handlers for all relevant XMPP events."""
        # Connection lifecycle events
        self.add_event_handler("connected", self._on_connected)
        self.add_event_handler("connecting", self._on_connecting)
        self.add_event_handler("connection_failed", self._on_connection_failed)
        self.add_event_handler("disconnected", self._on_disconnected)
        self.add_event_handler("eof_received", self._on_eof_received)
        self.add_event_handler("killed", self._on_killed)
        self.add_event_handler("reconnect_delay", self._on_reconnect_delay)

        # Session events
        self.add_event_handler("failed_auth", self._on_failed_auth)
        self.add_event_handler("session_end", self._on_session_end)
        self.add_event_handler("session_start", self._on_session_start)

        # TLS/SSL events
        self.add_event_handler("ssl_cert", self._on_ssl_cert)
        self.add_event_handler("ssl_invalid_chain", self._on_ssl_invalid_chain)
        self.add_event_handler("tls_success", self._on_tls_success)

        # Message and stanza events
        self.add_event_handler("groupchat_message", self._on_groupchat_message)
        self.add_event_handler("stanza_not_sent", self._on_stanza_not_sent)

        # MUC events
        self.add_event_handler("muc::*::got_offline", self._on_muc_got_offline)
        self.add_event_handler("muc::*::got_online", self._on_muc_got_online)
        self.add_event_handler("muc::*::presence", self._on_muc_presence)

    def start(self) -> asyncio.Future[bool]:
        """Connect to the XMPP server."""
        logger.info(
            "Connecting to NWWS-OI server",
            host=self.config.server,
            port=self.config.port,
        )
        self._connection_start_time = time.time()

        if self.stats_collector:
            self.stats_collector.record_connection_attempt()

        return super().connect(host=self.config.server, port=self.config.port)  # type: ignore  # noqa: PGH003

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

    # Event handlers for connection lifecycle
    async def _on_connecting(self, _event: object) -> None:
        """Handle connection initiation."""
        logger.debug("Connection attempt initiated")
        if self.stats_collector:
            self.stats_collector.record_connection_attempt()

    async def _on_connected(self, _event: object) -> None:
        """Handle successful TCP connection."""
        logger.info("Connected to NWWS-OI server")

        if self.stats_collector:
            self.stats_collector.update_connection_status(is_connected=True)

            if self._connection_start_time:
                duration_ms = (time.time() - self._connection_start_time) * 1000
                self.stats_collector.record_connection_success(duration_ms)

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

    async def _on_eof_received(self, _event: object) -> None:
        """Handle end-of-file received from server."""
        logger.warning("Server closed connection (EOF received)")
        if self.stats_collector:
            # Record EOF event for monitoring
            event = self.stats_collector.receiver_id
            labels = {"receiver": event}
            self.stats_collector.collector.increment_counter(
                "eof_received_total",
                labels=labels,
                help_text="Total number of EOF events received",
            )

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

    # TLS/SSL event handlers
    async def _on_tls_success(self, _event: object) -> None:
        """Handle successful TLS handshake."""
        logger.info("TLS handshake successful")
        if self.stats_collector:
            event = self.stats_collector.receiver_id
            labels = {"receiver": event}
            self.stats_collector.collector.increment_counter(
                "tls_success_total",
                labels=labels,
                help_text="Total number of successful TLS handshakes",
            )

    async def _on_ssl_cert(self, _cert: str) -> None:
        """Handle SSL certificate received."""
        logger.debug("SSL certificate received")
        if self.stats_collector:
            event = self.stats_collector.receiver_id
            labels = {"receiver": event}
            self.stats_collector.collector.increment_counter(
                "ssl_certificates_received_total",
                labels=labels,
                help_text="Total number of SSL certificates received",
            )

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

    # Session event handlers
    async def _on_session_start(self, _event: object) -> None:
        """Handle successful connection and authentication."""
        logger.info("Successfully authenticated with NWWS-OI server")

        # Reset state flags
        self._muc_joined = False
        self._subscription_verified = False

        # Start monitoring tasks
        await self._start_monitoring_tasks()

        # Send initial presence (non-blocking)
        self.send_presence()

        # Schedule roster retrieval (event-driven, don't await)
        self._create_background_task(self._retrieve_roster())

        # Schedule MUC join (event-driven, don't await)
        self._create_background_task(self._join_muc_room_with_timeout())

    async def _retrieve_roster(self) -> None:
        """Retrieve roster in event-driven manner."""
        try:
            await self.get_roster()  # type: ignore[misc]
            logger.debug("Roster retrieved successfully")
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to retrieve roster", error=str(e))
            # Continue operation even if roster fails

    async def _start_monitoring_tasks(self) -> None:
        """Start idle monitor and stats update tasks."""
        # Start idle monitor after session start
        if self._idle_monitor_task is None or self._idle_monitor_task.done():
            self._idle_monitor_task = asyncio.create_task(self._monitor_idle_timeout())
            logger.info("Idle timeout monitoring enabled", timeout=IDLE_TIMEOUT)

        # Start periodic stats updates if stats collector is available
        if self.stats_collector and (
            self._stats_update_task is None or self._stats_update_task.done()
        ):
            self._stats_update_task = asyncio.create_task(
                self._update_stats_periodically(),
            )
            logger.info("Periodic stats updates enabled")

    async def _on_session_end(self, _event: object) -> None:
        """Handle session end."""
        logger.warning("Session ended")

        # Reset state
        self._muc_joined = False
        self._subscription_verified = False

        # Cancel all monitoring tasks
        self._cancel_monitoring_tasks()

    def _cancel_monitoring_tasks(self) -> None:
        """Cancel all monitoring and timeout tasks."""
        tasks_to_cancel = [
            self._idle_monitor_task,
            self._stats_update_task,
            self._subscription_verify_task,
            self._muc_join_timeout_task,
        ]

        for task in tasks_to_cancel:
            if task is not None and not task.done():
                task.cancel()

        # Cancel all background tasks
        for task in self._background_tasks.copy():
            if not task.done():
                task.cancel()
        self._background_tasks.clear()

        # Reset task references
        self._idle_monitor_task = None
        self._stats_update_task = None
        self._subscription_verify_task = None
        self._muc_join_timeout_task = None

    async def _on_failed_auth(self, _event: object) -> None:
        """Handle authentication failure."""
        logger.error("Authentication failed for NWWS-OI client")

        if self.stats_collector:
            self.stats_collector.record_authentication_failure()

    async def _on_disconnected(self, reason: str | Exception) -> None:
        """Handle disconnection."""
        logger.warning("Disconnected from NWWS-OI server", reason=reason)

        # Reset state
        self._muc_joined = False
        self._subscription_verified = False

        if self.stats_collector:
            self.stats_collector.update_connection_status(is_connected=False)
            self.stats_collector.record_disconnection(str(reason))

    async def _on_connection_failed(self, reason: str | Exception) -> None:
        """Handle connection failure."""
        logger.error("Connection to NWWS-OI server failed", reason=str(reason))

        if self.stats_collector:
            self.stats_collector.record_connection_failure(str(reason))

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

    # MUC event handlers
    async def _on_muc_got_online(self, presence: object) -> None:
        """Handle MUC participant coming online."""
        logger.debug("MUC participant online", presence=presence)

    async def _on_muc_got_offline(self, presence: object) -> None:
        """Handle MUC participant going offline."""
        logger.debug("MUC participant offline", presence=presence)

    async def _on_muc_presence(self, _presence: object) -> None:
        """Handle MUC presence updates."""
        # Check if this is our own presence confirming MUC join
        if not self._muc_joined:
            self._muc_joined = True
            logger.info("Successfully joined MUC room", room=MUC_ROOM)

            # Cancel join timeout
            if self._muc_join_timeout_task and not self._muc_join_timeout_task.done():
                self._muc_join_timeout_task.cancel()

            # Record successful MUC join
            if self.stats_collector and self._muc_join_start_time:
                duration_ms = (time.time() - self._muc_join_start_time) * 1000
                event = self.stats_collector.receiver_id
                labels = {"receiver": event}
                self.stats_collector.collector.record_operation(
                    "muc_join",
                    success=True,
                    duration_ms=duration_ms,
                    labels=labels,
                )

            # Send subscription presence after successful join
            self._create_background_task(self._send_subscription_presence_with_timeout())

            # Start subscription verification
            self._start_subscription_verification()

    # MUC operations with timeouts and retries
    async def _join_muc_room_with_timeout(self, max_history: int = MAX_HISTORY) -> None:
        """Join MUC room with timeout and retry logic."""
        self._muc_join_start_time = time.time()

        try:
            # Start timeout task
            self._muc_join_timeout_task = asyncio.create_task(
                self._muc_join_timeout_handler()
            )

            logger.info("Joining MUC room", room=MUC_ROOM)

            # Join MUC room
            muc_room_jid = JID(MUC_ROOM)
            await self.plugin["xep_0045"].join_muc(  # type: ignore[misc]
                muc_room_jid,
                self.nickname,
                maxhistory=str(max_history),
            )

        except Exception as e:  # noqa: BLE001
            logger.error("Failed to join MUC room", error=str(e))
            if self.stats_collector:
                event = self.stats_collector.receiver_id
                labels = {"receiver": event, "error": str(e)}
                self.stats_collector.collector.record_operation(
                    "muc_join",
                    success=False,
                    labels=labels,
                )

            # Schedule retry
            await asyncio.sleep(5)
            if not self.is_shutting_down:
                self._create_background_task(self._join_muc_room_with_timeout())

    async def _muc_join_timeout_handler(self) -> None:
        """Handle MUC join timeout."""
        await asyncio.sleep(MUC_JOIN_TIMEOUT)

        if not self._muc_joined and not self.is_shutting_down:
            logger.warning("MUC join timed out, retrying", timeout=MUC_JOIN_TIMEOUT)

            if self.stats_collector:
                event = self.stats_collector.receiver_id
                labels = {"receiver": event, "reason": "timeout"}
                self.stats_collector.collector.increment_counter(
                    "muc_join_timeouts_total",
                    labels=labels,
                    help_text="Total number of MUC join timeouts",
                )

            # Retry MUC join
            self._create_background_task(self._join_muc_room_with_timeout())

    async def _send_subscription_presence_with_timeout(self) -> None:
        """Send subscription presence with timeout."""
        try:
            # Send presence to confirm subscription
            self.send_presence(pto=f"{MUC_ROOM}/{self.nickname}")
            logger.debug("Sent subscription confirmation presence")

            if self.stats_collector:
                event = self.stats_collector.receiver_id
                labels = {"receiver": event}
                self.stats_collector.collector.increment_counter(
                    "presence_sent_total",
                    labels=labels,
                    help_text="Total number of presence stanzas sent",
                )

        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to send subscription presence", error=str(e))
            if self.stats_collector:
                event = self.stats_collector.receiver_id
                labels = {"receiver": event, "error": str(e)}
                self.stats_collector.collector.record_error(
                    "presence_send_failure",
                    operation="presence_send",
                    labels=labels,
                )

    def _start_subscription_verification(self) -> None:
        """Start task to verify subscription is working by checking for messages."""
        if (
            self._subscription_verify_task is None
            or self._subscription_verify_task.done()
        ):
            self._subscription_verify_task = asyncio.create_task(
                self._verify_subscription()
            )

    async def _verify_subscription(self) -> None:
        """Verify that subscription is working by waiting for first message."""
        initial_message_time = self.last_message_time
        await asyncio.sleep(SUBSCRIPTION_VERIFY_TIMEOUT)

        # Check if we received any messages since starting verification
        if (
            not self._subscription_verified
            and self.last_message_time == initial_message_time
            and not self.is_shutting_down
        ):
            logger.warning(
                "No messages received after MUC join, subscription may have failed",
                timeout=SUBSCRIPTION_VERIFY_TIMEOUT,
            )

            if self.stats_collector:
                event = self.stats_collector.receiver_id
                labels = {"receiver": event}
                self.stats_collector.collector.increment_counter(
                    "subscription_verification_failures_total",
                    labels=labels,
                    help_text="Total number of subscription verification failures",
                )

            # Force reconnection to retry subscription
            self.reconnect(reason="Subscription verification failed")

    # Message handling
    async def _on_groupchat_message(self, msg: Message) -> None:
        """Process incoming groupchat message."""
        message_start_time = time.time()
        self.last_message_time = message_start_time

        # Mark subscription as verified on first message
        if not self._subscription_verified:
            self._subscription_verified = True
            logger.info("Subscription verified - first message received")

            if self.stats_collector:
                event = self.stats_collector.receiver_id
                labels = {"receiver": event}
                self.stats_collector.collector.increment_counter(
                    "subscription_verifications_success_total",
                    labels=labels,
                    help_text="Total number of successful subscription verifications",
                )

        if self.stats_collector:
            # Update the age of last message (should be near 0 for new messages)
            self.stats_collector.update_last_message_age(0.0)

        if self.is_shutting_down:
            logger.info("Client is shutting down, ignoring message")
            return

        # Check if the message is from the expected MUC room
        if msg.get_mucroom() != JID(MUC_ROOM).bare:
            logger.debug(
                f"Message not from {MUC_ROOM} room, skipping",
                from_jid=msg["from"].bare,
            )
            if self.stats_collector:
                self.stats_collector.record_message_error("wrong_room")
            return

        try:
            await self._nwws_message(msg)

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

    async def _nwws_message(self, msg: Message) -> None:
        """Process group chat message containing weather data."""
        # Get the message subject from the body or subject field
        subject = str(msg.get("body", "")) or str(msg.get("subject", ""))

        # Get delay stamp if available
        delay_stamp: datetime | None = msg["delay"]["stamp"] if "delay" in msg else None

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
        xid = x.get("id", "")
        issue_str = x.get("issue", "")
        ttaaii = x.get("ttaaii", "")
        cccc = x.get("cccc", "")
        awipsid = x.get("awipsid", "NONE")

        # Parse issue time from ISO 8601 format to datetime
        try:
            issue = datetime.fromisoformat(issue_str.replace("Z", "+00:00"))
        except ValueError:
            logger.warning(
                "Invalid issue time format, using current time",
                issue_str=issue_str,
                msg_id=msg.get_id(),
            )
            issue = datetime.now(UTC)

        # Convert the body to NOAAPort format
        # Replace double newlines with carriage returns and ensure proper termination
        # and add start and end markers
        unix_text: str = body
        noaaport: str = f"\x01{unix_text.replace('\n\n', '\r\r\n')}"
        if not noaaport.endswith("\n"):
            noaaport = f"{noaaport}\r\r\n"
        noaaport = f"{noaaport}\x03"

        # Calculate and record delay if present
        if delay_stamp and self.stats_collector:
            delay_ms = self._calculate_delay_ms(delay_stamp)
            if delay_ms is not None:
                self.stats_collector.record_delayed_message(delay_ms)

        logger.info(
            "received",
            subject=subject,
            id=xid,
            issue=issue.isoformat(),
            ttaaii=ttaaii,
            cccc=cccc,
            awipsid=awipsid,
            delay_stamp=delay_stamp,
        )

        # Call the callback with the event
        event = WeatherWireMessage(
            subject=subject,
            noaaport=noaaport,
            id=xid,
            issue=issue,
            ttaaii=ttaaii,
            cccc=cccc,
            awipsid=awipsid,
            delay_stamp=delay_stamp,
        )
        await self.callback(event)

    # Shutdown and cleanup
    async def stop(self, reason: str | None = None) -> None:
        """Gracefully shutdown the XMPP client."""
        if self.is_shutting_down:
            return

        logger.info("Shutting down NWWS-OI client")
        self.is_shutting_down = True

        # Cancel all monitoring tasks
        self._cancel_monitoring_tasks()

        # Leave MUC room gracefully
        self._leave_muc_room()

        # Disconnect from server
        await self.disconnect(ignore_send_queue=True, reason=reason)  # type: ignore[misc]

        if self.stats_collector:
            self.stats_collector.update_connection_status(is_connected=False)

        logger.info("Stopped NWWS-OI client")

    def _leave_muc_room(self) -> None:
        """Leave the MUC room gracefully."""
        if self._muc_joined:
            try:
                muc_room_jid = JID(MUC_ROOM)
                self.plugin["xep_0045"].leave_muc(muc_room_jid, self.nickname)
                logger.info("Unsubscribing from MUC room", room=MUC_ROOM)
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to leave MUC room gracefully", error=str(e))

    def _calculate_delay_ms(self, delay_stamp: datetime) -> float | None:
        """Calculate delay in milliseconds from delay stamp.

        Args:
            delay_stamp: Delay timestamp as a datetime object.

        Returns:
            Delay in milliseconds or None if parsing fails.

        """
        try:
            # Get current time in UTC
            current_time = datetime.now(UTC)

            # Calculate delay
            delay_delta = current_time - delay_stamp

            # Convert to milliseconds
            delay_ms = delay_delta.total_seconds() * 1000

            # Return positive delay only (ignore future timestamps)
            if delay_ms > 0:
                return delay_ms

        except (ValueError, TypeError, OverflowError) as e:
            logger.warning(
                "Failed to parse delay timestamp",
                delay_stamp=delay_stamp,
                error=str(e),
            )

        return None

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

                    # Update MUC status
                    event = self.stats_collector.receiver_id
                    labels = {"receiver": event}
                    muc_status = 1.0 if self._muc_joined else 0.0
                    self.stats_collector.collector.set_gauge(
                        "muc_joined_status",
                        muc_status,
                        labels=labels,
                        help_text="Whether the client is currently joined to MUC room",
                    )

                    # Update subscription status
                    subscription_status = 1.0 if self._subscription_verified else 0.0
                    self.stats_collector.collector.set_gauge(
                        "subscription_verified_status",
                        subscription_status,
                        labels=labels,
                        help_text="Whether the subscription is verified and receiving messages",
                    )

                # Wait before next update
                await asyncio.sleep(30)  # Update every 30 seconds

            except asyncio.CancelledError:
                break
            except (ValueError, TypeError, AttributeError) as e:
                logger.error("Error updating periodic stats", error=str(e))
                await asyncio.sleep(30)

    def _create_background_task(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        """Create a background task with proper reference tracking and exception handling."""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)

        # Add done callback to remove from set and handle exceptions
        task.add_done_callback(self._background_task_done)
        return task

    def _background_task_done(self, task: asyncio.Task[Any]) -> None:
        """Handle completion of background tasks."""
        # Remove from tracking set
        self._background_tasks.discard(task)

        # Log any exceptions that occurred
        try:
            exception = task.exception()
            if exception is not None:
                logger.error(
                    "Background task failed with exception",
                    task_name=task.get_name(),
                    error=str(exception),
                    exc_info=exception,
                )

                # Record task failure in stats if available
                if self.stats_collector:
                    event = self.stats_collector.receiver_id
                    labels = {"receiver": event, "task_name": task.get_name()}
                    self.stats_collector.collector.record_error(
                        "background_task_failure",
                        operation="background_task",
                        labels=labels,
                    )
        except asyncio.CancelledError:
            # Task was cancelled, this is expected during shutdown
            pass
        except (ValueError, TypeError, AttributeError) as e:
            logger.error("Error handling background task completion", error=str(e))

    def is_client_connected(self) -> bool:
        """Check if the XMPP client is connected."""
        return self.is_connected() and not self.is_shutting_down
