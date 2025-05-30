# pyright: strict
"""Tests for pipeline error handling module."""

from __future__ import annotations

import pytest

from src.pipeline.errors import (
    ErrorHandler,
    ErrorHandlingStrategy,
    FilterError,
    OutputError,
    PipelineError,
    PipelineErrorEvent,
    TransformerError,
)
from src.pipeline.types import PipelineEvent, PipelineEventMetadata, PipelineStage


class TestPipelineError:
    """Test PipelineError and subclasses."""

    def test_pipeline_error_basic(self) -> None:
        """Test basic PipelineError creation."""
        error = PipelineError("Test error")
        assert str(error) == "Test error"
        assert error.stage is None
        assert error.stage_id is None

    def test_pipeline_error_with_context(self) -> None:
        """Test PipelineError with stage context."""
        error = PipelineError("Test error", PipelineStage.FILTER, "filter-1")
        assert str(error) == "Test error"
        assert error.stage == PipelineStage.FILTER
        assert error.stage_id == "filter-1"

    def test_filter_error(self) -> None:
        """Test FilterError creation."""
        error = FilterError("Filter failed", "filter-123")
        assert str(error) == "Filter failed"
        assert error.stage == PipelineStage.FILTER
        assert error.stage_id == "filter-123"

    def test_transformer_error(self) -> None:
        """Test TransformerError creation."""
        error = TransformerError("Transform failed", "transformer-456")
        assert str(error) == "Transform failed"
        assert error.stage == PipelineStage.TRANSFORM
        assert error.stage_id == "transformer-456"

    def test_output_error(self) -> None:
        """Test OutputError creation."""
        error = OutputError("Output failed", "output-789")
        assert str(error) == "Output failed"
        assert error.stage == PipelineStage.OUTPUT
        assert error.stage_id == "output-789"


class TestPipelineErrorEvent:
    """Test PipelineErrorEvent data class."""

    def test_error_event_creation(self) -> None:
        """Test error event creation with required fields."""
        event = PipelineErrorEvent(
            event_id="test-event",
            stage=PipelineStage.FILTER,
            stage_id="filter-1",
            error_type="ValueError",
            error_message="Invalid value",
        )

        assert event.event_id == "test-event"
        assert event.stage == PipelineStage.FILTER
        assert event.stage_id == "filter-1"
        assert event.error_type == "ValueError"
        assert event.error_message == "Invalid value"
        assert event.timestamp > 0
        assert event.original_event is None
        assert event.exception is None
        assert event.details == {}
        assert event.recoverable is False

    def test_error_event_with_optional_fields(self) -> None:
        """Test error event with optional fields."""
        original_event = PipelineEvent(metadata=PipelineEventMetadata())
        exception = ValueError("Test error")
        details = {"context": "test"}

        event = PipelineErrorEvent(
            event_id="test-event",
            stage=PipelineStage.OUTPUT,
            stage_id="output-1",
            error_type="ValueError",
            error_message="Test error",
            original_event=original_event,
            exception=exception,
            details=details,
            recoverable=True,
        )

        assert event.original_event == original_event
        assert event.exception == exception
        assert event.details == details
        assert event.recoverable is True


