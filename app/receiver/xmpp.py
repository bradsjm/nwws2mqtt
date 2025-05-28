# pyright: basic
"""NWWS-OI XMPP client implementation."""

import json
import time
from datetime import UTC, datetime

from loguru import logger
from messaging import MessageBus, ProductMessage, Topics
from pyiem.exceptions import TextProductException
from pyiem.nws.product import TextProduct
from twisted.internet import reactor
from twisted.internet.error import ConnectError
from twisted.internet.task import LoopingCall
from twisted.names.srvconnect import SRVConnector
from twisted.words.protocols.jabber import client, error, xmlstream
from twisted.words.protocols.jabber.jid import JID
from twisted.words.xish import domish
from twisted.words.xish.xmlstream import STREAM_END_EVENT, XmlStream, XmlStreamFactory

from app.messaging.message_bus import StatsMessageProcessingMessage
from app.models import XMPPConfig, convert_text_product_to_model

# Configuration constants
MUC_ROOM = "nwws@conference.nwws-oi.weather.gov"
MAX_UNRESPONDED_PINGS = 5
PING_INTERVAL = 60
RECONNECT_DELAY = 30
MAX_RECONNECT_ATTEMPTS = 10
GROUPCHAT_MESSAGE_TIMEOUT = 300  # 5 minutes


