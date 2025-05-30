# pyright: strict
"""Shared pytest fixtures for nwws2mqtt tests."""

from __future__ import annotations

import asyncio
import time
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from src.pipeline.errors import ErrorHandler, ErrorHandlingStrategy
from src.pipeline.filters import Filter
from src.pipeline.outputs import Output
from src.pipeline.stats import StatsCollector
from src.pipeline.transformers import Transformer
from src.pipeline.types import PipelineEvent, PipelineEventMetadata, PipelineStage


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
def mock_stats_collector() -> Mock:
    """Create mock stats collector."""
    stats_mock = Mock(spec=StatsCollector)
    stats_mock.record_processing_time = Mock()
    stats_mock.record_throughput = Mock()
    stats_mock.stats = Mock()
    stats_mock.stats.get_summary = Mock(return_value={"processed": 10})
    return stats_mock


@pytest.fixture
def error_handler() -> ErrorHandler:
    """Create error handler with continue strategy."""
    return ErrorHandler(strategy=ErrorHandlingStrategy.CONTINUE)


@pytest.fixture
def retry_error_handler() -> ErrorHandler:
    """Create error handler with retry strategy."""
    return ErrorHandler(
        strategy=ErrorHandlingStrategy.RETRY,
        max_retries=2,
        retry_delay_seconds=0.01,
    )


@pytest.fixture
@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
