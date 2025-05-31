# pyright: standard
"""Test module for DuplicateFilter."""

from __future__ import annotations

import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from nwws.filters.duplicate_filter import DuplicateFilter
from nwws.models.events import NoaaPortEventData
from nwws.pipeline import PipelineEvent, PipelineEventMetadata, PipelineStage


@pytest.fixture
def test_event_metadata() -> PipelineEventMetadata:
    """Create test event metadata."""
    return PipelineEventMetadata(
        event_id="test-event-123",
        timestamp=time.time(),
        source="test-source",
        stage=PipelineStage.FILTER,
        trace_id="trace-123",
        custom={"test": "data"},
    )


@pytest.fixture
def test_event_with_id(test_event_metadata: PipelineEventMetadata) -> NoaaPortEventData:
    """Create event with product ID."""
    return NoaaPortEventData(
        metadata=test_event_metadata,
        awipsid="AFDBOX",
        cccc="KBOX",
        id="SXUS44KBOX121200",
        issue=datetime.fromisoformat("2023-07-12T12:00:00+00:00"),
        noaaport="Test forecast content",
        subject="Area Forecast Discussion",
        ttaaii="SXUS44",
        delay_stamp=None,
        content_type="text/plain",
    )


@pytest.fixture
def second_event_with_same_id(test_event_metadata: PipelineEventMetadata) -> NoaaPortEventData:
    """Create second event with same product ID."""
    return NoaaPortEventData(
        metadata=test_event_metadata,
        awipsid="AFDBOX",
        cccc="KBOX",
        id="SXUS44KBOX121200",  # Same ID as test_event_with_id
        issue=datetime.fromisoformat("2023-07-12T12:01:00+00:00"),
        noaaport="Updated forecast content",
        subject="Area Forecast Discussion",
        ttaaii="SXUS44",
        delay_stamp=None,
        content_type="text/plain",
    )


@pytest.fixture
def event_with_different_id(test_event_metadata: PipelineEventMetadata) -> NoaaPortEventData:
    """Create event with different product ID."""
    return NoaaPortEventData(
        metadata=test_event_metadata,
        awipsid="AFDALY",
        cccc="KALY",
        id="SXUS44KALY121200",
        issue=datetime.fromisoformat("2023-07-12T12:00:00+00:00"),
        noaaport="Albany forecast content",
        subject="Area Forecast Discussion",
        ttaaii="SXUS44",
        delay_stamp=None,
        content_type="text/plain",
    )


@pytest.fixture
def event_without_id(test_event_metadata: PipelineEventMetadata) -> PipelineEvent:
    """Create event without id attribute."""
    return PipelineEvent(metadata=test_event_metadata)


