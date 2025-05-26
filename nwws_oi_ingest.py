"""Ingest data from NWWS-OI."""

import asyncio
import os
import signal
import sys
import threading
import time
import json
from dataclasses import dataclass
from types import FrameType

from dotenv import load_dotenv
from loguru import logger
from pyiem.exceptions import TextProductException
from pyiem.nws.product import TextProduct
from pyiem.util import utc
from twisted.internet import reactor  # type: ignore[import]
from twisted.internet.task import LoopingCall
from twisted.names.srvconnect import SRVConnector
from twisted.words.protocols.jabber import client, error, xmlstream
from twisted.words.protocols.jabber.jid import JID
from twisted.words.xish import domish
from twisted.words.xish.xmlstream import STREAM_END_EVENT, XmlStream
from models import convert_text_product_to_model

from output_handlers import OutputConfig, OutputManager

"""
This script connects to the NWWS-OI XMPP server and listens for messages in the
NWWs conference room. It processes incoming messages, extracts the text product,
and publishes structured data. It includes comprehensive error handling, connection
monitoring, and graceful shutdown capabilities.
"""

# Configuration constants
MUC_ROOM = "nwws@conference.nwws-oi.weather.gov"
MAX_UNRESPONDED_PINGS = 5
PING_INTERVAL = 60
RECONNECT_DELAY = 30
MAX_RECONNECT_ATTEMPTS = 10
GROUPCHAT_MESSAGE_TIMEOUT = 300  # 5 minutes

load_dotenv(override=True)  # Load environment variables from .env file


