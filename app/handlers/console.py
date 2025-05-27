"""Console output handler for NWWS-OI data."""

from loguru import logger

from .base import OutputHandler


class ConsoleOutputHandler(OutputHandler):
    """Autonomous output handler that prints to console."""

    async def _start_handler(self) -> None:
        """Start console handler (no-op)."""
        logger.info("Autonomous console output handler starting")

    async def _stop_handler(self) -> None:
        """Stop console handler (no-op)."""
        logger.info("Autonomous console output handler stopping")

    async def publish(self, source: str, afos: str, product_id: str, structured_data: str, subject: str = "") -> None:
        """Print structured data to console."""
        try:
            # Use logger instead of print to be consistent with the rest of the application
            logger.info(
                "Product published", handler="console", product_id=product_id, source=source, afos=afos, data=structured_data
            )
        except Exception as e:
            logger.error("Failed to publish to console", handler="console", error=str(e))
            raise

    @property
    def is_connected(self) -> bool:
        """Console is always available."""
        return True