class TestDuplicateFilter:
    """Test cases for DuplicateFilter."""

    def test_init_default_values(self) -> None:
        """Test filter initialization with default values."""
        filter_instance = DuplicateFilter()
        assert filter_instance.filter_id == "duplicate-filter"
        assert filter_instance.window_seconds == 300.0
        assert filter_instance._seen_products == {}

    def test_init_custom_values(self) -> None:
        """Test filter initialization with custom values."""
        custom_id = "custom-duplicate-filter"
        custom_window = 600.0
        filter_instance = DuplicateFilter(custom_id, custom_window)
        assert filter_instance.filter_id == custom_id
        assert filter_instance.window_seconds == custom_window
        assert filter_instance._seen_products == {}

    def test_should_process_allows_first_occurrence(
        self, test_event_with_id: NoaaPortEventData
    ) -> None:
        """Test that first occurrence of product ID is allowed."""
        filter_instance = DuplicateFilter()
        result = filter_instance.should_process(test_event_with_id)
        assert result is True
        assert test_event_with_id.id in filter_instance._seen_products

    def test_should_process_rejects_duplicate_within_window(
        self, test_event_with_id: NoaaPortEventData, second_event_with_same_id: NoaaPortEventData
    ) -> None:
        """Test that duplicate product ID within window is rejected."""
        filter_instance = DuplicateFilter(window_seconds=300.0)

        # First occurrence should be allowed
        result1 = filter_instance.should_process(test_event_with_id)
        assert result1 is True

        # Second occurrence should be rejected
        result2 = filter_instance.should_process(second_event_with_same_id)
        assert result2 is False

    def test_should_process_allows_different_ids(
        self, test_event_with_id: NoaaPortEventData, event_with_different_id: NoaaPortEventData
    ) -> None:
        """Test that events with different product IDs are both allowed."""
        filter_instance = DuplicateFilter()

        result1 = filter_instance.should_process(test_event_with_id)
        result2 = filter_instance.should_process(event_with_different_id)

        assert result1 is True
        assert result2 is True
        assert len(filter_instance._seen_products) == 2

    def test_should_process_allows_event_without_id(
        self, event_without_id: PipelineEvent
    ) -> None:
        """Test that events without id attribute are allowed through."""
        filter_instance = DuplicateFilter()
        result = filter_instance.should_process(event_without_id)
        assert result is True
        assert len(filter_instance._seen_products) == 0

    def test_should_process_handles_empty_id(
        self, test_event_metadata: PipelineEventMetadata
    ) -> None:
        """Test handling when id is empty string."""
        event = NoaaPortEventData(
            metadata=test_event_metadata,
            awipsid="AFDBOX",
            cccc="KBOX",
            id="",  # Empty ID
            issue=datetime.fromisoformat("2023-07-12T12:00:00+00:00"),
            noaaport="Test content",
            subject="Test Subject",
            ttaaii="SXUS44",
            delay_stamp=None,
            content_type="text/plain",
        )

        filter_instance = DuplicateFilter()
        result = filter_instance.should_process(event)
        assert result is True
        assert len(filter_instance._seen_products) == 0

    def test_should_process_handles_none_id(self) -> None:
        """Test handling when id is None."""
        event = MagicMock()
        event.id = None
        event.metadata = MagicMock()
        event.metadata.event_id = "test-123"

        filter_instance = DuplicateFilter()
        result = filter_instance.should_process(event)
        assert result is True
        assert len(filter_instance._seen_products) == 0

    def test_should_process_handles_non_string_id(self) -> None:
        """Test handling when id is not a string."""
        event = MagicMock()
        event.id = 12345  # Non-string ID
        event.metadata = MagicMock()
        event.metadata.event_id = "test-123"

        filter_instance = DuplicateFilter()
        result = filter_instance.should_process(event)
        assert result is True
        assert len(filter_instance._seen_products) == 0

    @patch("time.time")
    def test_cleanup_expired_entries(
        self, mock_time: MagicMock, test_event_with_id: NoaaPortEventData
    ) -> None:
        """Test that expired entries are cleaned up."""
        initial_time = 1000.0
        mock_time.return_value = initial_time

        filter_instance = DuplicateFilter(window_seconds=300.0)

        # Process first event
        filter_instance.should_process(test_event_with_id)
        assert len(filter_instance._seen_products) == 1

        # Move time forward beyond window
        mock_time.return_value = initial_time + 400.0

        # Process another event to trigger cleanup
        event2 = NoaaPortEventData(
            metadata=test_event_with_id.metadata,
            awipsid="AFDALY",
            cccc="KALY",
            id="DIFFERENT_ID",
            issue=datetime.fromisoformat("2023-07-12T12:00:00+00:00"),
            noaaport="Test content",
            subject="Test Subject",
            ttaaii="SXUS44",
            delay_stamp=None,
            content_type="text/plain",
        )

        filter_instance.should_process(event2)

        # Original entry should be cleaned up, only new one remains
        assert len(filter_instance._seen_products) == 1
        assert "DIFFERENT_ID" in filter_instance._seen_products
        assert test_event_with_id.id not in filter_instance._seen_products

    @patch("time.time")
    def test_allows_same_id_after_window_expires(
        self, mock_time: MagicMock, test_event_with_id: NoaaPortEventData
    ) -> None:
        """Test that same product ID is allowed after window expires."""
        initial_time = 1000.0
        mock_time.return_value = initial_time

        filter_instance = DuplicateFilter(window_seconds=300.0)

        # First occurrence
        result1 = filter_instance.should_process(test_event_with_id)
        assert result1 is True

        # Move time forward beyond window
        mock_time.return_value = initial_time + 400.0

        # Same ID should now be allowed again
        result2 = filter_instance.should_process(test_event_with_id)
        assert result2 is True

    def test_get_cache_stats_empty_cache(self) -> None:
        """Test cache stats with empty cache."""
        filter_instance = DuplicateFilter()
        stats = filter_instance.get_cache_stats()

        assert stats["total_tracked"] == 0
        assert stats["window_seconds"] == 300.0
        assert stats["oldest_entry_age"] == 0.0

    def test_get_cache_stats_with_entries(
        self, test_event_with_id: NoaaPortEventData, event_with_different_id: NoaaPortEventData
    ) -> None:
        """Test cache stats with entries."""
        filter_instance = DuplicateFilter(window_seconds=300.0)

        # Add some entries
        filter_instance.should_process(test_event_with_id)
        time.sleep(0.1)  # Small delay to ensure different timestamps
        filter_instance.should_process(event_with_different_id)

        stats = filter_instance.get_cache_stats()

        assert stats["total_tracked"] == 2
        assert stats["window_seconds"] == 300.0
        assert stats["oldest_entry_age"] >= 0.1

    @patch("time.time")
    def test_multiple_cleanup_cycles(
        self, mock_time: MagicMock, test_event_with_id: NoaaPortEventData
    ) -> None:
        """Test multiple cleanup cycles work correctly."""
        mock_time.return_value = 1000.0
        filter_instance = DuplicateFilter(window_seconds=200.0)  # Longer window to prevent cleanup during addition

        # Add multiple entries at different times
        events = []
        for i in range(5):
            mock_time.return_value = 1000.0 + (i * 30)  # 30 second intervals
            event = NoaaPortEventData(
                metadata=test_event_with_id.metadata,
                awipsid=f"AFDTEST{i}",
                cccc="KTEST",
                id=f"TEST_ID_{i}",
                issue=datetime.fromisoformat("2023-07-12T12:00:00+00:00"),
                noaaport="Test content",
                subject="Test Subject",
                ttaaii="SXUS44",
                delay_stamp=None,
                content_type="text/plain",
            )
            events.append(event)
            filter_instance.should_process(event)

        assert len(filter_instance._seen_products) == 5

        # Move time forward to expire first 3 entries (added at 1000, 1030, 1060)
        # With window of 200s, they expire at 1200, 1230, 1260
        mock_time.return_value = 1270.0  # Should expire first 3 entries

        # Trigger cleanup by processing new event
        new_event = NoaaPortEventData(
            metadata=test_event_with_id.metadata,
            awipsid="AFDNEW",
            cccc="KNEW",
            id="NEW_ID",
            issue=datetime.fromisoformat("2023-07-12T12:00:00+00:00"),
            noaaport="New content",
            subject="New Subject",
            ttaaii="SXUS44",
            delay_stamp=None,
            content_type="text/plain",
        )

        filter_instance.should_process(new_event)

        # Should have 3 entries: last 2 original (at 1090, 1120) + new one
        assert len(filter_instance._seen_products) == 3

    def test_concurrent_same_id_processing(
        self, test_event_with_id: NoaaPortEventData, second_event_with_same_id: NoaaPortEventData
    ) -> None:
        """Test rapid processing of same ID."""
        filter_instance = DuplicateFilter(window_seconds=1.0)  # Short window

        # Process same ID multiple times rapidly
        results = []
        for _ in range(5):
            results.append(filter_instance.should_process(test_event_with_id))

        # First should pass, rest should fail
        assert results[0] is True
        assert all(result is False for result in results[1:])

    def test_window_boundary_conditions(
        self, test_event_with_id: NoaaPortEventData
    ) -> None:
        """Test behavior at window boundaries."""
        filter_instance = DuplicateFilter(window_seconds=0.1)  # Very short window

        # First occurrence
        result1 = filter_instance.should_process(test_event_with_id)
        assert result1 is True

        # Wait exactly window duration
        time.sleep(0.11)

        # Should be allowed now
        result2 = filter_instance.should_process(test_event_with_id)
        assert result2 is True