class TestErrorHandler:
    """Test ErrorHandler functionality."""

    def test_default_initialization(self) -> None:
        """Test error handler with default settings."""
        handler = ErrorHandler()
        assert handler.strategy == ErrorHandlingStrategy.CONTINUE
        assert handler.max_retries == 3
        assert handler.retry_delay_seconds == 1.0

    def test_custom_initialization(self) -> None:
        """Test error handler with custom settings."""
        handler = ErrorHandler(
            strategy=ErrorHandlingStrategy.RETRY,
            max_retries=5,
            retry_delay_seconds=0.5,
        )
        assert handler.strategy == ErrorHandlingStrategy.RETRY
        assert handler.max_retries == 5
        assert handler.retry_delay_seconds == 0.5

    def test_handle_error(self) -> None:
        """Test basic error handling."""
        handler = ErrorHandler()
        exception = ValueError("Test error")

        error_event = handler.handle_error(
            event_id="test-event",
            stage=PipelineStage.FILTER,
            stage_id="filter-1",
            exception=exception,
        )

        assert error_event.event_id == "test-event"
        assert error_event.stage == PipelineStage.FILTER
        assert error_event.stage_id == "filter-1"
        assert error_event.error_type == "ValueError"
        assert error_event.error_message == "Test error"
        assert error_event.exception == exception

    def test_error_counting(self) -> None:
        """Test error counting functionality."""
        handler = ErrorHandler()

        # No errors initially
        assert handler.get_error_count(PipelineStage.FILTER, "filter-1") == 0
        assert handler.get_total_errors() == 0

        # Handle first error
        handler.handle_error(
            "event-1", PipelineStage.FILTER, "filter-1", ValueError("Error 1")
        )
        assert handler.get_error_count(PipelineStage.FILTER, "filter-1") == 1
        assert handler.get_total_errors() == 1

        # Handle second error for same component
        handler.handle_error(
            "event-2", PipelineStage.FILTER, "filter-1", ValueError("Error 2")
        )
        assert handler.get_error_count(PipelineStage.FILTER, "filter-1") == 2
        assert handler.get_total_errors() == 2

        # Handle error for different component
        handler.handle_error(
            "event-3", PipelineStage.OUTPUT, "output-1", ValueError("Error 3")
        )
        assert handler.get_error_count(PipelineStage.FILTER, "filter-1") == 2
        assert handler.get_error_count(PipelineStage.OUTPUT, "output-1") == 1
        assert handler.get_total_errors() == 3

    def test_last_error_tracking(self) -> None:
        """Test last error tracking."""
        handler = ErrorHandler()

        # No last error initially
        assert handler.get_last_error(PipelineStage.FILTER, "filter-1") is None

        # Handle error
        exception = ValueError("Test error")
        handler.handle_error(
            "event-1", PipelineStage.FILTER, "filter-1", exception
        )

        last_error = handler.get_last_error(PipelineStage.FILTER, "filter-1")
        assert last_error is not None
        assert last_error.event_id == "event-1"
        assert last_error.error_type == "ValueError"
        assert last_error.exception == exception

    async def test_should_retry_continue_strategy(self) -> None:
        """Test retry logic with continue strategy."""
        handler = ErrorHandler(strategy=ErrorHandlingStrategy.CONTINUE)

        should_retry = await handler.should_retry(
            PipelineStage.FILTER, "filter-1", ValueError("Test")
        )
        assert should_retry is False

    async def test_should_retry_retry_strategy(self) -> None:
        """Test retry logic with retry strategy."""
        handler = ErrorHandler(strategy=ErrorHandlingStrategy.RETRY, max_retries=2)

        # Should retry for network errors
        should_retry = await handler.should_retry(
            PipelineStage.OUTPUT, "output-1", OSError("Network error")
        )
        assert should_retry is True

        # Should not retry for other errors
        should_retry = await handler.should_retry(
            PipelineStage.OUTPUT, "output-1", ValueError("Value error")
        )
        assert should_retry is False

    async def test_execute_with_retry_success(self) -> None:
        """Test successful operation execution."""
        handler = ErrorHandler(strategy=ErrorHandlingStrategy.RETRY)

        async def successful_operation() -> str:
            return "success"

        result = await handler.execute_with_retry(
            PipelineStage.OUTPUT, "output-1", successful_operation
        )
        assert result == "success"

    async def test_execute_with_retry_eventual_success(self) -> None:
        """Test operation that succeeds after retries."""
        handler = ErrorHandler(
            strategy=ErrorHandlingStrategy.RETRY,
            max_retries=2,
            retry_delay_seconds=0.01,
        )

        call_count = 0

        async def flaky_operation() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OSError("Temporary failure")
            return "success"

        result = await handler.execute_with_retry(
            PipelineStage.OUTPUT, "output-1", flaky_operation
        )
        assert result == "success"
        assert call_count == 2

    async def test_execute_with_retry_failure(self) -> None:
        """Test operation that fails after all retries."""
        handler = ErrorHandler(
            strategy=ErrorHandlingStrategy.RETRY,
            max_retries=1,
            retry_delay_seconds=0.01,
        )

        async def failing_operation() -> str:
            raise OSError("Persistent failure")

        with pytest.raises(OSError, match="Persistent failure"):
            await handler.execute_with_retry(
                PipelineStage.OUTPUT, "output-1", failing_operation
            )

    def test_error_summary(self) -> None:
        """Test error summary generation."""
        handler = ErrorHandler()

        # Handle some errors
        handler.handle_error(
            "event-1", PipelineStage.FILTER, "filter-1", ValueError("Error 1")
        )
        handler.handle_error(
            "event-2", PipelineStage.OUTPUT, "output-1", OSError("Error 2")
        )

        summary = handler.get_error_summary()

        assert summary["total_errors"] == 2
        assert summary["strategy"] == "continue"
        assert "filter.filter-1" in summary["errors_by_stage"]
        assert "output.output-1" in summary["errors_by_stage"]
        assert summary["errors_by_stage"]["filter.filter-1"] == 1
        assert summary["errors_by_stage"]["output.output-1"] == 1

    def test_reset_errors(self) -> None:
        """Test error reset functionality."""
        handler = ErrorHandler()

        # Handle error
        handler.handle_error(
            "event-1", PipelineStage.FILTER, "filter-1", ValueError("Error")
        )
        assert handler.get_total_errors() == 1

        # Reset errors
        handler.reset_errors()
        assert handler.get_total_errors() == 0
        assert handler.get_error_count(PipelineStage.FILTER, "filter-1") == 0
        assert handler.get_last_error(PipelineStage.FILTER, "filter-1") is None
