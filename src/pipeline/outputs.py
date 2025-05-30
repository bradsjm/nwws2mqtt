# pyright: strict
"""Pipeline outputs for event processing."""

from __future__ import annotations

import asyncio
import contextlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

# Optional dependencies
try:
    import aiofiles
except ImportError:
    aiofiles = None

try:
    import aiohttp
except ImportError:
    aiohttp = None

from .errors import OutputError

if TYPE_CHECKING:
    from collections.abc import Callable

    from aiohttp import ClientSession

    from .types import PipelineEvent


class Output(ABC):
    """Base class for pipeline outputs."""

    def __init__(self, output_id: str) -> None:
        """Initialize the output with an identifier."""
        self.output_id = output_id
        self._is_started = False

    @abstractmethod
    async def send(self, event: PipelineEvent) -> None:
        """Send the event to the output destination.

        Args:
            event: The pipeline event to send.

        Raises:
            OutputError: If an error occurs during output.

        """

    async def start(self) -> None:
        """Start the output (e.g., connect to external services)."""
        self._is_started = True
        logger.debug("Output started", output_id=self.output_id)

    async def stop(self) -> None:
        """Stop the output (e.g., disconnect from external services)."""
        self._is_started = False
        logger.debug("Output stopped", output_id=self.output_id)

    @property
    def is_started(self) -> bool:
        """Check if the output is started."""
        return self._is_started

    async def __call__(self, event: PipelineEvent) -> None:
        """Make the output callable."""
        if not self._is_started:
            logger.warning(
                "Output not started, skipping event",
                output_id=self.output_id,
                event_id=event.metadata.event_id,
            )
            return

        try:
            await self.send(event)
            logger.debug(
                "Output sent successfully",
                output_id=self.output_id,
                event_id=event.metadata.event_id,
                event_type=type(event).__name__,
            )
        except Exception as e:
            logger.error(
                "Output error",
                output_id=self.output_id,
                event_id=event.metadata.event_id,
                error=str(e),
            )
            msg = f"Output {self.output_id} failed: {e}"
            raise OutputError(msg, self.output_id) from e


class LogOutput(Output):
    """Output that logs events to the logger."""

    def __init__(self, output_id: str = "log", log_level: str = "info") -> None:
        """Initialize the log output.

        Args:
            output_id: Unique identifier for this output.
            log_level: Log level to use (debug, info, warning, error).

        """
        super().__init__(output_id)
        self.log_level = log_level.lower()

    async def send(self, event: PipelineEvent) -> None:
        """Log the event."""
        log_data = {
            "output_id": self.output_id,
            "event_id": event.metadata.event_id,
            "event_type": type(event).__name__,
            "stage": event.metadata.stage.value,
            "source": event.metadata.source,
        }

        if self.log_level == "debug":
            logger.debug("Pipeline event", **log_data)
        elif self.log_level == "warning":
            logger.warning("Pipeline event", **log_data)
        elif self.log_level == "error":
            logger.error("Pipeline event", **log_data)
        else:  # info
            logger.info("Pipeline event", **log_data)


