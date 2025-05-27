"""NWWS-OI XMPP client implementation."""

import json
import time
from dataclasses import dataclass
from typing import Callable

from loguru import logger
from pyiem.exceptions import TextProductException
from pyiem.nws.product import TextProduct
from pyiem.util import utc
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.names.srvconnect import SRVConnector
from twisted.words.protocols.jabber import client, error, xmlstream
from twisted.words.protocols.jabber.jid import JID
from twisted.words.xish import domish
from twisted.words.xish.xmlstream import STREAM_END_EVENT, XmlStream

from models import convert_text_product_to_model
from messaging import MessageBus, ProductMessage, Topics


# Configuration constants
MUC_ROOM = "nwws@conference.nwws-oi.weather.gov"
MAX_UNRESPONDED_PINGS = 5
PING_INTERVAL = 60
RECONNECT_DELAY = 30
MAX_RECONNECT_ATTEMPTS = 10
GROUPCHAT_MESSAGE_TIMEOUT = 300  # 5 minutes


@dataclass
class XMPPConfig:
    """Configuration class for XMPP client."""
    username: str
    password: str
    server: str = "nwws-oi.weather.gov"
    port: int = 5222


class NWWSXMPPClient:
    """Enhanced NWWS-OI XMPP Client."""

    def __init__(self, config: XMPPConfig, stats_collector=None) -> None:
        """Initialize the XMPP client with configuration."""
        self.config = config
        self.stats_collector = stats_collector
        self.outstanding_pings: list[str] = []
        self.xmlstream: XmlStream | None = None
        self.housekeeping_task: LoopingCall | None = None
        self.is_shutting_down = False
        self.reconnect_attempts = 0
        self.last_message_time = time.time()
        self.last_groupchat_message_time = time.time()

        # Callbacks for client lifecycle events
        self._on_connected_callback: Callable[[], None] | None = None
        self._on_disconnected_callback: Callable[[], None] | None = None
        self._on_error_callback: Callable[[str], None] | None = None

        logger.info("Initializing NWWS-OI XMPP client", 
                   username=config.username, server=config.server)

    def set_callbacks(self, 
                      on_connected: Callable[[], None] | None = None,
                      on_disconnected: Callable[[], None] | None = None,
                      on_error: Callable[[str], None] | None = None) -> None:
        """Set lifecycle callback functions."""
        self._on_connected_callback = on_connected
        self._on_disconnected_callback = on_disconnected
        self._on_error_callback = on_error

    def connect(self) -> None:
        """Establish connection to NWWS-OI server."""
        try:
            if self.stats_collector:
                self.stats_collector.on_connection_attempt()
                
            jid = JID(f"{self.config.username}@{self.config.server}")
            factory = client.XMPPClientFactory(jid, self.config.password)
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

        except Exception as e:
            logger.error("Failed to connect", error=str(e))
            if self.stats_collector:
                self.stats_collector.on_connection_error()
            if self._on_error_callback:
                self._on_error_callback(f"Connection failed: {e}")
            self._schedule_reconnect()

    def _on_connected(self, xs: XmlStream) -> None:
        """Handle successful connection."""
        logger.info("Connected to NWWS-OI server")
        self.xmlstream = xs
        self.reconnect_attempts = 0

        # Add observers with error handling
        self.xmlstream.addObserver("/message", self._safe_on_message)
        self.xmlstream.addObserver("/iq", self._safe_on_iq)
        self.xmlstream.addObserver(STREAM_END_EVENT, self._on_disconnected)

        if self._on_connected_callback:
            self._on_connected_callback()

    def _on_authenticated(self, _xs: XmlStream) -> None:
        """Handle successful authentication."""
        logger.info("Authenticated successfully")
        self.outstanding_pings = []

        # Record successful connection
        if self.stats_collector:
            self.stats_collector.on_connected()

        # Join and subscribe to MUC room
        try:
            self._join_muc_room()

            # Start housekeeping task
            if self.housekeeping_task is None or not self.housekeeping_task.running:
                self.housekeeping_task = LoopingCall(self._housekeeping)
                self.housekeeping_task.start(PING_INTERVAL)

        except Exception as e:
            logger.error("Failed during authentication", error=str(e))
            if self._on_error_callback:
                self._on_error_callback(f"Authentication setup failed: {e}")

    def _join_muc_room(self) -> None:
        """Join and subscribe to the MUC room with proper configuration."""
        if self.xmlstream is None:
            logger.error("xmlstream is None, cannot join MUC room")
            return

        try:
            # Create presence with MUC extension
            presence = domish.Element(("jabber:client", "presence"))
            presence["to"] = f"{MUC_ROOM}/{utc():%Y%m%d%H%M}"

            logger.info("Joining and subscribing to MUC room", room=MUC_ROOM)
            self.xmlstream.send(presence)

            # Send a follow-up presence to ensure we're properly subscribed
            reactor.callLater(2, self._send_subscription_presence)

        except Exception as e:
            logger.error("Failed to join MUC room", error=str(e))
            if self._on_error_callback:
                self._on_error_callback(f"Failed to join MUC room: {e}")

    def _send_subscription_presence(self) -> None:
        """Send additional presence to ensure proper subscription."""
        if self.xmlstream is None or self.is_shutting_down:
            return

        try:
            # Send a simple presence to confirm subscription
            presence = domish.Element(("jabber:client", "presence"))
            presence["to"] = f"{MUC_ROOM}/{utc():%Y%m%d%H%M}"

            self.xmlstream.send(presence)
            logger.debug("Sent subscription confirmation presence")

        except Exception as e:
            logger.error("Failed to send subscription presence", error=str(e))

    def _on_disconnected(self, reason) -> None:
        """Handle disconnection."""
        if not self.is_shutting_down:
            logger.warning("Disconnected from server", reason=str(reason))
        else:
            logger.info("Disconnected cleanly during shutdown")

        if self.housekeeping_task and self.housekeeping_task.running:
            self.housekeeping_task.stop()

        if self._on_disconnected_callback and not self.is_shutting_down:
            self._on_disconnected_callback()

        if not self.is_shutting_down:
            self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        """Schedule reconnection attempt."""
        if self.reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
            logger.error("Maximum reconnection attempts reached")
            if self._on_error_callback:
                self._on_error_callback("Maximum reconnection attempts reached")
            return

        self.reconnect_attempts += 1
        if self.stats_collector:
            self.stats_collector.on_reconnect_attempt()
            
        delay = min(RECONNECT_DELAY * (2 ** (self.reconnect_attempts - 1)), 300)  # Exponential backoff, max 5 min

        logger.info("Scheduling reconnection attempt", 
                   attempt=self.reconnect_attempts, 
                   delay_seconds=delay)
        reactor.callLater(delay, self.connect)

    def _housekeeping(self) -> None:
        """Periodic housekeeping tasks."""
        try:
            current_time = time.time()

            # Check for unresponsive connection
            if current_time - self.last_message_time > 300:  # 5 minutes
                logger.warning("No messages received in 5 minutes, connection may be dead")

            # Check for groupchat message timeout
            if current_time - self.last_groupchat_message_time > GROUPCHAT_MESSAGE_TIMEOUT:
                logger.warning("No groupchat messages received, forcing reconnection", 
                             timeout_seconds=GROUPCHAT_MESSAGE_TIMEOUT)
                self._force_reconnect()
                return

            # Handle outstanding pings
            if self.outstanding_pings:
                logger.debug("Outstanding pings", count=len(self.outstanding_pings))

            if len(self.outstanding_pings) > MAX_UNRESPONDED_PINGS:
                logger.error("Too many unresponded pings, forcing reconnection")
                self._force_reconnect()
                return

            # Send ping
            self._send_ping()

        except Exception as e:
            logger.error("Error in housekeeping", error=str(e))

    def _send_ping(self) -> None:
        """Send ping to server."""
        if self.xmlstream is None:
            logger.warning("Cannot send ping: xmlstream is None")
            return

        try:
            utcnow = utc()
            ping = domish.Element((None, "iq"))
            ping["to"] = self.config.server
            ping["type"] = "get"
            pingid = f"{utcnow:%Y%m%d%H%M%S}"
            ping["id"] = pingid
            ping.addChild(domish.Element(("urn:xmpp:ping", "ping")))

            self.outstanding_pings.append(pingid)
            self.xmlstream.send(ping)
            
            if self.stats_collector:
                self.stats_collector.on_ping_sent()
                
            logger.debug("Sent ping", ping_id=pingid)

        except Exception as e:
            logger.error("Failed to send ping", error=str(e))

    def _force_reconnect(self) -> None:
        """Force reconnection by closing current stream."""
        logger.info("Forcing reconnection")
        self.outstanding_pings = []

        if self.xmlstream:
            try:
                exc = error.StreamError("connection-timeout")
                self.xmlstream.send(exc)
            except Exception as e:
                logger.debug("Error sending stream error", error=str(e))

    def _safe_on_iq(self, elem: domish.Element) -> None:
        """Safely handle IQ messages."""
        try:
            self._on_iq(elem)
        except Exception as e:
            logger.error("Error processing IQ message", error=str(e))

    def _on_iq(self, elem: domish.Element) -> None:
        """Process IQ message."""
        iq_type = elem.getAttribute('type')
        logger.debug("Received IQ", type=iq_type)

        typ = elem.getAttribute("type")
        first_element = elem.firstChildElement()

        if typ == "get" and self.xmlstream and first_element and first_element.name == "ping":
            # Respond to ping request
            try:
                pong = domish.Element((None, "iq"))
                pong["type"] = "result"
                pong["to"] = elem["from"]
                pong["from"] = elem["to"]
                pong["id"] = elem["id"]
                self.xmlstream.send(pong)
                logger.debug("Responded to ping", from_jid=elem['from'])
            except Exception as e:
                logger.error("Failed to respond to ping", error=str(e))

        elif typ == "result":
            # Handle ping response
            ping_id = elem.getAttribute("id")
            if ping_id in self.outstanding_pings:
                self.outstanding_pings.remove(ping_id)
                if self.stats_collector:
                    self.stats_collector.on_pong_received()
                logger.debug("Received pong for ping", ping_id=ping_id)

    def _safe_on_message(self, elem: domish.Element) -> None:
        """Safely handle incoming messages."""
        try:
            self.last_message_time = time.time()
            if self.stats_collector:
                self.stats_collector.on_message_received()
            self._on_message(elem)
        except Exception as e:
            logger.error("Error processing message", error=str(e))

    def _on_message(self, elem: domish.Element) -> None:
        """Process incoming message."""
        if elem.hasAttribute("type") and elem["type"] == "groupchat":
            self._group_message(elem)

    def _group_message(self, elem: domish.Element) -> None:
        """Process group chat message containing weather data."""
        # Update groupchat message timestamp
        self.last_groupchat_message_time = time.time()
        if self.stats_collector:
            self.stats_collector.on_groupchat_message_received()

        try:
            subject = str(elem.body or "")

            if not elem.x:
                logger.debug("No x element in group message, skipping")
                return

            unixtext = str(elem.x)

            # Process the weather product
            noaaport = "\001" + unixtext.replace("\n\n", "\r\r\n")
            if noaaport[-1] != "\n":
                noaaport = noaaport + "\r\r\n"
            noaaport = noaaport + "\003"

            try:
                tp = TextProduct(noaaport, parse_segments=True, ugc_provider={})
                source = tp.source or "unknown"
                afos = tp.afos or "unknown"
                product_id = tp.get_product_id()
                if product_id:
                    logger.info("product", subject=subject, product_id=product_id)

                    # Record successful processing
                    if self.stats_collector:
                        self.stats_collector.on_message_processed(source, afos, product_id)

                    # Output structured data
                    try:
                        model = convert_text_product_to_model(tp)
                        model_json = json.dumps(model.model_dump(
                            mode="json",
                            by_alias=True,
                            exclude_defaults=True
                        ), sort_keys=True, indent=1)

                        # Publish product message to pubsub system
                        product_message = ProductMessage(
                            source=source,
                            afos=afos[:3], 
                            product_id=product_id,
                            structured_data=model_json,
                            subject=subject
                        )
                        
                        MessageBus.publish(Topics.PRODUCT_RECEIVED, message=product_message)
                        
                        # Record successful publishing
                        if self.stats_collector:
                            self.stats_collector.on_message_published()

                    except Exception as e:
                        logger.error("Failed to serialize product", product_id=product_id, error=str(e))
                        if self.stats_collector:
                            self.stats_collector.on_message_failed("serialization_error")
                else:
                    logger.debug("Product has no ID, skipping")

            except TextProductException as e:
                logger.warning("Failed to parse text product", error=str(e))
                if self.stats_collector:
                    self.stats_collector.on_message_failed("parse_error")
            except Exception as e:
                logger.error("Unexpected error parsing product", error=str(e))
                if self.stats_collector:
                    self.stats_collector.on_message_failed("unexpected_error")

        except Exception as e:
            logger.error("Error processing group message", error=str(e))
            if self.stats_collector:
                self.stats_collector.on_message_failed("processing_error")

    def _on_stream_error(self, failure) -> None:
        """Handle stream errors, such as authentication failures."""
        logger.error("Stream error (likely authentication failure)", failure=str(failure))
        if self._on_error_callback:
            self._on_error_callback(f"Stream error: {failure}")

    def shutdown(self) -> None:
        """Gracefully shutdown the XMPP client."""
        if self.is_shutting_down:
            return

        logger.info("Shutting down NWWS-OI XMPP client")
        self.is_shutting_down = True

        if self.housekeeping_task and self.housekeeping_task.running:
            self.housekeeping_task.stop()

        if self.xmlstream:
            try:
                # Send presence unavailable to leave the MUC room
                presence = domish.Element(("jabber:client", "presence"))
                presence["type"] = "unavailable"
                presence["to"] = f"{MUC_ROOM}/{utc():%Y%m%d%H%M}"
                self.xmlstream.send(presence)
                logger.info("Left MUC room")

                # Properly close the XML stream
                if self.xmlstream.transport:
                    self.xmlstream.transport.loseConnection()
                    logger.info("Closed XML stream connection")

            except Exception as e:
                logger.debug("Error during XMPP shutdown cleanup", error=str(e))

    def is_connected(self) -> bool:
        """Check if the XMPP client is connected."""
        return self.xmlstream is not None and not self.is_shutting_down
