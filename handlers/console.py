"""Console output handler for NWWS-OI data."""

from loguru import logger

from .base import OutputHandler


class ConsoleOutputHandler(OutputHandler):
    """Output handler that prints to console."""

    async def publish(self, source: str, afos: str, product_id: str, structured_data: str, subject: str = "") -> None:
        """Print structured data to console."""
        try:
            # Use logger instead of print to be consistent with the rest of the application
            logger.info(f"Product {product_id}: {structured_data}")
        except Exception as e:
            logger.error(f"Failed to publish to console: {e}")

    async def start(self) -> None:
        """Start console handler (no-op)."""
        logger.info("Console output handler started")

    async def stop(self) -> None:
        """Stop console handler (no-op)."""
        logger.info("Console output handler stopped")

    @property
    def is_connected(self) -> bool:
        """Console is always available."""
        return True
