# pyright: strict
"""Console output for pipeline events using Rich console."""

from rich.console import Console

from models.events import TextProductEventData
from pipeline import Output, PipelineEvent


class ConsoleOutput(Output):
    """Output that prints JSON formatted weather wire events to console using Rich."""

    def __init__(self, output_id: str = "console", *, pretty: bool = True) -> None:
        """Initialize the console output."""
        super().__init__(output_id)
        self.console = Console()
        self.pretty = pretty

    async def send(self, event: PipelineEvent) -> None:
        """Send the event to console as JSON."""
        if isinstance(event, TextProductEventData):
            json = event.product.model_dump_json(indent=2 if self.pretty else None, exclude_defaults=True, by_alias=True)
            self.console.print(json)
