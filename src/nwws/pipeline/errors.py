# pyright: strict
"""Pipeline error handling and error events."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from .types import EventId, PipelineEvent, PipelineStage, StageId, Timestamp


class ErrorHandlingStrategy(Enum):
    """Strategy for handling errors in pipeline processing.

    Each strategy determines how the pipeline responds to errors at any stage.
    Choose the strategy that best fits your reliability and operational requirements:

    - FAIL_FAST: Stops processing immediately on the first error encountered. No retries are
      attempted, and the pipeline or stage will halt, propagating the exception upstream. Use
      this for strict correctness or when errors indicate unrecoverable conditions.

    - CONTINUE: Logs the error and continues processing subsequent events or stages. The error
      is recorded, but the pipeline does not retry or halt. Use this when occasional errors are
      tolerable and you want maximum throughput and resilience to transient failures.

    - RETRY: Retries the failed operation up to a configurable maximum number of times
      (default: 3), with exponential backoff between attempts (default multiplier: 2.0,
      base delay: 1.0s). Retries are only attempted for certain exception types (OSError,
      ConnectionError, TimeoutError). If all retries fail, the error is logged and processing
      continues or fails based on context. Use this for transient or recoverable errors where
      retrying may succeed.

    - CIRCUIT_BREAKER: Uses the circuit breaker pattern for external dependencies. After a
      configurable number of consecutive failures (default: 5), the circuit breaker "opens"
      for that stage/component, causing further attempts to fail immediately for a timeout
      period (default: 60s). After the timeout, the circuit enters a "half-open" state to
      test recovery. If successful, it closes; if not, it reopens. This prevents overwhelming
      failing dependencies and allows for graceful degradation. Use this for outputs or stages
      that depend on unreliable external services.
    """

    FAIL_FAST = "fail_fast"
    """Stop processing immediately on the first error encountered. No retries are attempted,
    and the pipeline or stage will halt, propagating the exception upstream. Use for strict
    correctness or when errors are unrecoverable.
    """

    CONTINUE = "continue"
    """Log the error and continue processing subsequent events or stages. No retries are attempted.
    Errors are recorded, but the pipeline does not halt. Use when occasional errors are tolerable and
    you want maximum throughput.
    """

    RETRY = "retry"
    """Retry the failed operation up to a configurable maximum number of times (default: 3), with
    exponential backoff (default multiplier: 2.0, base delay: 1.0s). Retries are only attempted for
    OSError, ConnectionError, or TimeoutError. If all retries fail, the error is logged and processing
    continues or fails based on context. Use for transient or recoverable errors.
    """

    CIRCUIT_BREAKER = "circuit_breaker"
    """Use the circuit breaker pattern for external dependencies. After a configurable number of
    consecutive failures (default: 5), the circuit breaker opens for that stage/component, causing
    further attempts to fail immediately for a timeout period (default: 60s). After the timeout,
    the circuit enters a half-open state to test recovery. If successful, it closes; if not, it
    reopens. Use for outputs or stages that depend on unreliable external services.
    """


class PipelineError(Exception):
    """Base exception for pipeline-related errors."""

    def __init__(
        self,
        message: str,
        stage: PipelineStage | None = None,
        stage_id: str | None = None,
    ) -> None:
        """Initialize pipeline error with context."""
        super().__init__(message)
        self.stage = stage
        self.stage_id = stage_id


class FilterError(PipelineError):
    """Error during filter processing."""

    def __init__(self, message: str, filter_id: str) -> None:
        """Initialize filter error."""
        super().__init__(message, PipelineStage.FILTER, filter_id)


class TransformerError(PipelineError):
    """Error during transformation processing."""

    def __init__(self, message: str, transformer_id: str) -> None:
        """Initialize transformer error."""
        super().__init__(message, PipelineStage.TRANSFORM, transformer_id)


class OutputError(PipelineError):
    """Error during output processing."""

    def __init__(self, message: str, output_id: str) -> None:
        """Initialize output error."""
        super().__init__(message, PipelineStage.OUTPUT, output_id)


@dataclass(frozen=True)
class PipelineErrorEvent:
    """Event representing an error that occurred during pipeline processing."""

    event_id: EventId
    """Unique identifier for the original event that caused the error."""

    stage: PipelineStage
    """Pipeline stage where the error occurred."""

    stage_id: StageId
    """Specific component ID within the stage."""

    error_type: str
    """Type of error that occurred."""

    error_message: str
    """Human-readable error message."""

    timestamp: Timestamp = field(default_factory=time.time)
    """When this error occurred."""

    original_event: PipelineEvent | None = None
    """The original event that caused this error."""

    exception: Exception | None = None
    """The original exception, if available."""

    details: dict[str, Any] = field(default_factory=dict)
    """Additional error details and context."""

    recoverable: bool = False
    """Whether this error is recoverable."""


class PipelineErrorHandler:
    """Handles and tracks pipeline errors."""

    def __init__(  # noqa: PLR0913
        self,
        strategy: ErrorHandlingStrategy = ErrorHandlingStrategy.CONTINUE,
        *,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        backoff_multiplier: float = 2.0,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout_seconds: float = 60.0,
    ) -> None:
        """Initialize the error handler.

        Args:
            strategy: Error handling strategy to use.
            max_retries: Maximum number of retries for RETRY strategy.
            retry_delay_seconds: Base delay between retries for RETRY strategy.
            backoff_multiplier: Multiplier for exponential backoff for RETRY strategy.
            circuit_breaker_threshold: Number of failures to trigger circuit breaker.
            circuit_breaker_timeout_seconds: Time to wait before resetting circuit breaker.

        """
        self.strategy = strategy
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.backoff_multiplier = backoff_multiplier
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout_seconds = circuit_breaker_timeout_seconds

        self._error_counts: dict[str, int] = {}
        self._last_errors: dict[str, PipelineErrorEvent] = {}
        self._retry_counts: dict[str, int] = {}
        self._circuit_breaker_states: dict[str, dict[str, Any]] = {}

    def handle_error(  # noqa: PLR0913
        self,
        event_id: EventId,
        stage: PipelineStage,
        stage_id: StageId,
        exception: Exception,
        original_event: PipelineEvent | None = None,
        *,
        recoverable: bool = False,
        **details: Any,
    ) -> PipelineErrorEvent:
        """Handle an error and create an error event with enhanced metadata context."""
        error_key = f"{stage.value}.{stage_id}"
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1

        # Extract enhanced context from event metadata if available
        enhanced_details = details.copy()
        if original_event and original_event.metadata:
            metadata = original_event.metadata
            enhanced_details.update(
                {
                    "event_age_seconds": metadata.age_seconds,
                    "trace_id": metadata.trace_id,
                    "source": metadata.source,
                    "current_stage": metadata.stage.value,
                    "event_type": type(original_event).__name__,
                }
            )

            # Extract journey information from custom metadata
            journey_info = self._extract_journey_from_metadata(metadata)
            if journey_info:
                enhanced_details["journey_info"] = journey_info

        error_event = PipelineErrorEvent(
            event_id=event_id,
            stage=stage,
            stage_id=stage_id,
            error_type=type(exception).__name__,
            error_message=str(exception),
            original_event=original_event,
            exception=exception,
            details=enhanced_details,
            recoverable=recoverable,
        )

        self._last_errors[error_key] = error_event

        # Log error with enhanced context
        self._log_error_with_context(error_event, enhanced_details)

        # Update circuit breaker state if using that strategy
        if self.strategy == ErrorHandlingStrategy.CIRCUIT_BREAKER:
            self._update_circuit_breaker(error_key, failed=True)

        return error_event

    async def should_retry(
        self,
        stage: PipelineStage,
        stage_id: StageId,
        exception: Exception,
    ) -> bool:
        """Determine if an operation should be retried."""
        if self.strategy != ErrorHandlingStrategy.RETRY:
            return False

        error_key = f"{stage.value}.{stage_id}"
        retry_count = self._retry_counts.get(error_key, 0)

        if retry_count >= self.max_retries:
            logger.warning(
                "Max retries exceeded",
                stage=stage.value,
                stage_id=stage_id,
                retry_count=retry_count,
                max_retries=self.max_retries,
            )
            return False

        # Only retry on certain types of exceptions
        return isinstance(exception, (OSError, ConnectionError, TimeoutError))

    async def execute_with_retry(
        self,
        stage: PipelineStage,
        stage_id: StageId,
        operation: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute an operation with retry logic."""
        error_key = f"{stage.value}.{stage_id}"

        for attempt in range(self.max_retries + 1):
            try:
                if self._is_circuit_breaker_open(error_key):
                    error_msg = f"Circuit breaker is open for {error_key}"
                    raise PipelineError(  # noqa: TRY301
                        error_msg,
                        stage,
                        stage_id,
                    )

                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)  # type: ignore[misc]
                else:
                    result = operation(*args, **kwargs)

                # Reset retry count on success
                self._retry_counts[error_key] = 0

                # Update circuit breaker on success
                if self.strategy == ErrorHandlingStrategy.CIRCUIT_BREAKER:
                    self._update_circuit_breaker(error_key, failed=False)

                return result  # noqa: TRY300

            except Exception as e:
                self._retry_counts[error_key] = attempt + 1

                if attempt < self.max_retries and await self.should_retry(
                    stage, stage_id, e
                ):
                    delay = self.retry_delay_seconds * (
                        self.backoff_multiplier**attempt
                    )
                    logger.info(
                        "Retrying operation",
                        stage=stage.value,
                        stage_id=stage_id,
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
                    continue

                # Final failure
                if self.strategy == ErrorHandlingStrategy.CIRCUIT_BREAKER:
                    self._update_circuit_breaker(error_key, failed=True)
                raise
        return None

    def _is_circuit_breaker_open(self, error_key: str) -> bool:
        """Check if circuit breaker is open for the given error key."""
        if error_key not in self._circuit_breaker_states:
            return False

        state = self._circuit_breaker_states[error_key]

        if state["state"] == "open":
            # Check if timeout has passed
            if time.time() - state["opened_at"] > self.circuit_breaker_timeout_seconds:
                # Move to half-open state
                state["state"] = "half_open"
                logger.info(
                    "Circuit breaker moving to half-open",
                    error_key=error_key,
                )
                return False
            return True

        return False

    def _update_circuit_breaker(self, error_key: str, *, failed: bool) -> None:
        """Update circuit breaker state."""
        if error_key not in self._circuit_breaker_states:
            self._circuit_breaker_states[error_key] = {
                "state": "closed",  # closed, open, half_open
                "failure_count": 0,
                "opened_at": 0.0,
            }

        state = self._circuit_breaker_states[error_key]

        if failed:
            state["failure_count"] += 1

            if state["state"] == "half_open":
                # Failed in half-open state, go back to open
                state["state"] = "open"
                state["opened_at"] = time.time()
                logger.warning(
                    "Circuit breaker opened (half-open failure)",
                    error_key=error_key,
                )
            elif (
                state["state"] == "closed"
                and state["failure_count"] >= self.circuit_breaker_threshold
            ):
                # Too many failures, open the circuit breaker
                state["state"] = "open"
                state["opened_at"] = time.time()
                logger.warning(
                    "Circuit breaker opened (threshold exceeded)",
                    error_key=error_key,
                    failure_count=state["failure_count"],
                    threshold=self.circuit_breaker_threshold,
                )
        else:
            # Success - reset failure count and close circuit breaker
            state["failure_count"] = 0
            if state["state"] in ("open", "half_open"):
                state["state"] = "closed"
                logger.info(
                    "Circuit breaker closed (success)",
                    error_key=error_key,
                )

    def get_error_count(self, stage: PipelineStage, stage_id: StageId) -> int:
        """Get the error count for a specific stage component."""
        error_key = f"{stage.value}.{stage_id}"
        return self._error_counts.get(error_key, 0)

    def get_last_error(
        self, stage: PipelineStage, stage_id: StageId
    ) -> PipelineErrorEvent | None:
        """Get the last error for a specific stage component."""
        error_key = f"{stage.value}.{stage_id}"
        return self._last_errors.get(error_key)

    def get_total_errors(self) -> int:
        """Get the total number of errors across all stages."""
        return sum(self._error_counts.values())

    def get_error_summary(self) -> dict[str, Any]:
        """Get a summary of all errors."""
        return {
            "total_errors": self.get_total_errors(),
            "strategy": self.strategy.value,
            "errors_by_stage": self._error_counts.copy(),
            "retry_counts": self._retry_counts.copy(),
            "circuit_breaker_states": {
                key: {
                    "state": state["state"],
                    "failure_count": state["failure_count"],
                    "is_open": self._is_circuit_breaker_open(key),
                }
                for key, state in self._circuit_breaker_states.items()
            },
            "last_errors": {
                key: {
                    "error_type": error.error_type,
                    "error_message": error.error_message,
                    "timestamp": error.timestamp,
                    "recoverable": error.recoverable,
                }
                for key, error in self._last_errors.items()
            },
        }

    def _extract_journey_from_metadata(self, metadata: Any) -> dict[str, Any]:
        """Extract journey information from event metadata for error context.

        Args:
            metadata: Event metadata containing custom fields.

        Returns:
            Dictionary of journey information for error context.

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

        return journey_info

    def _log_error_with_context(
        self, error_event: PipelineErrorEvent, enhanced_details: dict[str, Any]
    ) -> None:
        """Log error with enhanced context from metadata.

        Args:
            error_event: The error event to log.
            enhanced_details: Enhanced details including metadata context.

        """
        log_context = {
            "error_type": error_event.error_type,
            "stage": error_event.stage.value,
            "stage_id": error_event.stage_id,
            "event_id": error_event.event_id,
            "recoverable": error_event.recoverable,
            "strategy": self.strategy.value,
            "error_count": self._error_counts.get(
                f"{error_event.stage.value}.{error_event.stage_id}", 0
            ),
        }

        # Add metadata context if available
        if "event_age_seconds" in enhanced_details:
            log_context["event_age_seconds"] = enhanced_details["event_age_seconds"]
        if "trace_id" in enhanced_details:
            log_context["trace_id"] = enhanced_details["trace_id"]
        if "source" in enhanced_details:
            log_context["source"] = enhanced_details["source"]
        if "event_type" in enhanced_details:
            log_context["event_type"] = enhanced_details["event_type"]

        # Add journey information if available
        if "journey_info" in enhanced_details:
            journey = enhanced_details["journey_info"]
            if "transformers_applied" in journey:
                log_context["transformers_applied"] = journey["transformers_applied"]
            if "filter_decisions" in journey:
                log_context["filter_decisions"] = journey["filter_decisions"]
            if "component_durations_ms" in journey:
                log_context["total_processing_time_ms"] = sum(
                    journey["component_durations_ms"].values()
                )

        logger.error(
            "Pipeline error occurred with enhanced context",
            error_message=error_event.error_message,
            **log_context,
        )

    def reset_errors(self) -> None:
        """Reset all error tracking."""
        self._error_counts.clear()
        self._last_errors.clear()
        self._retry_counts.clear()
        self._circuit_breaker_states.clear()
