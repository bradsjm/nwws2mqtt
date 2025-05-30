# pyright: strict
"""Tests for TestMessageFilter."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from nwws.filters.test_msg_filter import TestMessageFilter
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
def test_message_event(test_event_metadata: PipelineEventMetadata) -> NoaaPortEventData:
    """Create event with TSTMSG awipsid."""
    return NoaaPortEventData(
        metadata=test_event_metadata,
        awipsid="TSTMSG",
        cccc="KTEST",
        id="TEST123",
        issue="2023-07-12T12:00:00Z",
        noaaport="Test message content",
        subject="Test Message",
        ttaaii="TEST01",
        delay_stamp=None,
    )


@pytest.fixture
def normal_event(test_event_metadata: PipelineEventMetadata) -> NoaaPortEventData:
    """Create event with normal awipsid."""
    return NoaaPortEventData(
        metadata=test_event_metadata,
        awipsid="AFDBOX",
        cccc="KBOX",
        id="SXUS44KBOX121200",
        issue="2023-07-12T12:00:00Z",
        noaaport="Normal forecast content",
        subject="Area Forecast Discussion",
        ttaaii="SXUS44",
        delay_stamp=None,
    )


@pytest.fixture
def event_without_awipsid(test_event_metadata: PipelineEventMetadata) -> PipelineEvent:
    """Create event without awipsid attribute."""
    return PipelineEvent(metadata=test_event_metadata)


class TestTestMessageFilter:
    """Test cases for TestMessageFilter."""

    def test_init_default_id(self) -> None:
        """Test filter initialization with default ID."""
        filter_instance = TestMessageFilter()
        assert filter_instance.filter_id == "test-msg-filter"

    def test_init_custom_id(self) -> None:
        """Test filter initialization with custom ID."""
        custom_id = "custom-test-filter"
        filter_instance = TestMessageFilter(custom_id)
        assert filter_instance.filter_id == custom_id

    def test_should_process_rejects_test_message(
        self, test_message_event: NoaaPortEventData
    ) -> None:
        """Test that events with awipsid='TSTMSG' are rejected."""
        filter_instance = TestMessageFilter()
        result = filter_instance.should_process(test_message_event)
        assert result is False

    def test_should_process_rejects_test_message_case_insensitive(
        self, test_event_metadata: PipelineEventMetadata
    ) -> None:
        """Test that 'tstmsg' (lowercase) is also rejected."""
        event = NoaaPortEventData(
            metadata=test_event_metadata,
            awipsid="tstmsg",
            cccc="KTEST",
            id="TEST123",
            issue="2023-07-12T12:00:00Z",
            noaaport="Test message content",
            subject="Test Message",
            ttaaii="TEST01",
            delay_stamp=None,
        )
        
        filter_instance = TestMessageFilter()
        result = filter_instance.should_process(event)
        assert result is False

    def test_should_process_rejects_mixed_case_test_message(
        self, test_event_metadata: PipelineEventMetadata
    ) -> None:
        """Test that 'TstMsg' (mixed case) is also rejected."""
        event = NoaaPortEventData(
            metadata=test_event_metadata,
            awipsid="TstMsg",
            cccc="KTEST",
            id="TEST123",
            issue="2023-07-12T12:00:00Z",
            noaaport="Test message content",
            subject="Test Message",
            ttaaii="TEST01",
            delay_stamp=None,
        )
        
        filter_instance = TestMessageFilter()
        result = filter_instance.should_process(event)
        assert result is False

    def test_should_process_allows_normal_message(
        self, normal_event: NoaaPortEventData
    ) -> None:
        """Test that normal events are allowed through."""
        filter_instance = TestMessageFilter()
        result = filter_instance.should_process(normal_event)
        assert result is True

    def test_should_process_allows_event_without_awipsid(
        self, event_without_awipsid: PipelineEvent
    ) -> None:
        """Test that events without awipsid attribute are allowed through."""
        filter_instance = TestMessageFilter()
        result = filter_instance.should_process(event_without_awipsid)
        assert result is True

    def test_should_process_handles_none_awipsid(
        self, test_event_metadata: PipelineEventMetadata
    ) -> None:
        """Test handling when awipsid is None."""
        # Create a mock event with awipsid set to None
        event = MagicMock()
        event.awipsid = None
        
        filter_instance = TestMessageFilter()
        result = filter_instance.should_process(event)
        assert result is True

    def test_should_process_handles_empty_awipsid(
        self, test_event_metadata: PipelineEventMetadata
    ) -> None:
        """Test handling when awipsid is empty string."""
        event = NoaaPortEventData(
            metadata=test_event_metadata,
            awipsid="",
            cccc="KTEST",
            id="TEST123",
            issue="2023-07-12T12:00:00Z",
            noaaport="Test message content",
            subject="Test Message",
            ttaaii="TEST01",
            delay_stamp=None,
        )
        
        filter_instance = TestMessageFilter()
        result = filter_instance.should_process(event)
        assert result is True

    def test_should_process_handles_non_string_awipsid(
        self, test_event_metadata: PipelineEventMetadata
    ) -> None:
        """Test handling when awipsid is not a string."""
        # Create a mock event with awipsid as integer
        event = MagicMock()
        event.awipsid = 12345
        
        filter_instance = TestMessageFilter()
        result = filter_instance.should_process(event)
        assert result is True

    def test_should_process_allows_partial_match(
        self, test_event_metadata: PipelineEventMetadata
    ) -> None:
        """Test that partial matches like 'TSTMSG123' are allowed."""
        event = NoaaPortEventData(
            metadata=test_event_metadata,
            awipsid="TSTMSG123",
            cccc="KTEST",
            id="TEST123",
            issue="2023-07-12T12:00:00Z",
            noaaport="Test message content",
            subject="Test Message",
            ttaaii="TEST01",
            delay_stamp=None,
        )
        
        filter_instance = TestMessageFilter()
        result = filter_instance.should_process(event)
        assert result is True

    def test_should_process_allows_substring_match(
        self, test_event_metadata: PipelineEventMetadata
    ) -> None:
        """Test that substrings like 'MYTSTMSG' are allowed."""
        event = NoaaPortEventData(
            metadata=test_event_metadata,
            awipsid="MYTSTMSG",
            cccc="KTEST",
            id="TEST123",
            issue="2023-07-12T12:00:00Z",
            noaaport="Test message content",
            subject="Test Message",
            ttaaii="TEST01",
            delay_stamp=None,
        )
        
        filter_instance = TestMessageFilter()
        result = filter_instance.should_process(event)
        assert result is True