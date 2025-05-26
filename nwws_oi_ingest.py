"""Ingest data from NWWS-OI."""

import os

import jsonpickle
from dotenv import load_dotenv
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

MUC_ROOM = "nwws@conference.nwws-oi.weather.gov"
MAX_UNRESPONDED_PINGS = 5

load_dotenv()  # Load environment variables from .env file if it exists


class Client:
    """A Jabber Client."""

    def __init__(self, jid: JID, secret: str) -> None:
        """Constructor."""
        self.outstanding_pings = []
        self.xmlstream = None
        f = client.XMPPClientFactory(jid, secret)
        f.addBootstrap(xmlstream.STREAM_CONNECTED_EVENT, self.connected)
        f.addBootstrap(xmlstream.STREAM_AUTHD_EVENT, self.authd)
        connector = SRVConnector(
            reactor,
            "xmpp-client",
            jid.host,
            f,
            defaultPort=5222,
        )
        connector.connect()

    def connected(self, xs: XmlStream) -> None:
        """Connected."""
        logger.info("Connected.")
        self.xmlstream = xs
        self.xmlstream.addObserver("/message", self.on_message)
        self.xmlstream.addObserver("/iq", self.on_iq)

    def authd(self, _xs: XmlStream) -> None:
        """authedn..."""
        self.outstanding_pings = []
        presence = domish.Element(("jabber:client", "presence"))
        presence["to"] = f"{MUC_ROOM}/{utc():%Y%m%d%H%M}"
        if self.xmlstream is None:
            logger.warning("xmlstream is None, not sending presence")
            return
        logger.info(f"Joining MUC: {MUC_ROOM}")
        self.xmlstream.send(presence)
        lc = LoopingCall(self.housekeeping)
        lc.start(60)
        self.xmlstream.addObserver(STREAM_END_EVENT, lambda _x: lc.stop)

    def housekeeping(self) -> None:
        """
        This gets exec'd every minute to keep up after ourselves
        1. XMPP Server Ping
        2. Update presence
        """
        if self.outstanding_pings:
            logger.warning(f"Currently unresponded pings: {self.outstanding_pings}")
        if len(self.outstanding_pings) > MAX_UNRESPONDED_PINGS:
            self.outstanding_pings = []
            if self.xmlstream is not None:
                # Unsure of the proper code that a client should generate
                exc = error.StreamError("gone")
                self.xmlstream.send(exc)
            return
        if self.xmlstream is None:
            logger.warning("xmlstream is None, not sending ping")
            return
        utcnow = utc()
        ping = domish.Element((None, "iq"))
        ping["to"] = "nwws-oi.weather.gov"
        ping["type"] = "get"
        pingid = f"{utcnow:%Y%m%d%H%M}"
        ping["id"] = pingid
        ping.addChild(domish.Element(("urn:xmpp:ping", "ping")))
        self.outstanding_pings.append(pingid)
        self.xmlstream.send(ping)

    def on_iq(self, elem: domish.Element) -> None:
        """Process IQ message."""
        logger.debug(f"Received IQ: {elem.toXml()}")
        typ = elem.getAttribute("type")
        # A response is being requested of us.
        first_element = elem.firstChildElement()
        if typ == "get" and self.xmlstream and first_element and first_element.name == "ping":
            # Respond to a ping request.
            pong = domish.Element((None, "iq"))
            pong["type"] = "result"
            pong["to"] = elem["from"]
            pong["from"] = elem["to"]
            pong["id"] = elem["id"]
            self.xmlstream.send(pong)
        # We are getting a response to a request we sent, maybe.
        elif typ == "result":
            if elem.getAttribute("id") in self.outstanding_pings:
                self.outstanding_pings.remove(elem.getAttribute("id"))

    def on_message(self, elem: domish.Element) -> None:
        """Callback."""
        if elem.hasAttribute("type") and elem["type"] == "groupchat":
            self.process_group_msg(elem)

    def process_group_msg(self, elem: domish.Element) -> None:
        """Got message."""
        subject = str(elem.body or "")
        if not elem.x:
            logger.warning("No x element in group message, skipping")
            return
        unixtext = str(elem.x)
        noaaport = "\001" + unixtext.replace("\n\n", "\r\r\n")
        # Ensure product ends with \n
        if noaaport[-1] != "\n":
            noaaport = noaaport + "\r\r\n"
        noaaport = noaaport + "\003"
        try:
            tp = TextProduct(noaaport, parse_segments=True, ugc_provider={})
            product_id = tp.get_product_id()
            if product_id:
                logger.info(f"{tp.get_product_id()} {subject}")
                print(jsonpickle.encode(tp, unpicklable=False, indent=2))
        except TextProductException:
            logger.exception("Failed to parse product")


def main() -> None:
    """Main entry point."""
    username = os.getenv("USERNAME", "jonathan.bradshaw")
    password = os.getenv("PASSWORD", "Temp4Now!")
    Client(
        JID(f"{username}@nwws-oi.weather.gov"),
        password,
    )
    reactor.run()  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()
