"""Console output handler for NWWS-OI data."""

from loguru import logger

from .base import OutputHandler


class ConsoleOutputHandler(OutputHandler):
    """output handler that prints to console."""

    async def _start_handler(self) -> None:
        """Start console handler (no-op)."""
        logger.info("console output handler starting")

    async def _stop_handler(self) -> None:
        """Stop console handler (no-op)."""
        logger.info("console output handler stopping")

    async def publish(self, source: str, afos: str, product_id: str, structured_data: str, subject: str = "") -> None:
        """Print structured data to console."""
        try:
            print(structured_data, flush=True)
        except Exception as e:
            logger.error("Failed to publish to console", handler="console", error=str(e))
            raise

    @property
    def is_connected(self) -> bool:
        """Console is always available."""
        return True
