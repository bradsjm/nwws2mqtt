# pyright: standard
"""Integration tests for transformers and filters working together."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from nwws.filters.test_msg_filter import TestMessageFilter
from nwws.models.events import NoaaPortEventData, TextProductEventData
from nwws.pipeline import PipelineEventMetadata, PipelineStage
from nwws.transformers import NoaaPortTransformer


@pytest.fixture
def sample_noaaport_text() -> str:
    """Sample NOAAPort formatted text for testing."""
    return """SXUS44 KBOX 121200
AFDBOX

Area Forecast Discussion
National Weather Service Boston MA
800 AM EDT Wed Jul 12 2023

.SYNOPSIS...High pressure will remain in control through the
weekend providing generally fair weather conditions.

$$

Forecaster Smith
"""


@pytest.fixture
def normal_noaaport_event(sample_noaaport_text: str) -> NoaaPortEventData:
    """Create normal NoaaPortEventData that should pass filter."""
    metadata = PipelineEventMetadata(
        event_id="normal-event-123",
        timestamp=time.time(),
        source="test-source",
        stage=PipelineStage.INGEST,
        trace_id="trace-123",
        custom={"test": "data"},
    )

    return NoaaPortEventData(
        metadata=metadata,
        awipsid="AFDBOX",
        cccc="KBOX",
        id="SXUS44KBOX121200",
        issue="2023-07-12T12:00:00Z",
        noaaport=sample_noaaport_text,
        subject="Area Forecast Discussion",
        ttaaii="SXUS44",
        delay_stamp=None,
    )


@pytest.fixture
def test_message_noaaport_event(sample_noaaport_text: str) -> NoaaPortEventData:
    """Create test message NoaaPortEventData that should be filtered out."""
    metadata = PipelineEventMetadata(
        event_id="test-event-456",
        timestamp=time.time(),
        source="test-source",
        stage=PipelineStage.INGEST,
        trace_id="trace-456",
        custom={"test": "data"},
    )

    return NoaaPortEventData(
        metadata=metadata,
        awipsid="TSTMSG",
        cccc="KTEST",
        id="TSTMSGTEST121200",
        issue="2023-07-12T12:00:00Z",
        noaaport=sample_noaaport_text,
        subject="Test Message",
        ttaaii="TSTMSG",
        delay_stamp=None,
    )


class TestTransformerFilterIntegration:
    """Integration tests for transformers and filters."""

    @patch("nwws.transformers.noaa_port_transformer.parser")
    @patch("nwws.transformers.noaa_port_transformer.convert_text_product_to_model")
    def test_normal_event_passes_filter_and_transforms(
        self,
        mock_convert: MagicMock,
        mock_parser: MagicMock,
        normal_noaaport_event: NoaaPortEventData,
    ) -> None:
        """Test that normal events pass filter and get transformed."""
        # Setup mocks
        mock_parsed_product = MagicMock()
        mock_parser.return_value = mock_parsed_product
        mock_product_model = MagicMock()
        mock_convert.return_value = mock_product_model

        # Create filter and transformer
        test_filter = TestMessageFilter()
        transformer = NoaaPortTransformer()

        # Event should pass filter
        should_process = test_filter.should_process(normal_noaaport_event)
        assert should_process is True

        # Since it passes filter, we can transform it
        transformed_event = transformer.transform(normal_noaaport_event)

        # Verify transformation worked
        assert isinstance(transformed_event, TextProductEventData)
        assert transformed_event.awipsid == "AFDBOX"
        assert transformed_event.product == mock_product_model

    def test_test_message_filtered_out(
        self, test_message_noaaport_event: NoaaPortEventData
    ) -> None:
        """Test that test messages are filtered out and not transformed."""
        # Create filter and transformer
        test_filter = TestMessageFilter()
        transformer = NoaaPortTransformer()

        # Event should be filtered out
        should_process = test_filter.should_process(test_message_noaaport_event)
        assert should_process is False

        # In a real pipeline, this event would not reach the transformer
        # But if it did reach the transformer, it would still transform
        # (since the transformer's job is just transformation, not filtering)
        with patch("nwws.transformers.noaa_port_transformer.parser") as mock_parser:
            with patch("nwws.transformers.noaa_port_transformer.convert_text_product_to_model") as mock_convert:
                mock_parser.return_value = MagicMock()
                mock_convert.return_value = MagicMock()

                transformed_event = transformer.transform(test_message_noaaport_event)
                assert isinstance(transformed_event, TextProductEventData)
                assert transformed_event.awipsid == "TSTMSG"

    def test_pipeline_sequence_simulation(
        self, normal_noaaport_event: NoaaPortEventData
    ) -> None:
        """Simulate a complete pipeline sequence: filter then transform."""
        # Create pipeline components
        test_filter = TestMessageFilter()
        transformer = NoaaPortTransformer()

        events_to_process = [normal_noaaport_event]
        processed_events = []

        with patch("nwws.transformers.noaa_port_transformer.parser") as mock_parser:
            with patch("nwws.transformers.noaa_port_transformer.convert_text_product_to_model") as mock_convert:
                mock_parser.return_value = MagicMock()
                mock_convert.return_value = MagicMock()

                # Simulate pipeline processing
                for event in events_to_process:
                    # First apply filter
                    if test_filter.should_process(event):
                        # If passes filter, apply transformer
                        transformed_event = transformer.transform(event)
                        processed_events.append(transformed_event)

        # Verify results
        assert len(processed_events) == 1
        assert isinstance(processed_events[0], TextProductEventData)
        assert processed_events[0].awipsid == "AFDBOX"

    def test_test_message_filtered_out_in_pipeline(
        self, test_message_noaaport_event: NoaaPortEventData
    ) -> None:
        """Test that test messages are filtered out in pipeline simulation."""
        # Create pipeline components
        test_filter = TestMessageFilter()
        transformer = NoaaPortTransformer()

        events_to_process = [test_message_noaaport_event]
        processed_events = []

        # Simulate pipeline processing
        for event in events_to_process:
            # First apply filter
            if test_filter.should_process(event):
                # If passes filter, apply transformer
                transformed_event = transformer.transform(event)
                processed_events.append(transformed_event)

        # Verify that no events were processed (filtered out)
        assert len(processed_events) == 0

    def test_mixed_events_pipeline(
        self,
        normal_noaaport_event: NoaaPortEventData,
        test_message_noaaport_event: NoaaPortEventData,
    ) -> None:
        """Test pipeline with mixed normal and test events."""
        # Create pipeline components
        test_filter = TestMessageFilter()
        transformer = NoaaPortTransformer()

        events_to_process = [normal_noaaport_event, test_message_noaaport_event]
        processed_events = []

        with patch("nwws.transformers.noaa_port_transformer.parser") as mock_parser:
            with patch("nwws.transformers.noaa_port_transformer.convert_text_product_to_model") as mock_convert:
                mock_parser.return_value = MagicMock()
                mock_convert.return_value = MagicMock()

                # Simulate pipeline processing
                for event in events_to_process:
                    # First apply filter
                    if test_filter.should_process(event):
                        # If passes filter, apply transformer
                        transformed_event = transformer.transform(event)
                        processed_events.append(transformed_event)

        # Verify results - only normal event should be processed
        assert len(processed_events) == 1
        assert isinstance(processed_events[0], TextProductEventData)
        assert processed_events[0].awipsid == "AFDBOX"