@dataclass
class Config:
    """Configuration class for NWWS-OI client."""
    username: str
    password: str
    server: str = "nwws-oi.weather.gov"
    port: int = 5222
    log_level: str = "INFO"
    log_file: str | None = None
    output_config: OutputConfig | None = None

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables."""
        username = os.getenv("NWWS_USERNAME")
        password = os.getenv("NWWS_PASSWORD")

        if not username or not password:
            raise ValueError("NWWS_USERNAME and NWWS_PASSWORD environment variables must be set")

        return cls(
            username=username,
            password=password,
            server=os.getenv("NWWS_SERVER", "nwws-oi.weather.gov"),
            port=int(os.getenv("NWWS_PORT", "5222")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE"),
            output_config=OutputConfig.from_env(),
        )


class NWWSClient:
    """Enhanced NWWS-OI Jabber Client."""

    def __init__(self, config: Config) -> None:
        """Initialize the client with configuration."""
        self.config = config
        self.outstanding_pings: list[str] = []
        self.xmlstream: XmlStream | None = None
        self.housekeeping_task: LoopingCall | None = None
        self.is_shutting_down = False
        self.reconnect_attempts = 0
        self.last_message_time = time.time()
        self.last_groupchat_message_time = time.time()

        # Initialize output manager
        if config.output_config:
            self.output_manager = OutputManager(config.output_config)
        else:
            # Fallback to console output
            fallback_config = OutputConfig(enabled_handlers=["console"])
            self.output_manager = OutputManager(fallback_config)

        # Setup enhanced logging
        self._setup_logging()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("Starting NWWS-OI client",
                   username=config.username, server=config.server)

        # Start output handlers (we'll handle this in the twisted reactor context)
        self._start_output_handlers()

        self._connect()

    def _start_output_handlers(self) -> None:
        """Start output handlers in the reactor context."""
        def start_handlers():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.output_manager.start())
                logger.info("Output handlers started successfully")
            except Exception as e:
                logger.error(f"Failed to start output handlers: {e}")
            finally:
                loop.close()

        # Run in a separate thread to avoid blocking the reactor
        handler_thread = threading.Thread(target=start_handlers, daemon=True)
        handler_thread.start()

    def _setup_logging(self) -> None:
        """Configure structured logging."""
        logger.remove()  # Remove default handler
        logger.add(
            sys.stdout,
            level=self.config.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                   "<level>{message}</level>",
            serialize=False,
        )

        # Only add file logging if log_file is specified
        if self.config.log_file:
            logger.add(
                self.config.log_file,
                level=self.config.log_level,
                rotation="10 MB",
                retention="7 days",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            )
            logger.info(f"File logging enabled: {self.config.log_file}")

    def _signal_handler(self, signum: int, _frame: FrameType | None) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        reactor.callFromThread(self.shutdown) # type: ignore[no-untyped-call]

    def _connect(self) -> None:
        """Establish connection to NWWS-OI server."""
        try:
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
            logger.error(f"Failed to connect: {e}")
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

    def _on_authenticated(self, _xs: XmlStream) -> None:
        """Handle successful authentication."""
        logger.info("Authenticated successfully")
        self.outstanding_pings = []

        # Join and subscribe to MUC room
        try:
            self._join_muc_room()

            # Start housekeeping task
            if self.housekeeping_task is None or not self.housekeeping_task.running:
                self.housekeeping_task = LoopingCall(self._housekeeping)
                self.housekeeping_task.start(PING_INTERVAL)

        except Exception as e:
            logger.error(f"Failed during authentication: {e}")

    def _join_muc_room(self) -> None:
        """Join and subscribe to the MUC room with proper configuration."""
        if self.xmlstream is None:
            logger.error("xmlstream is None, cannot join MUC room")
            return

        try:
            # Create presence with MUC extension
            presence = domish.Element(("jabber:client", "presence"))
            presence["to"] = f"{MUC_ROOM}/{utc():%Y%m%d%H%M}"

            logger.info(f"Joining and subscribing to MUC room: {MUC_ROOM}")
            self.xmlstream.send(presence)

            # Send a follow-up presence to ensure we're properly subscribed
            reactor.callLater(2, self._send_subscription_presence) # type: ignore[no-untyped-call]

        except Exception as e:
            logger.error(f"Failed to join MUC room: {e}")

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
            logger.error(f"Failed to send subscription presence: {e}")

    def _on_disconnected(self, reason) -> None:
        """Handle disconnection."""
        if not self.is_shutting_down:
            logger.warning(f"Disconnected from server: {reason}")
        else:
            logger.info("Disconnected cleanly during shutdown")

        if self.housekeeping_task and self.housekeeping_task.running:
            self.housekeeping_task.stop()

        if not self.is_shutting_down:
            self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        """Schedule reconnection attempt."""
        if self.reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
            logger.error("Maximum reconnection attempts reached, shutting down")
            self.shutdown()
            return

        self.reconnect_attempts += 1
        delay = min(RECONNECT_DELAY * (2 ** (self.reconnect_attempts - 1)), 300)  # Exponential backoff, max 5 min

        logger.info(f"Scheduling reconnection attempt {self.reconnect_attempts} in {delay} seconds")
        reactor.callLater(delay, self._connect) # type: ignore[no-untyped-def]

    def _housekeeping(self) -> None:
        """Periodic housekeeping tasks."""
        try:
            current_time = time.time()

            # Check for unresponsive connection
            if current_time - self.last_message_time > 300:  # 5 minutes
                logger.warning("No messages received in 5 minutes, connection may be dead")

            # Check for groupchat message timeout
            if current_time - self.last_groupchat_message_time > GROUPCHAT_MESSAGE_TIMEOUT:
                logger.warning(f"No groupchat messages received in {GROUPCHAT_MESSAGE_TIMEOUT} seconds, forcing reconnection")
                self._force_reconnect()
                return

            # Handle outstanding pings
            if self.outstanding_pings:
                logger.debug(f"Outstanding pings: {len(self.outstanding_pings)}")

            if len(self.outstanding_pings) > MAX_UNRESPONDED_PINGS:
                logger.error("Too many unresponded pings, forcing reconnection")
                self._force_reconnect()
                return

            # Send ping
            self._send_ping()

        except Exception as e:
            logger.error(f"Error in housekeeping: {e}")

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
            logger.debug(f"Sent ping with ID: {pingid}")

        except Exception as e:
            logger.error(f"Failed to send ping: {e}")

    def _force_reconnect(self) -> None:
        """Force reconnection by closing current stream."""
        logger.info("Forcing reconnection")
        self.outstanding_pings = []

        if self.xmlstream:
            try:
                exc = error.StreamError("connection-timeout")
                self.xmlstream.send(exc)
            except Exception as e:
                logger.debug(f"Error sending stream error: {e}")

    def _safe_on_iq(self, elem: domish.Element) -> None:
        """Safely handle IQ messages."""
        try:
            self._on_iq(elem)
        except Exception as e:
            logger.error(f"Error processing IQ message: {e}")

    def _on_iq(self, elem: domish.Element) -> None:
        """Process IQ message."""
        logger.debug(f"Received IQ type: {elem.getAttribute('type')}")

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
                logger.debug(f"Responded to ping from {elem['from']}")
            except Exception as e:
                logger.error(f"Failed to respond to ping: {e}")

        elif typ == "result":
            # Handle ping response
            ping_id = elem.getAttribute("id")
            if ping_id in self.outstanding_pings:
                self.outstanding_pings.remove(ping_id)
                logger.debug(f"Received pong for ping ID: {ping_id}")

    def _safe_on_message(self, elem: domish.Element) -> None:
        """Safely handle incoming messages."""
        try:
            self.last_message_time = time.time()
            self._on_message(elem)
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _on_message(self, elem: domish.Element) -> None:
        """Process incoming message."""
        if elem.hasAttribute("type") and elem["type"] == "groupchat":
            self._process_group_message(elem)

    def _process_group_message(self, elem: domish.Element) -> None:
        """Process group chat message containing weather data."""
        # Update groupchat message timestamp
        self.last_groupchat_message_time = time.time()

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
                    logger.info(f"Processed product: {product_id}", subject=subject)

                    # Output structured data
                    try:
                        model = convert_text_product_to_model(tp)
                        model_json = json.dumps(model.model_dump(
                            mode="json",
                            by_alias=True,
                            exclude_defaults=True
                        ), sort_keys=True, indent=1)

                        # Publish to all configured output handlers
                        def publish_data():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(
                                    self.output_manager.publish(
                                        source, afos[:3], product_id, model_json, subject
                                    )
                                )
                            except Exception as e:
                                logger.error(f"Failed to publish data: {e}")
                            finally:
                                loop.close()

                        # Run in a separate thread to avoid blocking the reactor
                        publish_thread = threading.Thread(target=publish_data, daemon=True)
                        publish_thread.start()

                    except Exception as e:
                        logger.error(f"Failed to serialize product {product_id}: {e}")
                else:
                    logger.debug("Product has no ID, skipping")

            except TextProductException as e:
                logger.warning(f"Failed to parse text product: {e}")
            except Exception as e:
                logger.error(f"Unexpected error parsing product: {e}")

        except Exception as e:
            logger.error(f"Error processing group message: {e}")

    def _on_stream_error(self, failure) -> None:
        """Handle stream errors, such as authentication failures."""
        logger.error(f"Stream error (likely authentication failure): {failure}")
        self.shutdown()

    def shutdown(self) -> None:
        """Gracefully shutdown the client."""
        if self.is_shutting_down:
            return

        logger.info("Shutting down NWWS-OI client")
        self.is_shutting_down = True

        # Stop output handlers first
        try:
            def stop_handlers():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.output_manager.stop())
                    logger.info("Output handlers stopped")
                except Exception as e:
                    logger.error(f"Error stopping output handlers: {e}")
                finally:
                    loop.close()

            stop_thread = threading.Thread(target=stop_handlers, daemon=True)
            stop_thread.start()
            stop_thread.join(timeout=5.0)  # Wait up to 5 seconds
        except Exception as e:
            logger.error(f"Error during output handler shutdown: {e}")

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

                # Give time for the stream to close properly before stopping reactor
                reactor.callLater(1.0, self._final_shutdown) # type: ignore[no-untyped-call]

            except Exception as e:
                logger.debug(f"Error during shutdown cleanup: {e}")
                reactor.callLater(0.5, self._final_shutdown) # type: ignore[no-untyped-call]
        else:
            self._final_shutdown()

    def _final_shutdown(self) -> None:
        """Final shutdown step - stop the reactor."""
        logger.info("Stopping reactor")
        reactor.stop() # type: ignore[no-untyped-call]


def main() -> None:
    """Main entry point."""
    try:
        config = Config.from_env()
        _client = NWWSClient(config)
        reactor.run() # type: ignore[no-untyped-call]

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        logger.info("NWWS-OI client stopped")


if __name__ == "__main__":
    main()
