# pyright: strict
"""Tests for pipeline types module."""

from __future__ import annotations

import time

import pytest

from src.pipeline.types import PipelineEvent, PipelineEventMetadata, PipelineStage


class TestPipelineEventMetadata:
    """Test PipelineEventMetadata functionality."""

    def test_default_values(self) -> None:
        """Test metadata creation with default values."""
        metadata = PipelineEventMetadata()
        
        assert metadata.event_id is not None
        assert len(metadata.event_id) > 0
        assert metadata.timestamp > 0
        assert metadata.source == "unknown"
        assert metadata.stage == PipelineStage.INGEST
        assert metadata.trace_id is None
        assert metadata.custom == {}

    def test_custom_values(self) -> None:
        """Test metadata creation with custom values."""
        custom_data = {"key": "value", "number": 42}
        timestamp = time.time()
        
        metadata = PipelineEventMetadata(
            event_id="test-123",
            timestamp=timestamp,
            source="test-source",
            stage=PipelineStage.TRANSFORM,
            trace_id="trace-456",
            custom=custom_data,
        )
        
        assert metadata.event_id == "test-123"
        assert metadata.timestamp == timestamp
        assert metadata.source == "test-source"
        assert metadata.stage == PipelineStage.TRANSFORM
        assert metadata.trace_id == "trace-456"
        assert metadata.custom == custom_data

    def test_immutable(self) -> None:
        """Test that metadata is immutable."""
        metadata = PipelineEventMetadata(event_id="test")
        
        with pytest.raises(AttributeError):
            metadata.event_id = "changed"  # type: ignore[misc]


class TestPipelineEvent:
    """Test PipelineEvent functionality."""

    def test_creation(self) -> None:
        """Test event creation."""
        metadata = PipelineEventMetadata(event_id="test-event")
        event = PipelineEvent(metadata=metadata)
        
        assert event.metadata == metadata
        assert event.metadata.event_id == "test-event"

    def test_with_stage(self) -> None:
        """Test creating event copy with new stage."""
        original_metadata = PipelineEventMetadata(
            event_id="test-event",
            source="original-source",
            stage=PipelineStage.INGEST,
            custom={"original": "data"},
        )
        original_event = PipelineEvent(metadata=original_metadata)
        
        # Create copy with new stage
        new_event = original_event.with_stage(PipelineStage.FILTER, "filter-source")
        
        # Original event should be unchanged
        assert original_event.metadata.stage == PipelineStage.INGEST
        assert original_event.metadata.source == "original-source"
        
        # New event should have updated metadata
        assert new_event.metadata.event_id == "test-event"  # Same event ID
        assert new_event.metadata.stage == PipelineStage.FILTER
        assert new_event.metadata.source == "filter-source"
        assert new_event.metadata.timestamp > original_metadata.timestamp
        assert new_event.metadata.custom == {"original": "data"}  # Custom data copied
        
        # Should be different instances
        assert new_event is not original_event
        assert new_event.metadata is not original_event.metadata

    def test_with_stage_default_source(self) -> None:
        """Test with_stage preserves original source when not specified."""
        metadata = PipelineEventMetadata(source="original-source")
        event = PipelineEvent(metadata=metadata)
        
        new_event = event.with_stage(PipelineStage.OUTPUT)
        
        assert new_event.metadata.source == "original-source"
        assert new_event.metadata.stage == PipelineStage.OUTPUT


class TestPipelineStage:
    """Test PipelineStage enum."""

    def test_stage_values(self) -> None:
        """Test stage enum values."""
        assert PipelineStage.INGEST.value == "ingest"
        assert PipelineStage.FILTER.value == "filter"
        assert PipelineStage.TRANSFORM.value == "transform"
        assert PipelineStage.OUTPUT.value == "output"

    def test_stage_comparison(self) -> None:
        """Test stage comparison."""
        assert PipelineStage.INGEST == PipelineStage.INGEST
        assert PipelineStage.INGEST != PipelineStage.FILTER