# pyright: strict
"""Console output for pipeline events using Rich console."""

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
