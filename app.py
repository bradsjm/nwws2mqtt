"""Ingest data from NWWS-OI."""

import asyncio
import os
import signal
import sys
import threading
from dataclasses import dataclass
from types import FrameType

from dotenv import load_dotenv
from loguru import logger
from twisted.internet import reactor

from handlers import OutputConfig, OutputManager
from client.xmpp import NWWSXMPPClient, XMPPConfig

"""
This script connects to the NWWS-OI XMPP server and listens for messages in the
NWWs conference room. It processes incoming messages, extracts the text product,
and publishes structured data. It includes comprehensive error handling, connection
monitoring, and graceful shutdown capabilities.
"""

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


class NWWSApplication:
    """NWWS-OI Application orchestrator."""

    def __init__(self, config: Config) -> None:
        """Initialize the application with configuration."""
        self.config = config
        self.is_shutting_down = False

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

        # Create XMPP client
        xmpp_config = XMPPConfig(
            username=config.username,
            password=config.password,
            server=config.server,
            port=config.port
        )
        self.xmpp_client = NWWSXMPPClient(xmpp_config, self.output_manager)
        
        # Set up XMPP client callbacks
        self.xmpp_client.set_callbacks(
            on_connected=self._on_xmpp_connected,
            on_disconnected=self._on_xmpp_disconnected,
            on_error=self._on_xmpp_error
        )

        logger.info("Starting NWWS-OI application",
                   username=config.username, server=config.server)

        # Start output handlers
        self._start_output_handlers()

        # Connect to XMPP server
        self.xmpp_client.connect()

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
        reactor.callFromThread(self.shutdown)

    def _on_xmpp_connected(self) -> None:
        """Handle XMPP client connection."""
        logger.info("XMPP client connected successfully")

    def _on_xmpp_disconnected(self) -> None:
        """Handle XMPP client disconnection."""
        if not self.is_shutting_down:
            logger.warning("XMPP client disconnected unexpectedly")

    def _on_xmpp_error(self, error_msg: str) -> None:
        """Handle XMPP client errors."""
        logger.error(f"XMPP client error: {error_msg}")
        if "Maximum reconnection attempts reached" in error_msg or "authentication failure" in error_msg:
            logger.error("Fatal XMPP error, shutting down application")
            self.shutdown()

    def shutdown(self) -> None:
        """Gracefully shutdown the application."""
        if self.is_shutting_down:
            return

        logger.info("Shutting down NWWS-OI application")
        self.is_shutting_down = True

        # Shutdown XMPP client first
        try:
            self.xmpp_client.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down XMPP client: {e}")

        # Stop output handlers
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

        # Give time for cleanup before stopping reactor
        reactor.callLater(1.0, self._final_shutdown)

    def _final_shutdown(self) -> None:
        """Final shutdown step - stop the reactor."""
        logger.info("Stopping reactor")
        reactor.stop()


def main() -> None:
    """Main entry point."""
    try:
        config = Config.from_env()
        _app = NWWSApplication(config)
        reactor.run()

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        logger.info("NWWS-OI application stopped")


if __name__ == "__main__":
    main()
