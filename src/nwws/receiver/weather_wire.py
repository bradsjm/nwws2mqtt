# pyright: strict
"""NWWS-OI XMPP client implementation using slixmpp."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import slixmpp
from loguru import logger
from slixmpp import JID
from slixmpp.stanza import Message

from nwws.models import XMPPConfig

# Configuration constants
MUC_ROOM = "nwws@conference.nwws-oi.weather.gov"
IDLE_TIMEOUT = 5 * 60  # 5 minutes


@dataclass
class WeatherWireMessage:
    """Event representing a received weathermessage."""

    subject: str
    """Subject of the message, typically the product type or title."""
    noaaport: str
    """NOAAPort formatted text of the product message."""
    id: str
    """Unique identifier for the product (server process ID and sequence number)."""
    issue: str
    """Issue time of the product in ISO 8601 format."""
    ttaaii: str
    """TTAAII code representing the WMO product type and time."""
    cccc: str
    """CCCC code representing the issuing office or center."""
    awipsid: str
    """The six character AWIPS ID, sometimes called AFOS PIL; if available otherwise 'NONE'."""
    delay_stamp: str | None
    """Delay stamp if the message was delayed, otherwise None."""


class WeatherWire(slixmpp.ClientXMPP):
    """NWWS-OI XMPP client using slixmpp."""

    def __init__(self, config: XMPPConfig, callback: Callable[[WeatherWireMessage], Awaitable[None]]) -> None:
        """Initialize the XMPP client with configuration and callback.

        Args:
        config: XMPP configuration containing username, password, server details
        callback: Async function to call when a WeatherWireEvent is received

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

        # Register plugins
        self.register_plugin("xep_0030")  # Service Discovery  # type: ignore[misc]
        self.register_plugin("xep_0045")  # Multi-User Chat  # type: ignore[misc]
        self.register_plugin("xep_0199")  # XMPP Ping  # type: ignore[misc]
        self.register_plugin("xep_0203")  # Delayed Delivery # type: ignore[misc]

        # Add event handlers
        self.add_event_handler("session_start", self._on_session_start)
        self.add_event_handler("session_end", self._on_session_end)
        self.add_event_handler("groupchat_message", self._on_groupchat_message)
        self.add_event_handler("failed_auth", self._on_failed_auth)
        self.add_event_handler("connected", self._on_connected)
        self.add_event_handler("disconnected", self._on_disconnected)
        self.add_event_handler("connection_failed", self._on_connection_failed)

        # Initialize state variables
        self.last_message_time: float = time.time()
        self.is_shutting_down: bool = False
        self._idle_monitor_task: asyncio.Task[object] | None = None

        logger.info(
            "Initializing NWWS-OI XMPP client",
            username=config.username,
            server=config.server,
        )

    def start(self) -> asyncio.Future[bool]:
        """Connect to the XMPP server."""
        logger.info("Connecting to NWWS-OI server", host=self.config.server, port=self.config.port)
        return super().connect(host=self.config.server, port=self.config.port)  # type: ignore  # noqa: PGH003

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
                await self._force_reconnect()
                break

    async def _force_reconnect(self) -> None:
        """Force a reconnect of the XMPP client."""
        await self.stop()
        await asyncio.sleep(2)
        self.is_shutting_down = False
        self.last_message_time = time.time()
        self.start()

    async def _on_connected(self, _event: object) -> None:
        """Handle successful connection."""
        logger.info("Connected to NWWS-OI server")

    async def _on_session_start(self, _event: object) -> None:
        """Handle successful connection and authentication."""
        logger.info("Successfully authenticated with NWWS-OI server")

        # Start idle monitor after session start
        if self._idle_monitor_task is None or self._idle_monitor_task.done():
            self._idle_monitor_task = asyncio.create_task(self._monitor_idle_timeout())
            logger.info("Idle timeout monitoring enabled", timeout=IDLE_TIMEOUT)

        # Send initial presence
        self.send_presence()
        await self.get_roster()  # type: ignore[misc]

        # Join MUC room
        await self._join_muc_room()

    async def _on_session_end(self, _event: object) -> None:
        """Handle session end."""
        logger.warning("Session ended")
        # Stop idle monitor on session end
        if self._idle_monitor_task is not None:
            self._idle_monitor_task.cancel()
            self._idle_monitor_task = None

    async def _on_failed_auth(self, _event: object) -> None:
        """Handle authentication failure."""
        logger.error("Authentication failed for NWWS-OI client")

    async def _on_disconnected(self, reason: str | Exception) -> None:
        """Handle disconnection."""
        logger.warning("Disconnected from NWWS-OI server", reason=reason)

    async def _on_connection_failed(self, reason: str | Exception) -> None:
        """Handle connection failure."""
        logger.error("Connection to NWWS-OI server failed" + str(reason), reason=reason)

    async def _join_muc_room(self) -> None:
        """Join and subscribe to the MUC room with proper configuration."""
        logger.info("Subscribing to room", room=MUC_ROOM)

        # Join MUC room
        muc_room_jid = JID(MUC_ROOM)
        await self.plugin["xep_0045"].join_muc(  # type: ignore[misc]
            muc_room_jid,
            self.nickname,
            maxhistory="5",
        )

        # Send additional presence to ensure proper subscription
        await asyncio.sleep(2)
        await self._send_subscription_presence(self.nickname)

    async def _send_subscription_presence(self, nickname: str) -> None:
        """Send additional presence to ensure proper subscription."""
        # Send presence to confirm subscription
        self.send_presence(pto=f"{MUC_ROOM}/{nickname}")
        logger.debug("Sent subscription confirmation presence")

    async def _on_groupchat_message(self, msg: Message) -> None:
        """Process incoming groupchat message."""
        self.last_message_time = time.time()
        if self.is_shutting_down:
            logger.info("Client is shutting down, ignoring message")
            return

        # Check if the message is from the expected MUC room
        if msg.get_from().bare != JID(MUC_ROOM).bare:
            logger.debug(f"Message not from {MUC_ROOM} room, skipping", from_jid=msg["from"].bare)
            return

        await self._nwws_message(msg)

    async def _nwws_message(self, msg: Message) -> None:
        """Process group chat message containing weather data."""
        # Get the message subject from the body or subject field
        subject = str(msg.get("body", "")) or str(msg.get("subject", ""))
        # Get delay stamp if available
        delay_stamp: str | None = msg["delay"]["stamp"] if "delay" in msg else None

        # Check for NWWS-OI namespace in the message
        x = msg.xml.find("{nwws-oi}x")
        if x is None:
            logger.warning("No NWWS-OI namespace in group message, skipping", msg_id=msg.get_id())
            return

        # Get the message body which should contain the weather data
        body = (x.text or "").strip()
        if not body:
            logger.warning("No body text in NWWS-OI namespace, skipping", msg_id=msg.get_id())
            return

        # Get the metadata from the NWWS-OI namespace
        xid = x.get("id", "")
        issue = x.get("issue", "")
        ttaaii = x.get("ttaaii", "")
        cccc = x.get("cccc", "")
        awipsid = x.get("awipsid", "NONE")

        # Convert the body to NOAAPort format
        # Replace double newlines with carriage returns and ensure proper termination
        # and add start and end markers
        unix_text: str = body
        noaaport: str = f"\x01{unix_text.replace('\n\n', '\r\r\n')}"
        if not noaaport.endswith("\n"):
            noaaport = f"{noaaport}\r\r\n"
        noaaport = f"{noaaport}\x03"

        logger.info(
            "received",
            subject=subject,
            id=xid,
            issue=issue,
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

    async def stop(self) -> None:
        """Gracefully shutdown the XMPP client."""
        if self.is_shutting_down:
            return

        logger.info("Shutting down NWWS-OI client")
        self.is_shutting_down = True

        # Cancel idle monitor task if running
        if self._idle_monitor_task is not None:
            self._idle_monitor_task.cancel()
            self._idle_monitor_task = None

        # Leave MUC room gracefully
        self._leave_muc_room()

        # Disconnect from server
        await self.disconnect()  # type: ignore[misc]
        logger.info("Stopped NWWS-OI client")

    def _leave_muc_room(self) -> None:
        """Leave the MUC room gracefully."""
        muc_room_jid = JID(MUC_ROOM)
        self.plugin["xep_0045"].leave_muc(muc_room_jid, self.nickname)
        logger.info("Unsubscribing from MUC room", room=MUC_ROOM)

    def is_client_connected(self) -> bool:
        """Check if the XMPP client is connected."""
        return self.is_connected() and not self.is_shutting_down