class NWWSXMPPClient:
    """NWWSXMPPClient provides an XMPP client for interfacing with the NWWS-OI (National Weather Wire Service - Open Interface).

    This client manages the connection lifecycle, authentication, and communication with the NWWS-OI XMPP server,
    including joining and subscribing to a Multi-User Chat (MUC) room to receive weather data products.
    It implements robust error handling, automatic reconnection with exponential backoff, and periodic housekeeping tasks
    such as pinging the server and monitoring message activity.

    Key Features:
    - Establishes and maintains an XMPP connection using provided configuration.
    - Handles authentication and joins the designated MUC room for group chat messages.
    - Processes incoming messages, including weather data products, and publishes structured events to a message bus.
    - Implements periodic housekeeping to ensure connection health, including ping/pong handling and reconnection logic.
    - Provides graceful shutdown and resource cleanup.
    - Publishes detailed connection and message processing statistics and error events for monitoring and diagnostics.

    Attributes:
        config (XMPPConfig): Configuration for the XMPP connection.
        outstanding_pings (list[str]): List of outstanding ping IDs awaiting pong responses.
        xmlstream (XmlStream | None): The active XML stream for XMPP communication.
        housekeeping_task (LoopingCall | None): Periodic task for housekeeping operations.
        is_shutting_down (bool): Indicates if the client is in the process of shutting down.
        reconnect_attempts (int): Number of consecutive reconnection attempts.
        last_message_time (float): Timestamp of the last received message.
        last_groupchat_message_time (float): Timestamp of the last received group chat message.

    Methods:
        connect(): Establishes a connection to the NWWS-OI server.
        shutdown(): Gracefully shuts down the XMPP client and cleans up resources.
        is_connected() -> bool: Returns True if the client is connected and not shutting down.

    """

    def __init__(self, config: XMPPConfig) -> None:
        """Initialize the XMPP client with configuration."""
        self.config = config
        self.outstanding_pings: list[str] = []
        self.xmlstream: XmlStream | None = None
        self.housekeeping_task: LoopingCall | None = None
        self.is_shutting_down = False
        self.reconnect_attempts = 0
        self.last_message_time = time.time()
        self.last_groupchat_message_time = time.time()

        logger.info(
            "Initializing NWWS-OI XMPP client",
            username=config.username,
            server=config.server,
        )

    def connect(self) -> None:
        """Establish connection to NWWS-OI server."""
        try:
            # Publish connection attempt event
            MessageBus.publish(Topics.STATS_CONNECTION_ATTEMPT)

            jid = JID(f"{self.config.username}@{self.config.server}")
            factory: XmlStreamFactory = client.XMPPClientFactory(jid, str(self.config.password))
            factory.addBootstrap(xmlstream.STREAM_CONNECTED_EVENT, self._on_connected)
            factory.addBootstrap(xmlstream.STREAM_AUTHD_EVENT, self._on_authenticated)

            # Add error handlers
            factory.addBootstrap(xmlstream.STREAM_END_EVENT, self._on_disconnected)
            factory.addBootstrap(xmlstream.STREAM_ERROR_EVENT, self._on_stream_error)
            factory.addBootstrap(xmlstream.INIT_FAILED_EVENT, self._on_stream_error)

            connector = SRVConnector(
                reactor,
                "xmpp-client",
                jid.host,
                factory,
                defaultPort=self.config.port,
            )
            connector.connect()

        except ConnectError as e:
            logger.error("Failed to connect", error=str(e))
            # Publish connection error event
            MessageBus.publish(Topics.STATS_CONNECTION_ERROR)
            self._schedule_reconnect()

    def _on_connected(self, xs: XmlStream) -> None:
        """Handle successful connection."""
        logger.info("Connected to NWWS-OI server")
        self.xmlstream = xs
        self.reconnect_attempts = 0

        # Add observers with error handling
        self.xmlstream.addObserver("/message", self._on_message)
        self.xmlstream.addObserver("/iq", self._on_iq)
        self.xmlstream.addObserver(STREAM_END_EVENT, self._on_disconnected)

        # Publish connection event to MessageBus
        MessageBus.publish(Topics.XMPP_CONNECTED)

    def _on_authenticated(self, _xs: XmlStream) -> None:
        """Handle successful authentication."""
        logger.info("Authenticated successfully")
        self.outstanding_pings = []

        # Record successful connection
        MessageBus.publish(Topics.STATS_CONNECTION_ESTABLISHED)

        # Join and subscribe to MUC room
        self._join_muc_room()

        # Start housekeeping task
        if self.housekeeping_task is None or not self.housekeeping_task.running:
            self.housekeeping_task = LoopingCall(self._housekeeping)
            self.housekeeping_task.start(PING_INTERVAL)

    def _join_muc_room(self) -> None:
        """Join and subscribe to the MUC room with proper configuration."""
        # Create presence with MUC extension
        presence = domish.Element(("jabber:client", "presence"))
        presence["to"] = f"{MUC_ROOM}/{datetime.now(UTC):%Y%m%d%H%M}"

        logger.info("Joining and subscribing to MUC room", room=MUC_ROOM)
        self.xmlstream.send(presence)  # type: ignore  # noqa: PGH003

        # Send a follow-up presence to ensure we're properly subscribed
        reactor.callLater(2, self._send_subscription_presence)  # type: ignore  # noqa: PGH003

    def _send_subscription_presence(self) -> None:
        """Send additional presence to ensure proper subscription."""
        if self.xmlstream is None or self.is_shutting_down:
            return

        # Send a simple presence to confirm subscription
        presence = domish.Element(("jabber:client", "presence"))
        presence["to"] = f"{MUC_ROOM}/{datetime.now(UTC):%Y%m%d%H%M}"

        self.xmlstream.send(presence)
        logger.debug("Sent subscription confirmation presence")

    def _on_disconnected(self, reason) -> None:
        """Handle disconnection."""
        if not self.is_shutting_down:
            logger.warning("Disconnected from server", reason=str(reason))
            # Publish disconnection event to MessageBus
            MessageBus.publish(Topics.XMPP_DISCONNECTED)
        else:
            logger.info("Disconnected cleanly during shutdown")

        if self.housekeeping_task and self.housekeeping_task.running:
            self.housekeeping_task.stop()

        if not self.is_shutting_down:
            self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        """Schedule reconnection attempt."""
        if self.reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
            logger.error("Maximum reconnection attempts reached")
            # Publish XMPP error event to MessageBus
            MessageBus.publish(Topics.XMPP_ERROR)
            return

        self.reconnect_attempts += 1
        # Publish reconnection attempt event
        MessageBus.publish(Topics.STATS_RECONNECT_ATTEMPT)

        delay = min(
            RECONNECT_DELAY * (2 ** (self.reconnect_attempts - 1)),
            300,
        )  # Exponential backoff, max 5 min

        logger.info(
            "Scheduling reconnection attempt",
            attempt=self.reconnect_attempts,
            delay_seconds=delay,
        )
        reactor.callLater(delay, self.connect)  # type: ignore  # noqa: PGH003

    def _housekeeping(self) -> None:
        """Periodic housekeeping tasks."""
        current_time = time.time()

        # Check for unresponsive connection
        if current_time - self.last_message_time > 300:  # 5 minutes
            logger.warning("No messages received in 5 minutes, connection may be dead")

        # Check for groupchat message timeout
        if current_time - self.last_groupchat_message_time > GROUPCHAT_MESSAGE_TIMEOUT:
            logger.warning(
                "No groupchat messages received, forcing reconnection",
                timeout_seconds=GROUPCHAT_MESSAGE_TIMEOUT,
            )
            # Publish XMPP error event to MessageBus
            MessageBus.publish(Topics.XMPP_ERROR)
            self._force_reconnect()
            return

        # Handle outstanding pings
        if self.outstanding_pings:
            logger.debug("Outstanding pings", count=len(self.outstanding_pings))

        if len(self.outstanding_pings) > MAX_UNRESPONDED_PINGS:
            logger.error("Too many unresponded pings, forcing reconnection")
            # Publish XMPP error event to MessageBus
            MessageBus.publish(Topics.XMPP_ERROR)
            self._force_reconnect()
            return

        # Send ping
        self._send_ping()

    def _send_ping(self) -> None:
        """Send ping to server."""
        if self.xmlstream is None:
            logger.warning("Cannot send ping: xmlstream is None")
            return

        utcnow = datetime.now(UTC)
        ping = domish.Element((None, "iq"))
        ping["to"] = self.config.server
        ping["type"] = "get"
        pingid = f"{utcnow:%Y%m%d%H%M%S}"
        ping["id"] = pingid
        ping.addChild(domish.Element(("urn:xmpp:ping", "ping")))

        self.outstanding_pings.append(pingid)
        self.xmlstream.send(ping)

        # Publish ping sent event
        logger.debug("Sent ping", ping_id=pingid)
        MessageBus.publish(Topics.STATS_PING_SENT)

    def _force_reconnect(self) -> None:
        """Force reconnection by closing current stream."""
        logger.info("Forcing reconnection")
        self.outstanding_pings = []

        if self.xmlstream:
            exc = error.StreamError("connection-timeout")
            self.xmlstream.send(exc)

    def _on_iq(self, elem: domish.Element) -> None:
        """Process IQ message."""
        iq_type = elem.getAttribute("type")
        logger.debug("Received IQ", type=iq_type)

        typ = elem.getAttribute("type")
        first_element = elem.firstChildElement()

        if typ == "get" and self.xmlstream and first_element and first_element.name == "ping":
            # Respond to ping request
            pong = domish.Element((None, "iq"))
            pong["type"] = "result"
            pong["to"] = elem["from"]
            pong["from"] = elem["to"]
            pong["id"] = elem["id"]
            self.xmlstream.send(pong)
            logger.debug("Responded to ping", from_jid=elem["from"])

        elif typ == "result":
            # Handle ping response
            ping_id = elem.getAttribute("id")
            if ping_id in self.outstanding_pings:
                self.outstanding_pings.remove(ping_id)
                # Publish pong received event
                MessageBus.publish(Topics.STATS_PONG_RECEIVED)
                logger.debug("Received pong for ping", ping_id=ping_id)

    def _on_message(self, elem: domish.Element) -> None:
        """Process incoming message."""
        self.last_message_time = time.time()

        # Publish message received event
        MessageBus.publish(Topics.STATS_MESSAGE_RECEIVED)

        if elem.hasAttribute("type") and elem["type"] == "groupchat":
            self._group_message(elem)

    def _group_message(self, elem: domish.Element) -> None:
        """Process group chat message containing weather data."""
        # Update groupchat message timestamp
        self.last_groupchat_message_time = time.time()
        # Publish groupchat message received event
        MessageBus.publish(Topics.STATS_GROUPCHAT_MESSAGE_RECEIVED)

        subject = str(elem.body or "")

        if not elem.x:
            logger.debug("No x element in group message, skipping")
            return

        # Process the weather product
        unix_text: str = str(elem.x)
        noaaport: str = f"\x01{unix_text.replace('\n\n', '\r\r\n')}"
        if not noaaport.endswith("\n"):
            noaaport = f"{noaaport}\r\r\n"
        noaaport = f"{noaaport}\x03"

        tp = TextProduct(noaaport, parse_segments=True, ugc_provider={})
        source = tp.source or "unknown"  # type: ignore  # noqa: PGH003
        afos = tp.afos or "unknown"  # type: ignore  # noqa: PGH003
        wmo = tp.wmo or "unknown"  # type: ignore  # noqa: PGH003
        product_id = tp.get_product_id()

        if not product_id:
            logger.warning("Product has no ID, skipping", source=source, afos=afos, wmo=wmo)
            MessageBus.publish(Topics.STATS_MESSAGE_FAILED)
            return

        logger.info("product", subject=subject, product_id=product_id)

        # Record successful processing
        MessageBus.publish(
            Topics.STATS_MESSAGE_PROCESSED,
            message=StatsMessageProcessingMessage(
                source=source,
                afos=afos,
                wmo=wmo,
            ),
        )

        # Output structured data
        try:
            model = convert_text_product_to_model(tp)
        except TextProductException as e:
            logger.warning("Failed to parse text product", error=str(e))
            MessageBus.publish(
                Topics.STATS_MESSAGE_FAILED,
                message=StatsMessageProcessingMessage(
                    source=source,
                    afos=afos,
                    wmo=wmo,
                    error_type=str(e),
                ),
            )
            return

        try:
            model_json = json.dumps(
                model.model_dump(mode="json", by_alias=True, exclude_defaults=True),
                sort_keys=True,
                indent=1,
            )
        except (TypeError, ValueError, RecursionError) as e:
            logger.error(
                "Failed to serialize product",
                product_id=product_id,
                error=str(e),
            )
            MessageBus.publish(Topics.STATS_MESSAGE_FAILED)
            return

        # Publish product message to pubsub system
        product_message = ProductMessage(
            source=source,
            afos=afos[:3],
            product_id=product_id,
            structured_data=model_json,
            subject=subject,
        )

        MessageBus.publish(Topics.PRODUCT_RECEIVED, message=product_message)

        # Record successful publishing
        MessageBus.publish(Topics.STATS_MESSAGE_PUBLISHED)

    def _on_stream_error(self, failure) -> None:
        """Handle stream errors, such as authentication failures."""
        logger.error("Stream error (likely authentication failure)", failure=str(failure))
        # Publish XMPP error event to MessageBus
        MessageBus.publish(Topics.XMPP_ERROR, message=f"Stream error: {failure}")

    def shutdown(self) -> None:
        """Gracefully shutdown the XMPP client."""
        if self.is_shutting_down:
            return

        logger.info("Shutting down NWWS-OI XMPP client")
        self.is_shutting_down = True

        if self.housekeeping_task and self.housekeeping_task.running:
            self.housekeeping_task.stop()

        if self.xmlstream:
            # Send presence unavailable to leave the MUC room
            presence = domish.Element(("jabber:client", "presence"))
            presence["type"] = "unavailable"
            presence["to"] = f"{MUC_ROOM}/{datetime.now(UTC):%Y%m%d%H%M}"
            self.xmlstream.send(presence)
            logger.info("Left MUC room")

            # Properly close the XML stream
            if self.xmlstream.transport:
                self.xmlstream.transport.loseConnection()
                logger.info("Closed XML stream connection")

    def is_connected(self) -> bool:
        """Check if the XMPP client is connected."""
        return self.xmlstream is not None and not self.is_shutting_down