class BatchOutput(Output):
    """Output that batches events and sends them in groups."""

    def __init__(
        self,
        output_id: str,
        target_output: Output,
        batch_size: int = 10,
        batch_timeout_seconds: float = 5.0,
    ) -> None:
        """Initialize the batch output.

        Args:
            output_id: Unique identifier for this output.
            target_output: The output to send batched events to.
            batch_size: Number of events to batch before sending.
            batch_timeout_seconds: Maximum time to wait before sending partial batch.

        """
        super().__init__(output_id)
        self.target_output = target_output
        self.batch_size = batch_size
        self.batch_timeout_seconds = batch_timeout_seconds
        self._batch: list[PipelineEvent] = []
        self._batch_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the batch output and target output."""
        await super().start()
        await self.target_output.start()

    async def stop(self) -> None:
        """Stop the batch output and flush remaining events."""
        if self._batch_task:
            self._batch_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._batch_task

        # Flush remaining events
        if self._batch:
            await self._flush_batch()

        await self.target_output.stop()
        await super().stop()

    async def send(self, event: PipelineEvent) -> None:
        """Add event to batch and send if batch is full."""
        self._batch.append(event)

        if len(self._batch) >= self.batch_size:
            await self._flush_batch()
        elif self._batch_task is None or self._batch_task.done():
            # Start timeout task for partial batch
            self._batch_task = asyncio.create_task(self._batch_timeout())

    async def _flush_batch(self) -> None:
        """Send all events in the current batch."""
        if not self._batch:
            return

        batch_to_send = self._batch.copy()
        self._batch.clear()

        # Cancel timeout task if running
        if self._batch_task and not self._batch_task.done():
            self._batch_task.cancel()

        # Send all events in batch
        for event in batch_to_send:
            await self.target_output.send(event)

        logger.debug(
            "Batch flushed",
            output_id=self.output_id,
            batch_size=len(batch_to_send),
        )

    async def _batch_timeout(self) -> None:
        """Flush batch after timeout period."""
        try:
            await asyncio.sleep(self.batch_timeout_seconds)
            if self._batch:  # Only flush if we still have events
                await self._flush_batch()
        except asyncio.CancelledError:
            pass


class ConditionalOutput(Output):
    """Output that sends events to different outputs based on conditions."""

    def __init__(
        self,
        output_id: str,
        conditions: list[tuple[Callable[[PipelineEvent], bool], Output]],
        default_output: Output | None = None,
    ) -> None:
        """Initialize the conditional output.

        Args:
            output_id: Unique identifier for this output.
            conditions: List of (condition_func, output) tuples.
            default_output: Output to use if no conditions match.

        """
        super().__init__(output_id)
        self.conditions = conditions
        self.default_output = default_output

    async def start(self) -> None:
        """Start all outputs."""
        await super().start()
        for _, output in self.conditions:
            await output.start()
        if self.default_output:
            await self.default_output.start()

    async def stop(self) -> None:
        """Stop all outputs."""
        for _, output in self.conditions:
            await output.stop()
        if self.default_output:
            await self.default_output.stop()
        await super().stop()

    async def send(self, event: PipelineEvent) -> None:
        """Send event to the first matching output."""
        for condition, output in self.conditions:
            if condition(event):
                await output.send(event)
                return

        if self.default_output:
            await self.default_output.send(event)
        else:
            logger.debug(
                "No matching condition for event",
                output_id=self.output_id,
                event_id=event.metadata.event_id,
            )


class MulticastOutput(Output):
    """Output that sends events to multiple outputs simultaneously."""

    def __init__(self, output_id: str, outputs: list[Output], *, fail_fast: bool = False) -> None:
        """Initialize the multicast output.

        Args:
            output_id: Unique identifier for this output.
            outputs: List of outputs to send events to.
            fail_fast: If True, stop on first error; if False, continue with other outputs.

        """
        super().__init__(output_id)
        self.outputs = outputs
        self.fail_fast = fail_fast

    async def start(self) -> None:
        """Start all outputs."""
        await super().start()
        for output in self.outputs:
            await output.start()

    async def stop(self) -> None:
        """Stop all outputs."""
        for output in self.outputs:
            await output.stop()
        await super().stop()

    async def send(self, event: PipelineEvent) -> None:
        """Send event to all outputs."""
        errors: list[Exception] = []

        for output in self.outputs:
            try:
                await output.send(event)
            except Exception as e:
                if self.fail_fast:
                    raise
                errors.append(e)
                logger.warning(
                    "Output failed in multicast",
                    output_id=self.output_id,
                    failed_output_id=output.output_id,
                    error=str(e),
                )

        if errors and not self.fail_fast:
            logger.warning(
                "Some outputs failed in multicast",
                output_id=self.output_id,
                error_count=len(errors),
                total_outputs=len(self.outputs),
            )


class FileOutput(Output):
    """Output that writes events to a file."""

    def __init__(
        self,
        output_id: str,
        filename: str | Path,
        mode: str = "a",
        encoding: str = "utf-8",
        formatter: Callable[[PipelineEvent], str] | None = None,
    ) -> None:
        """Initialize the file output.

        Args:
            output_id: Unique identifier for this output.
            filename: Path to the output file.
            mode: File opening mode (default: append).
            encoding: File encoding (default: utf-8).
            formatter: Function to format events as strings.

        """
        super().__init__(output_id)
        self.filename = Path(filename)
        self.mode = mode
        self.encoding = encoding
        self.formatter = formatter or self._default_formatter

    def _default_formatter(self, event: PipelineEvent) -> str:
        """Format event as string."""
        return f"{event.metadata.timestamp}: {type(event).__name__}({event.metadata.event_id})\n"

    async def start(self) -> None:
        """Start the file output and ensure directory exists."""
        await super().start()
        # Ensure parent directory exists
        self.filename.parent.mkdir(parents=True, exist_ok=True)

    async def send(self, event: PipelineEvent) -> None:
        """Write the event to the file."""
        if aiofiles is None:
            error_msg = f"FileOutput {self.output_id} requires aiofiles package. Install with: pip install aiofiles"
            raise OutputError(
                error_msg,
                self.output_id,
            )

        try:
            formatted_event = self.formatter(event)
            async with aiofiles.open(  # type: ignore[misc]
                str(self.filename),
                mode=self.mode,  # type: ignore[arg-type]
                encoding=self.encoding,
            ) as f:  # type: ignore[misc]
                await f.write(formatted_event)  # type: ignore[misc]
        except (OSError, ValueError) as e:
            logger.error(
                "Failed to write to file",
                output_id=self.output_id,
                filename=str(self.filename),
                error=str(e),
            )
            error_msg = f"File output {self.output_id} failed: {e}"
            raise OutputError(error_msg, self.output_id) from e


class HttpOutput(Output):
    """Output that sends events to HTTP endpoints."""

    def __init__(
        self,
        output_id: str,
        url: str,
        method: str = "POST",
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        formatter: Callable[[PipelineEvent], dict[str, Any]] | None = None,
    ) -> None:
        """Initialize the HTTP output.

        Args:
            output_id: Unique identifier for this output.
            url: HTTP endpoint URL.
            method: HTTP method (GET, POST, PUT, etc.).
            headers: HTTP headers to include.
            timeout: Request timeout in seconds.
            formatter: Function to format events as JSON-serializable dicts.

        """
        super().__init__(output_id)
        self.url = url
        self.method = method.upper()
        self.headers = headers or {}
        self.timeout = timeout
        self.formatter = formatter or self._default_formatter
        self._session: ClientSession | None = None

    def _default_formatter(self, event: PipelineEvent) -> dict[str, Any]:
        """Format event as dictionary."""
        return {
            "event_id": event.metadata.event_id,
            "timestamp": event.metadata.timestamp,
            "source": event.metadata.source,
            "stage": event.metadata.stage.value,
            "event_type": type(event).__name__,
            "trace_id": event.metadata.trace_id,
            "custom": event.metadata.custom,
        }

    async def start(self) -> None:
        """Start the HTTP output and create session."""
        if aiohttp is None:
            error_msg = f"HttpOutput {self.output_id} requires aiohttp package. Install with: pip install aiohttp"
            raise OutputError(
                error_msg,
                self.output_id,
            )

        await super().start()
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)

    async def stop(self) -> None:
        """Stop the HTTP output and close session."""
        if self._session:
            await self._session.close()
            self._session = None
        await super().stop()

    async def send(self, event: PipelineEvent) -> None:
        """Send the event to the HTTP endpoint."""
        if not self._session:
            error_msg = f"HTTP output {self.output_id} not started"
            raise OutputError(error_msg, self.output_id)

        try:
            data = self.formatter(event)

            async with self._session.request(
                self.method,
                self.url,
                json=data,
                headers=self.headers,
            ) as response:
                response.raise_for_status()

                logger.debug(
                    "HTTP request successful",
                    output_id=self.output_id,
                    url=self.url,
                    status=response.status,
                    event_id=event.metadata.event_id,
                )

        except Exception as e:
            logger.error(
                "HTTP request failed",
                output_id=self.output_id,
                url=self.url,
                error=str(e),
                event_id=event.metadata.event_id,
            )
            error_msg = f"HTTP output {self.output_id} failed: {e}"
            raise OutputError(error_msg, self.output_id) from e


class FunctionOutput(Output):
    """Output that processes events using a custom function."""

    def __init__(
        self,
        output_id: str,
        output_function: Callable[[PipelineEvent], Any],
    ) -> None:
        """Initialize the function output.

        Args:
            output_id: Unique identifier for this output.
            output_function: Function to process events (can be sync or async).

        """
        super().__init__(output_id)
        self.output_function = output_function
        self._is_async = asyncio.iscoroutinefunction(output_function)

    async def send(self, event: PipelineEvent) -> None:
        """Process the event using the custom function."""
        try:
            if self._is_async:
                await self.output_function(event)  # type: ignore[misc]
            else:
                self.output_function(event)
        except Exception as e:
            logger.error(
                "Function output error",
                output_id=self.output_id,
                event_id=event.metadata.event_id,
                error=str(e),
            )
            error_msg = f"Function output {self.output_id} failed: {e}"
            raise OutputError(error_msg, self.output_id) from e


@dataclass
class OutputConfig:
    """Configuration for an output."""

    output_type: str
    """Type of output to create."""

    output_id: str
    """Unique identifier for the output."""

    config: dict[str, Any] = field(default_factory=dict[str, Any])
    """Output-specific configuration."""


class OutputRegistry:
    """Registry for managing and creating outputs."""

    def __init__(self) -> None:
        """Initialize the output registry."""
        self._output_factories: dict[str, Callable[..., Output]] = {}
        self._register_builtin_outputs()

    def register(self, output_type: str, factory: Callable[..., Output]) -> None:
        """Register an output factory.

        Args:
            output_type: String identifier for the output type.
            factory: Factory function that creates the output.

        """
        self._output_factories[output_type] = factory

    def create(self, config: OutputConfig) -> Output:
        """Create an output from configuration.

        Args:
            config: Output configuration.

        Returns:
            Configured output instance.

        Raises:
            OutputError: If the output type is not registered or creation fails.

        """
        if config.output_type not in self._output_factories:
            msg = f"Unknown output type: {config.output_type}"
            raise OutputError(
                msg,
                config.output_id,
            )

        try:
            factory = self._output_factories[config.output_type]
            return factory(config.output_id, **config.config)
        except Exception as e:
            msg = f"Failed to create output {config.output_id}: {e}"
            raise OutputError(
                msg,
                config.output_id,
            ) from e

    def get_available_types(self) -> list[str]:
        """Get a list of available output types."""
        return list(self._output_factories.keys())

    def _register_builtin_outputs(self) -> None:
        """Register built-in output types."""
        self.register("log", LogOutput)
        self.register("file", FileOutput)
        self.register("http", HttpOutput)
        self.register("function", FunctionOutput)
        self.register("batch", BatchOutput)
        self.register("conditional", ConditionalOutput)
        self.register("multicast", MulticastOutput)


# Global output registry instance
output_registry = OutputRegistry()
