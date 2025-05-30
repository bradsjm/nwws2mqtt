# pyright: strict
"""Tests for NoaaPortTransformer."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

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

.NEAR TERM /THROUGH TONIGHT/...
Mostly sunny skies expected today with temperatures reaching
the upper 70s to lower 80s across the region.

$$

Forecaster Smith
"""


@pytest.fixture
def noaaport_event_data(sample_noaaport_text: str) -> NoaaPortEventData:
    """Create test NoaaPortEventData."""
    metadata = PipelineEventMetadata(
        event_id="test-event-123",
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
def non_noaaport_event() -> TextProductEventData:
    """Create test event that is not NoaaPortEventData."""
    metadata = PipelineEventMetadata(
        event_id="test-event-456",
        timestamp=time.time(),
        source="test-source",
        stage=PipelineStage.TRANSFORM,
        trace_id="trace-456",
        custom={},
    )
    
    return TextProductEventData(
        metadata=metadata,
        awipsid="TESTMSG",
        cccc="KTEST",
        id="TEST123",
        issue="2023-07-12T12:00:00Z",
        product=MagicMock(),
        subject="Test Message",
        ttaaii="TEST01",
        delay_stamp=None,
    )


class TestNoaaPortTransformer:
    """Test cases for NoaaPortTransformer."""

    def test_init_default_id(self) -> None:
        """Test transformer initialization with default ID."""
        transformer = NoaaPortTransformer()
        assert transformer.transformer_id == "noaaport"

    def test_init_custom_id(self) -> None:
        """Test transformer initialization with custom ID."""
        custom_id = "custom-noaaport-transformer"
        transformer = NoaaPortTransformer(custom_id)
        assert transformer.transformer_id == custom_id

    @patch("nwws.transformers.noaa_port_transformer.parser")
    @patch("nwws.transformers.noaa_port_transformer.convert_text_product_to_model")
    def test_transform_noaaport_event(
        self,
        mock_convert: MagicMock,
        mock_parser: MagicMock,
        noaaport_event_data: NoaaPortEventData,
    ) -> None:
        """Test transformation of NoaaPortEventData."""
        # Setup mocks
        mock_parsed_product = MagicMock()
        mock_parser.return_value = mock_parsed_product
        mock_product_model = MagicMock()
        mock_convert.return_value = mock_product_model
        
        transformer = NoaaPortTransformer()
        result = transformer.transform(noaaport_event_data)
        
        # Verify parser was called with correct parameters
        mock_parser.assert_called_once_with(
            text=noaaport_event_data.noaaport,
            ugc_provider={},
        )
        
        # Verify convert_text_product_to_model was called
        mock_convert.assert_called_once_with(mock_parsed_product)
        
        # Verify result is TextProductEventData
        assert isinstance(result, TextProductEventData)
        assert result.product == mock_product_model
        
        # Verify metadata is updated correctly
        assert result.metadata.event_id == noaaport_event_data.metadata.event_id
        assert result.metadata.source == "noaaport"
        assert result.metadata.stage == PipelineStage.TRANSFORM
        assert result.metadata.trace_id == noaaport_event_data.metadata.trace_id
        
        # Verify original data is preserved
        assert result.awipsid == noaaport_event_data.awipsid
        assert result.cccc == noaaport_event_data.cccc
        assert result.id == noaaport_event_data.id
        assert result.issue == noaaport_event_data.issue
        assert result.subject == noaaport_event_data.subject
        assert result.ttaaii == noaaport_event_data.ttaaii
        assert result.delay_stamp == noaaport_event_data.delay_stamp

    def test_transform_non_noaaport_event_passthrough(
        self, non_noaaport_event: TextProductEventData
    ) -> None:
        """Test that non-NoaaPortEventData events pass through unchanged."""
        transformer = NoaaPortTransformer()
        result = transformer.transform(non_noaaport_event)
        
        # Should return the same event unchanged
        assert result is non_noaaport_event
        assert isinstance(result, TextProductEventData)
        assert result.metadata.event_id == non_noaaport_event.metadata.event_id

    @patch("nwws.transformers.noaa_port_transformer.parser")
    def test_transform_parser_exception(
        self,
        mock_parser: MagicMock,
        noaaport_event_data: NoaaPortEventData,
    ) -> None:
        """Test handling of parser exceptions."""
        mock_parser.side_effect = ValueError("Invalid text format")
        
        transformer = NoaaPortTransformer()
        
        with pytest.raises(ValueError, match="Invalid text format"):
            transformer.transform(noaaport_event_data)

    @patch("nwws.transformers.noaa_port_transformer.parser")
    @patch("nwws.transformers.noaa_port_transformer.convert_text_product_to_model")
    def test_transform_convert_exception(
        self,
        mock_convert: MagicMock,
        mock_parser: MagicMock,
        noaaport_event_data: NoaaPortEventData,
    ) -> None:
        """Test handling of convert_text_product_to_model exceptions."""
        mock_parser.return_value = MagicMock()
        mock_convert.side_effect = AttributeError("Missing attribute")
        
        transformer = NoaaPortTransformer()
        
        with pytest.raises(AttributeError, match="Missing attribute"):
            transformer.transform(noaaport_event_data)

    @patch("nwws.transformers.noaa_port_transformer.parser")
    @patch("nwws.transformers.noaa_port_transformer.convert_text_product_to_model")
    def test_custom_metadata_preserved(
        self,
        mock_convert: MagicMock,
        mock_parser: MagicMock,
        noaaport_event_data: NoaaPortEventData,
    ) -> None:
        """Test that custom metadata is preserved during transformation."""
        # Setup mocks
        mock_parser.return_value = MagicMock()
        mock_convert.return_value = MagicMock()
        
        # Add custom metadata
        noaaport_event_data.metadata.custom["custom_field"] = "custom_value"
        
        transformer = NoaaPortTransformer()
        result = transformer.transform(noaaport_event_data)
        
        # Verify custom metadata is preserved
        assert result.metadata.custom["custom_field"] == "custom_value"
        assert result.metadata.custom["test"] == "data"