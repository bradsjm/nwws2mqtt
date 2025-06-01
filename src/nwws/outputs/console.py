# pyright: strict
"""Console output for pipeline events using Rich console."""

from typing import Any

from loguru import logger
from rich.console import Console

from nwws.models.events.noaa_port_event_data import NoaaPortEventData
from nwws.pipeline import Output, PipelineEvent


class ConsoleOutput(Output):
    """Output that prints JSON formatted weather wire events to console using Rich."""

    def __init__(self, output_id: str = "console", *, pretty: bool = True) -> None:
        """Initialize the console output."""
        super().__init__(output_id)
        self.console = Console()
        self.pretty = pretty

        logger.info("Console Output initialized", output_id=self.output_id)

    async def send(self, event: PipelineEvent) -> None:
        """Send the event to console."""
        if not isinstance(event, NoaaPortEventData):
            logger.debug(
                "Skipping non-text product event",
                output_id=self.output_id,
                event_type=type(event).__name__,
            )
            return

        self.console.print(str(event))

    def get_output_metadata(self, event: PipelineEvent) -> dict[str, Any]:
        """Get metadata about the console output operation."""
        metadata = super().get_output_metadata(event)

        # Add console-specific metadata
        metadata[f"{self.output_id}_pretty_print"] = self.pretty
        metadata[f"{self.output_id}_console_output"] = True

        if isinstance(event, NoaaPortEventData):
            metadata[f"{self.output_id}_event_processed"] = True
            metadata[f"{self.output_id}_content_length"] = len(str(event))
        else:
            metadata[f"{self.output_id}_event_processed"] = False
            metadata[f"{self.output_id}_skip_reason"] = "not_noaa_port_event"

        return metadata
