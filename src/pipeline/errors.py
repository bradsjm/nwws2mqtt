# pyright: strict
"""Pipeline error handling and error events."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .types import EventId, PipelineEvent, PipelineStage, StageId, Timestamp


class PipelineError(Exception):
    """Base exception for pipeline-related errors."""

    def __init__(self, message: str, stage: PipelineStage | None = None, stage_id: str | None = None) -> None:
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


class ErrorHandler:
    """Handles and tracks pipeline errors."""

    def __init__(self) -> None:
        """Initialize the error handler."""
        self._error_counts: dict[str, int] = {}
        self._last_errors: dict[str, PipelineErrorEvent] = {}

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
        """Handle an error and create an error event."""
        error_key = f"{stage.value}.{stage_id}"
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1

        error_event = PipelineErrorEvent(
            event_id=event_id,
            stage=stage,
            stage_id=stage_id,
            error_type=type(exception).__name__,
            error_message=str(exception),
            original_event=original_event,
            exception=exception,
            details=details,
            recoverable=recoverable,
        )

        self._last_errors[error_key] = error_event
        return error_event

    def get_error_count(self, stage: PipelineStage, stage_id: StageId) -> int:
        """Get the error count for a specific stage component."""
        error_key = f"{stage.value}.{stage_id}"
        return self._error_counts.get(error_key, 0)

    def get_last_error(self, stage: PipelineStage, stage_id: StageId) -> PipelineErrorEvent | None:
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
            "errors_by_stage": self._error_counts.copy(),
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

    def reset_errors(self) -> None:
        """Reset all error tracking."""
        self._error_counts.clear()
        self._last_errors.clear()
