# pyright: strict
"""Core pipeline engine and management."""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING, Any, Self

from loguru import logger

from .errors import PipelineError, PipelineErrorHandler
from .types import PipelineEvent, PipelineStage

if TYPE_CHECKING:
    from .config import PipelineManagerConfig
    from .filters import Filter
    from .outputs import Output
    from .stats import PipelineStatsCollector
    from .transformers import Transformer


class Pipeline:
    """Core event processing pipeline with filters, transformers, and outputs.

    The Pipeline class represents a single processing pathway for events within the NWWS
    system. It orchestrates the sequential processing of events through configurable
    stages: filtering, transformation, and output delivery. Each pipeline operates
    independently with its own error handling, statistics collection, and lifecycle
    management.

    The pipeline implements a robust error handling strategy where failures at any stage
    are logged with comprehensive context, recorded in statistics, and propagated to
    allow upstream error handling decisions. All processing stages are instrumented
    with timing metrics and detailed logging for observability.

    Key responsibilities:
    - Event filtering through configurable filter chains
    - Event transformation using pluggable transformers
    - Concurrent delivery to multiple outputs with error isolation
    - Comprehensive error handling and recovery
    - Performance metrics collection and reporting
    - Lifecycle management with proper resource cleanup
    """

    def __init__(  # noqa: PLR0913
        self,
        pipeline_id: str,
        filters: list[Filter] | None = None,
        transformer: Transformer | None = None,
        outputs: list[Output] | None = None,
        stats_collector: PipelineStatsCollector | None = None,
        error_handler: PipelineErrorHandler | None = None,
    ) -> None:
        """Initialize the pipeline with processing components and configuration.

        Creates a new pipeline instance with the specified processing components.
        The pipeline starts in a stopped state and must be explicitly started before
        processing events. All components are validated and configured during
        initialization, but actual connections and resources are established during
        the start phase.

        Args:
            pipeline_id: Unique identifier for this pipeline instance used in logging
                and statistics. Must be unique within a PipelineManager context.
            filters: Optional list of filter instances to apply to incoming events.
                Filters are applied sequentially and any filter returning False will
                cause the event to be dropped from further processing.
            transformer: Optional transformer instance to convert events between types.
                If None, events pass through unchanged.
            outputs: Optional list of output instances for event delivery. Events are
                delivered to all outputs concurrently with individual error handling.
            stats_collector: Optional statistics collector for recording performance
                metrics, processing counts, and error rates.
            error_handler: Optional error handler for recording and managing pipeline
                errors. Defaults to basic PipelineErrorHandler if not provided.

        """
        self.pipeline_id = pipeline_id
        self.filters = filters or []
        self.transformer = transformer
        self.outputs = outputs or []
        self.stats_collector = stats_collector
        self.error_handler = error_handler or PipelineErrorHandler()
        self._is_started = False

    async def start(self) -> None:
        """Start the pipeline and initialize all output connections.

        Transitions the pipeline from stopped to started state by initializing all
        configured outputs. The startup process validates output configurations,
        establishes connections, and prepares resources for event processing.
        If any output fails to start, the entire pipeline startup fails with a
        detailed error message.

        The pipeline startup is idempotent - calling start() on an already started
        pipeline has no effect. All outputs are started sequentially to ensure
        proper error reporting and resource management.

        Raises:
            PipelineError: If any output fails to start, containing details about
                the specific output and underlying error. The pipeline remains in
                a stopped state if startup fails.

        """
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
        """Stop the pipeline and cleanup all output connections.

        Transitions the pipeline from started to stopped state by gracefully shutting
        down all configured outputs. The shutdown process attempts to stop all outputs
        even if some fail, logging warnings for any errors encountered but not raising
        exceptions to ensure complete cleanup.

        The pipeline stop is idempotent - calling stop() on an already stopped
        pipeline has no effect. After stopping, the pipeline will reject new events
        until restarted.

        Output shutdown errors are logged as warnings rather than errors since the
        pipeline is transitioning to a stopped state where failures are expected
        to be recoverable through restart.
        """
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
        """Process an event through the complete pipeline workflow.

        Orchestrates the processing of a single event through all configured pipeline
        stages: filtering, transformation, and output delivery. The method implements
        comprehensive error handling, performance monitoring, and detailed logging
        throughout the processing lifecycle.

        The processing workflow:
        1. Validates pipeline is in started state
        2. Applies all configured filters sequentially
        3. Applies transformation if configured
        4. Delivers to all outputs concurrently
        5. Records performance metrics and success statistics
        6. Handles errors with detailed context and propagation

        Performance metrics are collected for the entire processing duration as well
        as individual stage timings. All errors are logged with comprehensive context
        including event metadata, processing stage, and timing information.

        Args:
            event: The pipeline event to process containing the payload and metadata
                for tracking, tracing, and error handling.

        Returns:
            True if the event was successfully processed through all stages and
            delivered to all outputs. False if the event was filtered out during
            the filtering stage.

        Raises:
            Exception: Any exception encountered during processing is logged with
                comprehensive context and re-raised for upstream handling. This
                includes filter errors, transformation errors, and output errors.

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
                processing_duration_seconds = time.time() - start_time
                event_type = type(transformed_event).__name__
                source = event.metadata.source
                age_seconds = event.metadata.age_seconds

                self.stats_collector.record_event_processed(
                    processing_duration_seconds=processing_duration_seconds,
                    event_type=event_type,
                    source=source,
                    event_age_seconds=age_seconds,
                )

            # Log successful processing with journey summary
            total_duration_ms = (time.time() - start_time) * 1000

            logger.info(
                "Event processed successfully through pipeline",
                pipeline_id=self.pipeline_id,
                event_id=event.metadata.event_id,
                trace_id=event.metadata.trace_id,
                total_duration_ms=total_duration_ms,
                event_age_seconds=event.metadata.age_seconds,
                final_event_type=type(transformed_event).__name__,
                filters_count=len(self.filters),
                outputs_count=len(self.outputs),
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
                self.stats_collector.record_stage_error(
                    stage="pipeline",
                    stage_id=self.pipeline_id,
                    error_type=type(e).__name__,
                )

            logger.error(
                "Pipeline processing failed",
                pipeline_id=self.pipeline_id,
                event_id=event.metadata.event_id,
                trace_id=event.metadata.trace_id,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=duration_ms,
                event_age_seconds=event.metadata.age_seconds,
                event_type=type(event).__name__,
                stage=event.metadata.stage.value,
                source=event.metadata.source,
            )

            # Re-raise for upstream handling
            raise
        else:
            return True

    def _extract_journey_info(self, metadata: Any) -> dict[str, Any]:
        """Extract processing journey information from event metadata for logging.

        Analyzes event metadata to extract comprehensive journey information that
        tracks the event's path through various processing components. This includes
        applied transformations, filter decisions, component processing times, and
        error contexts that provide valuable debugging and monitoring information.

        The extracted journey information is used for detailed logging and debugging
        to understand how events flow through the system and where potential issues
        may occur. This method specifically looks for standardized metadata patterns
        used by pipeline components to record their processing activities.

        Args:
            metadata: Event metadata object containing custom fields with processing
                information from filters, transformers, and outputs.

        Returns:
            Dictionary containing structured journey information with keys:
            - transformers_applied: List of transformer IDs that processed the event
            - filter_decisions: Mapping of filter names to their pass/fail decisions
            - component_durations_ms: Processing times for individual components
            - derived_from: Information about event transformation chains
            - error_contexts: Any error-related metadata for debugging

        """
        custom = getattr(metadata, "custom", {}) or {}
        journey_info: dict[str, Any] = {}

        # Extract applied transformers
        transformers_applied = [
            key.replace("_applied", "")
            for key in custom
            if key.endswith("_applied") and custom[key] is True
        ]
        if transformers_applied:
            journey_info["transformers_applied"] = transformers_applied

        # Extract filter decisions
        filter_decisions = {}
        for key, value in custom.items():
            if key.endswith("_decision"):
                filter_name = key.replace("_decision", "")
                filter_decisions[filter_name] = value
        if filter_decisions:
            journey_info["filter_decisions"] = filter_decisions

        # Extract processing times
        processing_times = {}
        for key, value in custom.items():
            if key.endswith("_duration_ms") and isinstance(value, (int, float)):
                component_name = key.replace("_duration_ms", "")
                processing_times[component_name] = value
        if processing_times:
            journey_info["component_durations_ms"] = processing_times

        # Extract transformation chain if available
        if "derived_from" in custom:
            journey_info["derived_from"] = custom["derived_from"]

        # Extract any error contexts
        error_contexts = {
            key: value
            for key, value in custom.items()
            if "error" in key.lower() or "failed" in key.lower()
        }
        if error_contexts:
            journey_info["error_contexts"] = error_contexts

        return journey_info

    async def _apply_filters(self, event: PipelineEvent) -> PipelineEvent | None:
        """Apply all configured filters to the event sequentially.

        Processes the event through each configured filter in order, applying the
        filter's logic to determine if the event should continue through the pipeline.
        If any filter returns False, the event is immediately dropped and no further
        processing occurs.

        Each filter application is timed and logged for performance monitoring.
        Filter errors are logged with comprehensive context including filter ID,
        event details, and processing timing. All filter statistics are recorded
        including processing duration and pass/fail status.

        The method updates the event's processing stage to FILTER and maintains
        the event's metadata chain for tracing and debugging purposes.

        Args:
            event: The pipeline event to filter, which will be updated with filter
                stage information and processing metadata.

        Returns:
            The filtered event if all filters pass, or None if any filter rejects
            the event. The returned event maintains all metadata from the filtering
            process for downstream components.

        Raises:
            Exception: Any exception from filter processing is logged with detailed
                context and re-raised to allow upstream error handling decisions.

        """
        current_event = event.with_stage(PipelineStage.FILTER, self.pipeline_id)

        for filter_instance in self.filters:
            start_time = time.time()

            try:
                if not filter_instance(current_event):
                    # Event was filtered out
                    if self.stats_collector:
                        processing_duration_seconds = time.time() - start_time
                        event_type = type(current_event).__name__

                        self.stats_collector.record_filter_processed(
                            filter_id=filter_instance.filter_id,
                            processing_duration_seconds=processing_duration_seconds,
                            passed=False,
                            event_type=event_type,
                        )

                    logger.debug(
                        "Event filtered out",
                        pipeline_id=self.pipeline_id,
                        filter_id=filter_instance.filter_id,
                        event_id=event.metadata.event_id,
                        trace_id=current_event.metadata.trace_id,
                        event_age_seconds=current_event.metadata.age_seconds,
                        stage=current_event.metadata.stage.value,
                        source=current_event.metadata.source,
                        event_type=type(current_event).__name__,
                    )
                    return None

                # Record successful filter application
                if self.stats_collector:
                    processing_duration_seconds = time.time() - start_time
                    event_type = type(current_event).__name__

                    self.stats_collector.record_filter_processed(
                        filter_id=filter_instance.filter_id,
                        processing_duration_seconds=processing_duration_seconds,
                        passed=True,
                        event_type=event_type,
                    )

            except Exception as e:
                # Record filter error with enhanced context
                duration_ms = (time.time() - start_time) * 1000

                # Add error context using metadata
                error_context = {
                    "failed_at_stage": "filter",
                    "filter_id": filter_instance.filter_id,
                    "event_type": type(current_event).__name__,
                    "pipeline_stage": current_event.metadata.stage.value,
                    "event_age_seconds": current_event.metadata.age_seconds,
                    "trace_id": current_event.metadata.trace_id,
                    "source": current_event.metadata.source,
                    "duration_ms": duration_ms,
                }

                # Log enhanced error information
                logger.error(
                    "Filter processing error",
                    pipeline_id=self.pipeline_id,
                    filter_id=filter_instance.filter_id,
                    event_id=current_event.metadata.event_id,
                    error=str(e),
                    error_type=type(e).__name__,
                    **error_context,
                )

                self.error_handler.handle_error(
                    event.metadata.event_id,
                    PipelineStage.FILTER,
                    filter_instance.filter_id,
                    e,
                    current_event,
                )

                if self.stats_collector:
                    self.stats_collector.record_stage_error(
                        stage="filter",
                        stage_id=filter_instance.filter_id,
                        error_type=type(e).__name__,
                    )

                # Re-raise filter errors
                raise

        return current_event

    async def _apply_transformation(self, event: PipelineEvent) -> PipelineEvent:
        """Apply the configured transformer to convert the event.

        Processes the event through the configured transformer if one is present,
        otherwise returns the event unchanged. The transformation stage updates
        the event's processing stage and applies the transformer's logic to
        convert the event to a different type or modify its content.

        Transformation processing is timed and logged for performance monitoring.
        Both successful transformations and errors are recorded with comprehensive
        context including input/output types, processing duration, and event
        metadata.

        The method maintains event metadata chains and tracing information to
        support debugging and monitoring of transformation processes.

        Args:
            event: The pipeline event to transform, which will be updated with
                transformation stage information.

        Returns:
            The transformed event with updated type and content as determined by
            the transformer, or the original event if no transformer is configured.
            All metadata and tracing information is preserved.

        Raises:
            Exception: Any exception from transformation processing is logged with
                detailed context including transformer ID, input/output types, and
                timing information, then re-raised for upstream handling.

        """
        if not self.transformer:
            return event

        current_event = event.with_stage(PipelineStage.TRANSFORM, self.pipeline_id)
        start_time = time.time()

        try:
            transformed_event = self.transformer(current_event)

            # Record successful transformation with enhanced logging
            duration_ms = (time.time() - start_time) * 1000

            logger.debug(
                "Event transformation completed",
                pipeline_id=self.pipeline_id,
                transformer_id=self.transformer.transformer_id,
                event_id=current_event.metadata.event_id,
                trace_id=current_event.metadata.trace_id,
                input_type=type(current_event).__name__,
                output_type=type(transformed_event).__name__,
                event_age_seconds=current_event.metadata.age_seconds,
                transformation_duration_ms=duration_ms,
                stage=current_event.metadata.stage.value,
            )

            if self.stats_collector:
                processing_duration_seconds = time.time() - start_time
                input_type = type(current_event).__name__
                output_type = type(transformed_event).__name__

                self.stats_collector.record_transformation_processed(
                    transformer_id=self.transformer.transformer_id,
                    processing_duration_seconds=processing_duration_seconds,
                    input_type=input_type,
                    output_type=output_type,
                )

        except Exception as e:
            # Record transformation error with enhanced context
            duration_ms = (time.time() - start_time) * 1000

            # Add transformation-specific error context
            error_context = {
                "failed_at_stage": "transformation",
                "transformer_id": self.transformer.transformer_id,
                "input_event_type": type(current_event).__name__,
                "pipeline_stage": current_event.metadata.stage.value,
                "event_age_seconds": current_event.metadata.age_seconds,
                "trace_id": current_event.metadata.trace_id,
                "source": current_event.metadata.source,
                "duration_ms": duration_ms,
            }

            logger.error(
                "Transformation processing error",
                pipeline_id=self.pipeline_id,
                transformer_id=self.transformer.transformer_id,
                event_id=current_event.metadata.event_id,
                error=str(e),
                error_type=type(e).__name__,
                **error_context,
            )

            self.error_handler.handle_error(
                event.metadata.event_id,
                PipelineStage.TRANSFORM,
                self.transformer.transformer_id,
                e,
                current_event,
            )

            if self.stats_collector:
                self.stats_collector.record_stage_error(
                    stage="transform",
                    stage_id=self.transformer.transformer_id,
                    error_type=type(e).__name__,
                )

            # Re-raise transformation errors
            raise

        return transformed_event

    async def _send_to_outputs(self, event: PipelineEvent) -> None:
        """Send the event to all configured outputs concurrently.

        Delivers the event to all configured outputs using concurrent execution
        to minimize total delivery time. Each output is processed independently
        with individual error handling to prevent failures in one output from
        affecting others.

        The method creates an async task for each output and waits for all to
        complete using asyncio.gather with return_exceptions=True. If any outputs
        fail, warnings are logged with failure counts, and the first error is
        re-raised to signal pipeline failure.

        The event's processing stage is updated to OUTPUT before delivery to
        support proper error handling and tracing throughout the output stage.

        Args:
            event: The pipeline event to deliver to all outputs, which will be
                updated with output stage information.

        Raises:
            Exception: If any output fails during delivery, the first error
                encountered is re-raised after logging summary information about
                all failures. This ensures pipeline errors are propagated while
                providing comprehensive error context.

        """
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
        """Send an event to a single output with comprehensive error handling.

        Delivers the event to a specific output while recording detailed performance
        metrics and error information. The method times the output operation and
        logs comprehensive context for both successful deliveries and failures.

        For successful deliveries, the method records processing duration, payload
        size estimation, and destination information in the statistics collector.
        For failures, detailed error context is logged including output state,
        timing information, and event metadata.

        All errors are handled through the pipeline's error handler and recorded
        in statistics before being re-raised for upstream handling decisions.

        Args:
            output: The specific output instance to deliver the event to.
            event: The pipeline event to deliver with all metadata and content.

        Raises:
            Exception: Any exception from output delivery is logged with comprehensive
                context including output ID, event details, timing information, and
                output state, then re-raised for pipeline-level error handling.

        """
        start_time = time.time()

        try:
            await output(event)

            # Record successful output with enhanced logging
            duration_ms = (time.time() - start_time) * 1000

            logger.debug(
                "Event output completed",
                pipeline_id=self.pipeline_id,
                output_id=output.output_id,
                event_id=event.metadata.event_id,
                trace_id=event.metadata.trace_id,
                event_type=type(event).__name__,
                event_age_seconds=event.metadata.age_seconds,
                output_duration_ms=duration_ms,
                stage=event.metadata.stage.value,
                source=event.metadata.source,
            )

            if self.stats_collector:
                processing_duration_seconds = time.time() - start_time
                destination = type(output).__name__
                # Estimate payload size (simplified)
                payload_size_bytes = len(str(event))

                self.stats_collector.record_output_delivered(
                    output_id=output.output_id,
                    processing_duration_seconds=processing_duration_seconds,
                    payload_size_bytes=payload_size_bytes,
                    destination=destination,
                )

        except Exception as e:
            # Record output error with enhanced context
            duration_ms = (time.time() - start_time) * 1000

            # Add output-specific error context
            error_context = {
                "failed_at_stage": "output",
                "output_id": output.output_id,
                "output_type": type(output).__name__,
                "event_type": type(event).__name__,
                "pipeline_stage": event.metadata.stage.value,
                "event_age_seconds": event.metadata.age_seconds,
                "trace_id": event.metadata.trace_id,
                "source": event.metadata.source,
                "duration_ms": duration_ms,
                "output_started": output.is_started,
            }

            logger.error(
                "Output processing error",
                pipeline_id=self.pipeline_id,
                output_id=output.output_id,
                event_id=event.metadata.event_id,
                error=str(e),
                error_type=type(e).__name__,
                **error_context,
            )

            self.error_handler.handle_error(
                event.metadata.event_id,
                PipelineStage.OUTPUT,
                output.output_id,
                e,
                event,
            )

            if self.stats_collector:
                self.stats_collector.record_stage_error(
                    stage="output",
                    stage_id=output.output_id,
                    error_type=type(e).__name__,
                )

            # Re-raise output errors
            raise

    @property
    def is_started(self) -> bool:
        """Check if the pipeline is currently in a started state.

        Returns:
            True if the pipeline has been started and is ready to process events,
            False if the pipeline is stopped or has not been started.

        """
        return self._is_started

    def get_stats_summary(self) -> dict[str, Any] | None:
        """Get a comprehensive summary of pipeline processing statistics.

        Retrieves accumulated statistics from the pipeline's statistics collector
        including processing counts, timing metrics, error rates, and performance
        data across all pipeline stages.

        Returns:
            Dictionary containing pipeline statistics summary with metrics for
            events processed, processing times, error counts, and stage-specific
            performance data. Returns None if no statistics collector is configured.

        """
        return self.stats_collector.get_summary() if self.stats_collector else None

    def get_error_summary(self) -> dict[str, Any]:
        """Get a comprehensive summary of pipeline error history and statistics.

        Retrieves accumulated error information from the pipeline's error handler
        including error counts by type, stage-specific error rates, and recent
        error context for debugging and monitoring purposes.

        Returns:
            Dictionary containing error summary with counts by error type, stage
            where errors occurred, recent error details, and other error-related
            metrics for operational monitoring.

        """
        return self.error_handler.get_error_summary()


class PipelineManager:
    """Centralized manager for multiple pipelines with concurrent event processing.

    The PipelineManager serves as the central orchestration point for multiple
    Pipeline instances within the NWWS system. It provides unified event routing,
    lifecycle management, and resource coordination across all registered pipelines.
    The manager implements a queue-based architecture for efficient event distribution
    and concurrent processing.

    Key responsibilities:
    - Pipeline registration and lifecycle management
    - Centralized event queuing and distribution
    - Concurrent event processing across multiple pipelines
    - Resource management and cleanup coordination
    - Performance monitoring and statistics aggregation
    - Graceful shutdown and error handling

    The manager operates an internal event processing loop that continuously dequeues
    events and routes them to appropriate pipelines. Events can be routed to specific
    pipelines or broadcast to all registered pipelines. The processing loop includes
    timeout handling, error recovery, and comprehensive logging.

    The manager implements proper async context manager protocol for resource management
    and provides safety mechanisms to prevent resource leaks through proper cleanup
    in destructor and context exit handlers.
    """

    def __init__(self, config: PipelineManagerConfig | None = None) -> None:
        """Initialize the pipeline manager with configuration and internal state.

        Creates a new pipeline manager instance with an internal event queue for
        processing events across multiple pipelines. The manager starts in a stopped
        state and must be explicitly started before accepting events.

        The event queue is configured with a maximum size to provide backpressure
        and prevent memory exhaustion under high load conditions. The processing
        task is created during startup to handle the continuous event processing loop.

        Args:
            config: Optional configuration object containing queue size limits,
                timeout values, and other operational parameters. If not provided,
                default configuration values are used.

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
        """Add a pipeline to the manager's registry for event processing.

        Registers a new pipeline with the manager and starts it immediately if
        the manager is currently running. This allows for dynamic pipeline
        registration during runtime without requiring manager restart.

        The pipeline is indexed by its pipeline_id, which must be unique within
        the manager's context. If the manager is running, the pipeline is started
        immediately to begin participating in event processing.

        Args:
            pipeline: The pipeline instance to register with the manager. The
                pipeline's pipeline_id must be unique within this manager's context.

        Raises:
            PipelineError: If the pipeline fails to start when the manager is
                running, or if there are conflicts with the pipeline configuration.

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
        """Remove a pipeline from the manager's registry.

        Unregisters a pipeline from the manager's active pipeline list. The
        pipeline is not automatically stopped - the caller is responsible for
        proper lifecycle management of the removed pipeline.

        Removing a pipeline while the manager is running will prevent new events
        from being routed to that pipeline, but does not affect events already
        in the processing queue.

        Args:
            pipeline_id: Unique identifier of the pipeline to remove from the
                manager's registry.

        Returns:
            The removed pipeline instance if found, or None if no pipeline with
            the specified ID was registered. The caller should handle stopping
            the returned pipeline if needed.

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
        """Retrieve a specific pipeline by its identifier.

        Provides access to registered pipeline instances for direct manipulation
        or status checking. This method is used for pipeline-specific operations
        that cannot be performed through the manager's unified interface.

        Args:
            pipeline_id: Unique identifier of the pipeline to retrieve.

        Returns:
            The pipeline instance if found, or None if no pipeline with the
            specified ID is registered with this manager.

        """
        return self._pipelines.get(pipeline_id)

    def get_all_pipelines(self) -> list[Pipeline]:
        """Retrieve all registered pipelines for bulk operations or monitoring.

        Provides access to all pipeline instances managed by this manager for
        operations that need to iterate over all pipelines or collect aggregate
        information.

        Returns:
            List of all pipeline instances currently registered with the manager.
            The list is a copy and modifications will not affect the manager's
            internal registry.

        """
        return list(self._pipelines.values())

    async def start(self) -> None:
        """Start the pipeline manager and all registered pipelines.

        Transitions the manager from stopped to running state by starting all
        registered pipelines and launching the internal event processing task.
        The startup process validates that all pipelines can be started before
        beginning event processing.

        The manager startup is idempotent - calling start() on an already running
        manager has no effect. All pipelines are started sequentially to ensure
        proper error reporting and resource initialization.

        After successful startup, the manager begins accepting events through
        submit_event and submit_event_to_all methods and processes them through
        the internal event processing loop.

        Raises:
            PipelineError: If any pipeline fails to start, the manager startup
                fails and remains in stopped state. All successfully started
                pipelines are left running.

        """
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
        """Stop the pipeline manager and gracefully shut down all components.

        Transitions the manager from running to stopped state by cancelling the
        event processing task and stopping all registered pipelines. The shutdown
        process attempts to stop all components gracefully even if some fail.

        The manager stop is idempotent - calling stop() on an already stopped
        manager has no effect. The event processing task is cancelled and awaited
        to ensure proper cleanup of the processing loop.

        After stopping, the manager will no longer accept new events and all
        pipelines will be in a stopped state. The manager can be restarted after
        stopping to resume operations.
        """
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
        """Enter async context manager by starting the pipeline manager.

        Provides async context manager support for automatic resource management.
        Starting the manager when entering the context ensures all pipelines are
        ready for event processing.

        Returns:
            Self instance for use within the async context block.

        Raises:
            PipelineError: If the manager fails to start during context entry.

        """
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context manager and ensure complete cleanup.

        Provides async context manager support for automatic resource cleanup.
        Stopping the manager when exiting the context ensures all pipelines are
        properly shut down and resources are released.

        Args:
            exc_type: Type of exception that caused context exit, if any.
            exc_val: Exception instance that caused context exit, if any.
            exc_tb: Exception traceback object, if any.

        """
        await self.stop()

    def __del__(self) -> None:
        """Clean up resources when the manager is garbage collected.

        Provides safety mechanism to prevent resource leaks if the manager is
        garbage collected while still running. This should not be relied upon
        for normal operation - proper cleanup should use stop() or async context
        manager protocol.

        If the manager is still running when garbage collected, a warning is
        logged and an attempt is made to cancel the processing task. However,
        this cleanup is best-effort and may not complete successfully if the
        event loop is already closed.

        """
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

        Queues an event for processing by a specific pipeline identified by its
        pipeline_id. The event is added to the internal event queue and will be
        processed by the event processing loop when capacity is available.

        The submission includes timeout handling to prevent blocking indefinitely
        if the event queue is full. If the manager is not running, the event is
        dropped with a warning log message.

        Args:
            pipeline_id: Identifier of the specific pipeline that should process
                the event. The pipeline must be registered with this manager.
            event: The pipeline event to process containing payload and metadata
                for tracking and error handling.

        Raises:
            TimeoutError: If the event cannot be queued within the configured
                timeout period, typically due to queue backpressure from high
                event volume or slow pipeline processing.

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
        """Submit an event to all registered pipelines for processing.

        Queues an event for processing by all currently registered pipelines.
        The event is added to the internal event queue with a None pipeline_id
        marker indicating it should be broadcast to all pipelines.

        The submission includes timeout handling to prevent blocking indefinitely
        if the event queue is full. If the manager is not running, the event is
        dropped with a warning log message.

        Args:
            event: The pipeline event to process through all registered pipelines.
                Each pipeline will receive a copy of the event for independent
                processing.

        Raises:
            TimeoutError: If the event cannot be queued within the configured
                timeout period, typically due to queue backpressure from high
                event volume or slow pipeline processing.

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
        """Process events from the queue through specified or all pipelines.

        Implements the core event processing loop that continuously dequeues events
        and routes them to appropriate pipelines. The loop runs until the manager
        is stopped and handles both targeted pipeline processing and broadcast
        processing to all pipelines.

        For broadcast events (pipeline_id is None), the event is processed
        concurrently through all started pipelines using asyncio.gather. For
        targeted events, the event is processed by the specified pipeline with
        timeout handling.

        The processing loop includes comprehensive error handling for various
        failure scenarios including pipeline errors, timeouts, and queue
        processing errors. All errors are logged with detailed context but
        do not terminate the processing loop.

        The loop uses a 1-second timeout on queue operations to allow periodic
        checking of the running state and graceful shutdown when requested.

        """
        while self._is_running:
            try:
                # Wait for next event with timeout
                pipeline_id, event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)

                if pipeline_id is None:
                    # Process event through all pipelines concurrently
                    tasks = [
                        asyncio.create_task(pipeline.process(event))
                        for pipeline in self._pipelines.values()
                        if pipeline.is_started
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
        """Check if the pipeline manager is currently running and processing events.

        Returns:
            True if the manager is started and actively processing events through
            the internal processing loop, False if stopped or not yet started.

        """
        return self._is_running

    @property
    def queue_size(self) -> int:
        """Get the current number of events in the processing queue.

        Provides insight into the current queue depth for monitoring and
        capacity planning. High queue sizes may indicate processing bottlenecks
        or high event volume that exceeds processing capacity.

        Returns:
            Current number of events waiting in the queue for processing.

        """
        return self._event_queue.qsize()

    def get_manager_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics and status information for the manager.

        Collects and aggregates status information from the manager and all
        registered pipelines including running state, queue status, pipeline
        counts, and individual pipeline statistics and error summaries.

        This method provides a complete operational view of the manager state
        for monitoring, debugging, and capacity planning purposes.

        Returns:
            Dictionary containing comprehensive manager statistics including:
            - is_running: Current running state of the manager
            - pipeline_count: Total number of registered pipelines
            - queue_size: Current event queue depth
            - pipelines: Per-pipeline status and statistics including start state,
              component counts, processing statistics, and error summaries

        """
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
