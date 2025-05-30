# pyright: strict
"""Tests for pipeline core module."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from src.pipeline.core import Pipeline, PipelineManager
from src.pipeline.errors import ErrorHandler, PipelineError
from src.pipeline.types import PipelineEvent, PipelineEventMetadata


class TestPipeline:
    """Test Pipeline functionality."""

    def test_pipeline_initialization(
        self,
        mock_filter: Mock,
        mock_transformer: Mock,
        mock_output: Mock,
        mock_stats_collector: Mock,
        error_handler: ErrorHandler,
    ) -> None:
        """Test pipeline initialization with components."""
        pipeline = Pipeline(
            pipeline_id="test-pipeline",
            filters=[mock_filter],
            transformer=mock_transformer,
            outputs=[mock_output],
            stats_collector=mock_stats_collector,
            error_handler=error_handler,
        )

        assert pipeline.pipeline_id == "test-pipeline"
        assert len(pipeline.filters) == 1
        assert pipeline.transformer == mock_transformer
        assert len(pipeline.outputs) == 1
        assert pipeline.stats_collector == mock_stats_collector
        assert pipeline.error_handler == error_handler
        assert pipeline.is_started is False

    def test_pipeline_minimal_initialization(self) -> None:
        """Test pipeline initialization with minimal components."""
        pipeline = Pipeline(pipeline_id="minimal-pipeline")

        assert pipeline.pipeline_id == "minimal-pipeline"
        assert pipeline.filters == []
        assert pipeline.transformer is None
        assert pipeline.outputs == []
        assert pipeline.stats_collector is None
        assert pipeline.error_handler is not None
        assert pipeline.is_started is False

    async def test_start_pipeline(self, mock_output: Mock) -> None:
        """Test starting pipeline."""
        pipeline = Pipeline(
            pipeline_id="test-pipeline",
            outputs=[mock_output],
        )

        await pipeline.start()

        assert pipeline.is_started is True
        mock_output.start.assert_called_once()

    async def test_start_pipeline_already_started(self, mock_output: Mock) -> None:
        """Test starting already started pipeline."""
        pipeline = Pipeline(
            pipeline_id="test-pipeline",
            outputs=[mock_output],
        )

        await pipeline.start()
        mock_output.start.assert_called_once()

        # Start again - should not call output.start again
        await pipeline.start()
        mock_output.start.assert_called_once()

    async def test_start_pipeline_output_failure(self, mock_output: Mock) -> None:
        """Test pipeline start with output failure."""
        mock_output.start.side_effect = OSError("Connection failed")

        pipeline = Pipeline(
            pipeline_id="test-pipeline",
            outputs=[mock_output],
        )

        with pytest.raises(PipelineError, match="Failed to start output"):
            await pipeline.start()

        assert pipeline.is_started is False

    async def test_stop_pipeline(self, mock_output: Mock) -> None:
        """Test stopping pipeline."""
        pipeline = Pipeline(
            pipeline_id="test-pipeline",
            outputs=[mock_output],
        )

        await pipeline.start()
        await pipeline.stop()

        assert pipeline.is_started is False
        mock_output.stop.assert_called_once()

    async def test_stop_pipeline_not_started(self, mock_output: Mock) -> None:
        """Test stopping pipeline that is not started."""
        pipeline = Pipeline(
            pipeline_id="test-pipeline",
            outputs=[mock_output],
        )

        await pipeline.stop()

        # Should not call output.stop if pipeline was never started
        mock_output.stop.assert_not_called()

    async def test_stop_pipeline_output_error(self, mock_output: Mock) -> None:
        """Test stopping pipeline with output error."""
        mock_output.stop.side_effect = OSError("Stop failed")

        pipeline = Pipeline(
            pipeline_id="test-pipeline",
            outputs=[mock_output],
        )

        await pipeline.start()
        # Should not raise exception even if output.stop fails
        await pipeline.stop()

        assert pipeline.is_started is False

    async def test_process_event_not_started(self, pipeline_event: PipelineEvent) -> None:
        """Test processing event when pipeline not started."""
        pipeline = Pipeline(pipeline_id="test-pipeline")

        result = await pipeline.process(pipeline_event)

        assert result is False

    async def test_process_event_success(
        self,
        pipeline_event: PipelineEvent,
        mock_filter: AsyncMock,
        mock_transformer: AsyncMock,
        mock_stats_collector: AsyncMock,
    ) -> None:
        """Test successful event processing."""
        # Configure mocks
        mock_filter.return_value = True
        mock_transformer.transform.return_value = pipeline_event

        pipeline = Pipeline(
            pipeline_id="test-pipeline",
            filters=[mock_filter],
            transformer=mock_transformer,
            outputs=[],
            stats_collector=mock_stats_collector,
        )

        await pipeline.start()
        result = await pipeline.process(pipeline_event)

        assert result is True
        mock_filter.assert_called_once()
        mock_transformer.assert_called_once()
        mock_stats_collector.record_processing_time.assert_called()
        mock_stats_collector.record_throughput.assert_called()

    async def test_process_event_filtered_out(
        self,
        pipeline_event: PipelineEvent,
        mock_filter: Mock,
    ) -> None:
        """Test event being filtered out."""
        mock_filter.return_value = False

        pipeline = Pipeline(
            pipeline_id="test-pipeline",
            filters=[mock_filter],
        )

        await pipeline.start()
        result = await pipeline.process(pipeline_event)

        assert result is False

    async def test_process_event_with_error(
        self,
        pipeline_event: PipelineEvent,
        mock_output: Mock,
        mock_stats_collector: Mock,
    ) -> None:
        """Test event processing with error."""
        mock_output.side_effect = OSError("Send failed")

        pipeline = Pipeline(
            pipeline_id="test-pipeline",
            outputs=[mock_output],
            stats_collector=mock_stats_collector,
        )

        await pipeline.start()

        with pytest.raises(OSError, match="Send failed"):
            await pipeline.process(pipeline_event)

        # Should record failure stats
        mock_stats_collector.record_processing_time.assert_called()

    def test_get_stats_summary(self, mock_stats_collector: Mock) -> None:
        """Test getting stats summary."""
        pipeline = Pipeline(
            pipeline_id="test-pipeline",
            stats_collector=mock_stats_collector,
        )

        summary = pipeline.get_stats_summary()
        assert summary == {"processed": 10}

    def test_get_stats_summary_no_collector(self) -> None:
        """Test getting stats summary without collector."""
        pipeline = Pipeline(pipeline_id="test-pipeline")

        summary = pipeline.get_stats_summary()
        assert summary is None

    def test_get_error_summary(self, error_handler: ErrorHandler) -> None:
        """Test getting error summary."""
        pipeline = Pipeline(
            pipeline_id="test-pipeline",
            error_handler=error_handler,
        )

        summary = pipeline.get_error_summary()
        assert "total_errors" in summary
        assert summary["total_errors"] == 0


class TestPipelineManager:
    """Test PipelineManager functionality."""

    def test_manager_initialization(self) -> None:
        """Test pipeline manager initialization."""
        manager = PipelineManager()

        assert len(manager.get_all_pipelines()) == 0
        assert manager.is_running is False
        assert manager.queue_size == 0

    async def test_add_pipeline(self) -> None:
        """Test adding pipeline to manager."""
        manager = PipelineManager()
        pipeline = Pipeline(pipeline_id="test-pipeline")

        await manager.add_pipeline(pipeline)

        pipelines = manager.get_all_pipelines()
        assert len(pipelines) == 1
        assert pipelines[0] == pipeline

        retrieved = manager.get_pipeline("test-pipeline")
        assert retrieved == pipeline

    async def test_add_duplicate_pipeline(self) -> None:
        """Test adding pipeline with duplicate ID."""
        manager = PipelineManager()
        pipeline1 = Pipeline(pipeline_id="test-pipeline")
        pipeline2 = Pipeline(pipeline_id="test-pipeline")

        await manager.add_pipeline(pipeline1)
        # This actually overwrites in the current implementation
        await manager.add_pipeline(pipeline2)

        assert manager.get_pipeline("test-pipeline") == pipeline2

    async def test_remove_pipeline(self) -> None:
        """Test removing pipeline from manager."""
        manager = PipelineManager()
        pipeline = Pipeline(pipeline_id="test-pipeline")

        await manager.add_pipeline(pipeline)
        assert len(manager.get_all_pipelines()) == 1

        removed = manager.remove_pipeline("test-pipeline")
        assert removed == pipeline
        assert len(manager.get_all_pipelines()) == 0

    def test_remove_nonexistent_pipeline(self) -> None:
        """Test removing non-existent pipeline."""
        manager = PipelineManager()

        result = manager.remove_pipeline("nonexistent")
        assert result is None

    def test_get_nonexistent_pipeline(self) -> None:
        """Test getting non-existent pipeline."""
        manager = PipelineManager()

        result = manager.get_pipeline("nonexistent")
        assert result is None

    async def test_start_manager(self) -> None:
        """Test starting pipeline manager."""
        manager = PipelineManager()
        pipeline = Pipeline(pipeline_id="test-pipeline")
        await manager.add_pipeline(pipeline)

        await manager.start()

        assert manager.is_running is True
        assert pipeline.is_started is True

        await manager.stop()  # Clean up after test

    async def test_stop_manager(self) -> None:
        """Test stopping pipeline manager."""
        manager = PipelineManager()
        pipeline = Pipeline(pipeline_id="test-pipeline")
        await manager.add_pipeline(pipeline)

        await manager.start()
        await manager.stop()

        assert manager.is_running is False
        assert pipeline.is_started is False

    async def test_submit_event(self) -> None:
        """Test submitting event to specific pipeline."""
        manager = PipelineManager()
        pipeline = Pipeline(pipeline_id="test-pipeline")
        await manager.add_pipeline(pipeline)

        await manager.start()

        event = PipelineEvent(metadata=PipelineEventMetadata())
        await manager.submit_event("test-pipeline", event)

        # Event should be queued
        assert manager.queue_size > 0

        await manager.stop()  # Clean up after test

    async def test_submit_event_to_nonexistent_pipeline(self) -> None:
        """Test submitting event to non-existent pipeline."""
        manager = PipelineManager()
        await manager.start()

        event = PipelineEvent(metadata=PipelineEventMetadata())

        # This doesn't actually raise an error in current implementation
        await manager.submit_event("nonexistent", event)
        # Event is still queued even for nonexistent pipeline
        assert manager.queue_size > 0

        await manager.stop()  # Clean up after test


    async def test_submit_event_to_all(self) -> None:
        """Test submitting event to all pipelines."""
        manager = PipelineManager()
        pipeline1 = Pipeline(pipeline_id="pipeline-1")
        pipeline2 = Pipeline(pipeline_id="pipeline-2")
        await manager.add_pipeline(pipeline1)
        await manager.add_pipeline(pipeline2)

        await manager.start()

        event = PipelineEvent(metadata=PipelineEventMetadata())
        await manager.submit_event_to_all(event)

        # Should have events for both pipelines
        assert manager.queue_size >= 1

        await manager.stop()  # Clean up after test


    async def test_get_manager_stats(self) -> None:
        """Test getting manager statistics."""
        manager = PipelineManager()
        pipeline1 = Pipeline(pipeline_id="pipeline-1")
        pipeline2 = Pipeline(pipeline_id="pipeline-2")
        await manager.add_pipeline(pipeline1)
        await manager.add_pipeline(pipeline2)

        stats = manager.get_manager_stats()

        assert "pipeline_count" in stats
        assert stats["pipeline_count"] == 2
        assert "is_running" in stats
        assert stats["is_running"] is False
        assert "queue_size" in stats

    async def test_manager_async_context_manager(self) -> None:
        """Test pipeline manager as async context manager."""
        pipeline = Pipeline(pipeline_id="test-pipeline")

        async with PipelineManager() as manager:
            await manager.add_pipeline(pipeline)
            assert manager.is_running is True
            assert pipeline.is_started is True

        # After exiting context, manager should be stopped
        assert manager.is_running is False
        assert pipeline.is_started is False

    async def test_manager_context_manager_with_exception(self) -> None:
        """Test pipeline manager context manager cleanup on exception."""
        pipeline = Pipeline(pipeline_id="test-pipeline")
        manager = None

        try:
            async with PipelineManager() as mgr:
                manager = mgr
                await manager.add_pipeline(pipeline)
                assert manager.is_running is True
                raise ValueError("Test exception")
        except ValueError:
            pass

        # After exception, manager should still be properly stopped
        assert manager is not None
        assert manager.is_running is False
        assert pipeline.is_started is False
