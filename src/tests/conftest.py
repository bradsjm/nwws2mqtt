# pyright: strict
"""Shared pytest fixtures for nwws2mqtt tests."""

from __future__ import annotations

import asyncio
import time
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from nwws.metrics.collectors import MetricsCollector
from nwws.metrics.registry import MetricRegistry
from nwws.pipeline.errors import PipelineErrorHandler, ErrorHandlingStrategy
from nwws.pipeline.filters import Filter
from nwws.pipeline.outputs import Output
from nwws.pipeline.transformers import Transformer
from nwws.pipeline.types import PipelineEvent, PipelineEventMetadata, PipelineStage


@pytest.fixture
def metric_registry() -> MetricRegistry:
    """Create a new metric registry for testing."""
    return MetricRegistry()


@pytest.fixture
def metrics_collector(metric_registry: MetricRegistry) -> MetricsCollector:
    """Create a metrics collector for testing."""
    return MetricsCollector(registry=metric_registry, prefix="test")


@pytest.fixture
def event_metadata() -> PipelineEventMetadata:
    """Create test event metadata."""
    return PipelineEventMetadata(
        event_id="test-event-123",
        timestamp=time.time(),
        source="test-source",
        stage=PipelineStage.INGEST,
        trace_id="trace-123",
        custom={"test": "data"},
    )


@pytest.fixture
def pipeline_event(event_metadata: PipelineEventMetadata) -> PipelineEvent:
    """Create test pipeline event."""
    return PipelineEvent(metadata=event_metadata)


@pytest.fixture
def mock_filter() -> MagicMock:
    """Create mock filter."""
    filter_mock = MagicMock(spec=Filter)
    filter_mock.filter_id = "test-filter"
    filter_mock.should_process = Mock(return_value=True)
    filter_mock.return_value = True
    return filter_mock


@pytest.fixture
def mock_transformer() -> Mock:
    """Create mock transformer."""
    transformer_mock = Mock(spec=Transformer)
    transformer_mock.transformer_id = "test-transformer"
    transformer_mock.transform = AsyncMock(side_effect=lambda event: event)  # type: ignore[no-untyped-def, misc]
    return transformer_mock


@pytest.fixture
def mock_output() -> MagicMock:
    """Create mock output."""
    output_mock = MagicMock(spec=Output)
    output_mock.output_id = "test-output"
    output_mock.start = AsyncMock()
    output_mock.stop = AsyncMock()
    output_mock.send = AsyncMock()
    return output_mock


@pytest.fixture
def metrics_mock() -> Mock:
    """Create mock metrics collector."""
    collector_mock = Mock(spec=MetricsCollector)
    collector_mock.record_operation = Mock()
    collector_mock.record_duration_ms = Mock()
    collector_mock.record_error = Mock()
    collector_mock.increment_counter = Mock()
    collector_mock.set_gauge = Mock()
    collector_mock.observe_histogram = Mock()
    collector_mock.update_status = Mock()
    return collector_mock


@pytest.fixture
def mock_stats_collector() -> Mock:
    """Create mock pipeline stats collector."""
    from nwws.pipeline.stats import PipelineStatsCollector

    stats_mock = Mock(spec=PipelineStatsCollector)
    stats_mock.record_processing_time = Mock()
    stats_mock.record_throughput = Mock()
    stats_mock.record_queue_size = Mock()
    stats_mock.record_error = Mock()
    stats_mock.update_stage_status = Mock()
    stats_mock.get_summary = Mock(return_value={"processed": 10})
    return stats_mock


@pytest.fixture
def error_handler() -> PipelineErrorHandler:
    """Create error handler with continue strategy."""
    return PipelineErrorHandler(strategy=ErrorHandlingStrategy.CONTINUE)


@pytest.fixture
def retry_error_handler() -> PipelineErrorHandler:
    """Create error handler with retry strategy."""
    return PipelineErrorHandler(
        strategy=ErrorHandlingStrategy.RETRY,
        max_retries=2,
        retry_delay_seconds=0.01,
    )


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
