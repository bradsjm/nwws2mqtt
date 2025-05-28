"""Console output handler for NWWS-OI data."""

from loguru import logger
from rich.console import Console

from app.models.output_config import OutputConfig

from .base import OutputHandler


class ConsoleOutputHandler(OutputHandler):
    """output handler that prints to console."""

    def __init__(self, config: OutputConfig) -> None:
        """Initialize the console output handler.

        Args:
            config: Output configuration for the handler.

        """
        super().__init__(config)
        self.console = Console()

    async def _start_handler(self) -> None:
        """Start console handler (no-op)."""
        logger.info("console output handler starting")

    async def _stop_handler(self) -> None:
        """Stop console handler (no-op)."""
        logger.info("console output handler stopping")

    async def publish(
        self,
        source: str,
        afos: str,
        product_id: str,
        structured_data: str,
        subject: str = "",
    ) -> None:
        """Print structured data to console."""
        try:
            # TODO: change structured_data to a json object
            self.console.print(structured_data)
        except Exception as e:
            logger.error("Failed to publish to console", handler="console", error=str(e))
            raise

    @property
    def is_connected(self) -> bool:
        """Console is always available."""
        return True
