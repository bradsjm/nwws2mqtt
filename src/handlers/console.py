"""Console output handler for NWWS-OI data."""

from loguru import logger
from rich.console import Console

from app.models.output_config import OutputConfig
from app.models.product import TextProductModel
from app.utils.conversion import product_to_json

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
        text_product: TextProductModel,
        subject: str = "",
    ) -> None:
        """Print structured data to console."""
        try:
            json_data = product_to_json(text_product)
            self.console.print_json(json_data)
        except (TypeError, ValueError, OSError) as e:
            logger.error(
                "Failed to publish to console",
                source=source,
                afos=afos,
                product_id=product_id,
                subject=subject,
                handler="console",
                error=str(e),
            )

    @property
    def is_connected(self) -> bool:
        """Console is always available."""
        return True
