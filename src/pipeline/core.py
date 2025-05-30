# pyright: strict
"""Core pipeline engine and management."""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING, Any, Self

from loguru import logger

from .errors import ErrorHandler, PipelineError
from .types import PipelineEvent, PipelineStage

if TYPE_CHECKING:
    from .config import PipelineManagerConfig
    from .filters import Filter
    from .outputs import Output
    from .stats import StatsCollector
    from .transformers import Transformer


class Pipeline:
    """Core pipeline for processing events through filters, transformers, and outputs."""

    def __init__(  # noqa: PLR0913
        self,
        pipeline_id: str,
        filters: list[Filter] | None = None,
        transformer: Transformer | None = None,
        outputs: list[Output] | None = None,
        stats_collector: StatsCollector | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        """Initialize the pipeline with components.

        Args:
            pipeline_id: Unique identifier for this pipeline.
            filters: List of filters to apply to events.
            transformer: Transformer to convert events.
            outputs: List of outputs to send events to.
            stats_collector: Statistics collector for metrics.
            error_handler: Error handler for pipeline errors.

        """
        self.pipeline_id = pipeline_id
        self.filters = filters or []
        self.transformer = transformer
        self.outputs = outputs or []
        self.stats_collector = stats_collector
        self.error_handler = error_handler or ErrorHandler()
        self._is_started = False

    async def start(self) -> None:
        """Start the pipeline and all outputs."""
        if self._is_started:
            return

        logger.info("Starting pipeline", pipeline_id=self.pipeline_id)

        # Start all outputs
        for output in self.outputs:
            try:
                await output.start()
            except (OSError, ValueError, RuntimeError) as e:
                logger.error(
                    "Failed to start output",
                    pipeline_id=self.pipeline_id,
                    output_id=output.output_id,
                    error=str(e),
                )
                error_msg = f"Failed to start output {output.output_id}: {e}"
                raise PipelineError(error_msg) from e

        self._is_started = True
        logger.info("Pipeline started successfully", pipeline_id=self.pipeline_id)

    async def stop(self) -> None:
        """Stop the pipeline and all outputs."""
        if not self._is_started:
            return

        logger.info("Stopping pipeline", pipeline_id=self.pipeline_id)

        # Stop all outputs
        for output in self.outputs:
            try:
                await output.stop()
            except (OSError, ValueError, RuntimeError) as e:
                logger.warning(
                    "Error stopping output",
                    pipeline_id=self.pipeline_id,
                    output_id=output.output_id,
                    error=str(e),
                )

        self._is_started = False
        logger.info("Pipeline stopped", pipeline_id=self.pipeline_id)

    async def process(self, event: PipelineEvent) -> bool:
        """Process an event through the pipeline.

        Args:
            event: The event to process.

        Returns:
            True if the event was processed successfully, False if filtered out.

        """
        if not self._is_started:
            logger.warning(
                "Pipeline not started, skipping event",
                pipeline_id=self.pipeline_id,
                event_id=event.metadata.event_id,
            )
            return False

        start_time = time.time()

        try:
            # Apply filters
            filtered_event = await self._apply_filters(event)
            if filtered_event is None:
                return False  # Event was filtered out

            # Apply transformation
            transformed_event = await self._apply_transformation(filtered_event)

            # Send to outputs
            await self._send_to_outputs(transformed_event)

            # Record success stats
            if self.stats_collector:
                duration_ms = (time.time() - start_time) * 1000
                self.stats_collector.record_processing_time(
                    event.metadata.event_id,
                    PipelineStage.OUTPUT,
                    self.pipeline_id,
                    duration_ms,
                    success=True,
                )
                self.stats_collector.record_throughput(
                    event.metadata.event_id,
                    PipelineStage.OUTPUT,
                    self.pipeline_id,
                )

            logger.debug(
                "Event processed successfully",
                pipeline_id=self.pipeline_id,
                event_id=event.metadata.event_id,
                duration_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            # Handle and record error
            duration_ms = (time.time() - start_time) * 1000
            self.error_handler.handle_error(
                event.metadata.event_id,
                PipelineStage.OUTPUT,
                self.pipeline_id,
                e,
                event,
            )

            if self.stats_collector:
                self.stats_collector.record_processing_time(
                    event.metadata.event_id,
                    PipelineStage.OUTPUT,
                    self.pipeline_id,
                    duration_ms,
                    success=False,
                )

            logger.error(
                "Pipeline processing error",
                pipeline_id=self.pipeline_id,
                event_id=event.metadata.event_id,
                error=str(e),
                duration_ms=duration_ms,
            )

            # Re-raise for upstream handling
            raise
        else:
            return True

    async def _apply_filters(self, event: PipelineEvent) -> PipelineEvent | None:
        """Apply all filters to the event."""
        current_event = event.with_stage(PipelineStage.FILTER, self.pipeline_id)

        for filter_instance in self.filters:
            start_time = time.time()

            try:
                if not filter_instance(current_event):
                    # Event was filtered out
                    if self.stats_collector:
                        duration_ms = (time.time() - start_time) * 1000
                        self.stats_collector.record_processing_time(
                            event.metadata.event_id,
                            PipelineStage.FILTER,
                            filter_instance.filter_id,
                            duration_ms,
                            success=True,
                        )

                    logger.debug(
                        "Event filtered out",
                        pipeline_id=self.pipeline_id,
                        filter_id=filter_instance.filter_id,
                        event_id=event.metadata.event_id,
                    )
                    return None

                # Record successful filter application
                if self.stats_collector:
                    duration_ms = (time.time() - start_time) * 1000
                    self.stats_collector.record_processing_time(
                        event.metadata.event_id,
                        PipelineStage.FILTER,
                        filter_instance.filter_id,
                        duration_ms,
                        success=True,
                    )

            except Exception as e:
                # Record filter error
                duration_ms = (time.time() - start_time) * 1000
                self.error_handler.handle_error(
                    event.metadata.event_id,
                    PipelineStage.FILTER,
                    filter_instance.filter_id,
                    e,
                    current_event,
                )

                if self.stats_collector:
                    self.stats_collector.record_processing_time(
                        event.metadata.event_id,
                        PipelineStage.FILTER,
                        filter_instance.filter_id,
                        duration_ms,
                        success=False,
                    )

                # Re-raise filter errors
                raise

        return current_event

    async def _apply_transformation(self, event: PipelineEvent) -> PipelineEvent:
        """Apply transformation to the event."""
        if not self.transformer:
            return event

        current_event = event.with_stage(PipelineStage.TRANSFORM, self.pipeline_id)
        start_time = time.time()

        try:
            transformed_event = self.transformer(current_event)

            # Record successful transformation
            if self.stats_collector:
                duration_ms = (time.time() - start_time) * 1000
                self.stats_collector.record_processing_time(
                    event.metadata.event_id,
                    PipelineStage.TRANSFORM,
                    self.transformer.transformer_id,
                    duration_ms,
                    success=True,
                )

        except Exception as e:
            # Record transformation error
            duration_ms = (time.time() - start_time) * 1000
            self.error_handler.handle_error(
                event.metadata.event_id,
                PipelineStage.TRANSFORM,
                self.transformer.transformer_id,
                e,
                current_event,
            )

            if self.stats_collector:
                self.stats_collector.record_processing_time(
                    event.metadata.event_id,
                    PipelineStage.TRANSFORM,
                    self.transformer.transformer_id,
                    duration_ms,
                    success=False,
                )

            # Re-raise transformation errors
            raise

        return transformed_event

    async def _send_to_outputs(self, event: PipelineEvent) -> None:
        """Send event to all outputs."""
        output_event = event.with_stage(PipelineStage.OUTPUT, self.pipeline_id)

        # Send to all outputs concurrently
        tasks: list[asyncio.Task[None]] = []
        for output in self.outputs:
            task = asyncio.create_task(self._send_to_single_output(output, output_event))
            tasks.append(task)

        if tasks:
            # Wait for all outputs to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for errors
            errors = [result for result in results if isinstance(result, Exception)]
            if errors:
                logger.warning(
                    "Some outputs failed",
                    pipeline_id=self.pipeline_id,
                    event_id=event.metadata.event_id,
                    error_count=len(errors),
                    total_outputs=len(self.outputs),
                )
                # Re-raise the first error
                raise errors[0]

    async def _send_to_single_output(self, output: Output, event: PipelineEvent) -> None:
        """Send event to a single output with error handling."""
        start_time = time.time()

        try:
            await output(event)

            # Record successful output
            if self.stats_collector:
                duration_ms = (time.time() - start_time) * 1000
                self.stats_collector.record_processing_time(
                    event.metadata.event_id,
                    PipelineStage.OUTPUT,
                    output.output_id,
                    duration_ms,
                    success=True,
                )

        except Exception as e:
            # Record output error
            duration_ms = (time.time() - start_time) * 1000
            self.error_handler.handle_error(
                event.metadata.event_id,
                PipelineStage.OUTPUT,
                output.output_id,
                e,
                event,
            )

            if self.stats_collector:
                self.stats_collector.record_processing_time(
                    event.metadata.event_id,
                    PipelineStage.OUTPUT,
                    output.output_id,
                    duration_ms,
                    success=False,
                )

            # Re-raise output errors
            raise

    @property
    def is_started(self) -> bool:
        """Check if the pipeline is started."""
        return self._is_started

    def get_stats_summary(self) -> dict[str, Any] | None:
        """Get a summary of pipeline statistics."""
        return self.stats_collector.stats.get_summary() if self.stats_collector else None

    def get_error_summary(self) -> dict[str, Any]:
        """Get a summary of pipeline errors."""
        return self.error_handler.get_error_summary()


class PipelineManager:
    """Manages multiple pipelines and event routing."""

    def __init__(self, config: PipelineManagerConfig | None = None) -> None:
        """Initialize the pipeline manager.

        Args:
            config: Optional configuration for the pipeline manager.

        """
        from .config import PipelineManagerConfig

        self.config = config or PipelineManagerConfig()
        self._pipelines: dict[str, Pipeline] = {}
        self._event_queue: asyncio.Queue[tuple[str | None, PipelineEvent]] = asyncio.Queue(
            maxsize=self.config.max_queue_size,
        )
        self._processing_task: asyncio.Task[None] | None = None
        self._is_running = False

    async def add_pipeline(self, pipeline: Pipeline) -> None:
        """Add a pipeline to the manager.

        Args:
            pipeline: The pipeline to add.

        """
        self._pipelines[pipeline.pipeline_id] = pipeline

        # If manager is running, start the pipeline immediately
        if self._is_running:
            await pipeline.start()

        logger.info(
            "Pipeline added to manager",
            pipeline_id=pipeline.pipeline_id,
            total_pipelines=len(self._pipelines),
        )

    def remove_pipeline(self, pipeline_id: str) -> Pipeline | None:
        """Remove a pipeline from the manager.

        Args:
            pipeline_id: ID of the pipeline to remove.

        Returns:
            The removed pipeline, or None if not found.

        """
        pipeline = self._pipelines.pop(pipeline_id, None)
        if pipeline:
            logger.info(
                "Pipeline removed from manager",
                pipeline_id=pipeline_id,
                total_pipelines=len(self._pipelines),
            )
        return pipeline

    def get_pipeline(self, pipeline_id: str) -> Pipeline | None:
        """Get a pipeline by ID.

        Args:
            pipeline_id: ID of the pipeline to retrieve.

        Returns:
            The pipeline, or None if not found.

        """
        return self._pipelines.get(pipeline_id)

    def get_all_pipelines(self) -> list[Pipeline]:
        """Get all registered pipelines."""
        return list(self._pipelines.values())

    async def start(self) -> None:
        """Start the pipeline manager and all pipelines."""
        if self._is_running:
            return

        logger.info("Starting pipeline manager", pipeline_count=len(self._pipelines))

        # Start all pipelines
        for pipeline in self._pipelines.values():
            await pipeline.start()

        # Start event processing task
        self._is_running = True
        self._processing_task = asyncio.create_task(self._process_events())

        logger.info("Pipeline manager started successfully")

    async def stop(self) -> None:
        """Stop the pipeline manager and all pipelines."""
        if not self._is_running:
            return

        logger.info("Stopping pipeline manager")
        self._is_running = False

        # Stop event processing task
        if self._processing_task:
            self._processing_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._processing_task

        # Stop all pipelines
        for pipeline in self._pipelines.values():
            await pipeline.stop()

        logger.info("Pipeline manager stopped")

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context manager and ensure cleanup."""
        await self.stop()

    def __del__(self) -> None:
        """Clean up resources when the manager is garbage collected."""
        if self._is_running and self._processing_task and not self._processing_task.done():
            logger.warning(
                "PipelineManager was garbage collected while still running. "
                "Call stop() or use as async context manager to avoid resource leaks.",
            )
            # Try to cancel the task, but ignore errors if event loop is closed
            with contextlib.suppress(RuntimeError):
                self._processing_task.cancel()

    async def submit_event(self, pipeline_id: str, event: PipelineEvent) -> None:
        """Submit an event to a specific pipeline for processing.

        Args:
            pipeline_id: ID of the pipeline to process the event.
            event: The event to process.

        """
        if not self._is_running:
            logger.warning(
                "Pipeline manager not running, dropping event",
                event_id=event.metadata.event_id,
                pipeline_id=pipeline_id,
            )
            return

        try:
            await asyncio.wait_for(
                self._event_queue.put((pipeline_id, event)),
                timeout=self.config.processing_timeout_seconds,
            )
            logger.debug(
                "Event submitted for processing",
                event_id=event.metadata.event_id,
                pipeline_id=pipeline_id,
            )
        except TimeoutError:
            logger.error(
                "Event submission timeout",
                event_id=event.metadata.event_id,
                pipeline_id=pipeline_id,
                timeout=self.config.processing_timeout_seconds,
            )

    async def submit_event_to_all(self, event: PipelineEvent) -> None:
        """Submit an event to all pipelines for processing.

        Args:
            event: The event to process.

        """
        if not self._is_running:
            logger.warning(
                "Pipeline manager not running, dropping event",
                event_id=event.metadata.event_id,
            )
            return

        try:
            await asyncio.wait_for(
                self._event_queue.put((None, event)),
                timeout=self.config.processing_timeout_seconds,
            )
            logger.debug("Event submitted to all pipelines", event_id=event.metadata.event_id)
        except TimeoutError:
            logger.error(
                "Event submission timeout",
                event_id=event.metadata.event_id,
                timeout=self.config.processing_timeout_seconds,
            )

    async def _process_events(self) -> None:  # noqa: C901
        """Process events from the queue through specified or all pipelines."""
        while self._is_running:
            try:
                # Wait for next event with timeout
                pipeline_id, event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)

                if pipeline_id is None:
                    # Process event through all pipelines concurrently
                    tasks = [
                        asyncio.create_task(pipeline.process(event)) for pipeline in self._pipelines.values() if pipeline.is_started
                    ]

                    if tasks:
                        # Wait for all pipelines to process the event
                        results = await asyncio.gather(*tasks, return_exceptions=True)

                        # Log any errors
                        errors = [result for result in results if isinstance(result, Exception)]
                        if errors:
                            logger.warning(
                                "Some pipelines failed to process event",
                                event_id=event.metadata.event_id,
                                error_count=len(errors),
                                total_pipelines=len(tasks),
                            )
                else:
                    # Process event through specific pipeline
                    pipeline = self._pipelines.get(pipeline_id)
                    if pipeline and pipeline.is_started:
                        try:
                            await asyncio.wait_for(
                                pipeline.process(event),
                                timeout=self.config.processing_timeout_seconds,
                            )
                        except TimeoutError:
                            logger.error(
                                "Pipeline processing timeout",
                                pipeline_id=pipeline_id,
                                event_id=event.metadata.event_id,
                                timeout=self.config.processing_timeout_seconds,
                            )
                        except (OSError, ValueError, RuntimeError, PipelineError) as e:
                            logger.error(
                                "Pipeline processing error",
                                pipeline_id=pipeline_id,
                                event_id=event.metadata.event_id,
                                error=str(e),
                            )
                    else:
                        logger.warning(
                            "Pipeline not found or not started",
                            pipeline_id=pipeline_id,
                            event_id=event.metadata.event_id,
                        )

                # Mark task as done
                self._event_queue.task_done()

            except TimeoutError:
                # No events in queue, continue waiting
                continue
            except asyncio.CancelledError:
                # Manager is shutting down
                break
            except (OSError, ValueError, RuntimeError, PipelineError) as e:
                logger.error("Error in event processing loop", error=str(e))

    @property
    def is_running(self) -> bool:
        """Check if the pipeline manager is running."""
        return self._is_running

    @property
    def queue_size(self) -> int:
        """Get the current size of the event queue."""
        return self._event_queue.qsize()

    def get_manager_stats(self) -> dict[str, Any]:
        """Get manager-level statistics."""
        return {
            "is_running": self._is_running,
            "pipeline_count": len(self._pipelines),
            "queue_size": self.queue_size,
            "pipelines": {
                pipeline_id: {
                    "is_started": pipeline.is_started,
                    "filter_count": len(pipeline.filters),
                    "output_count": len(pipeline.outputs),
                    "has_transformer": pipeline.transformer is not None,
                    "stats": pipeline.get_stats_summary(),
                    "errors": pipeline.get_error_summary(),
                }
                for pipeline_id, pipeline in self._pipelines.items()
            },
        }
