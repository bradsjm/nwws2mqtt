# pyright: strict
"""Tests for NoaaPortTransformer."""

from __future__ import annotations

import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from pyiem.nws.ugc import UGCProvider

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
        issue=datetime.fromisoformat("2023-07-12T12:00:00+00:00"),
        noaaport=sample_noaaport_text,
        subject="Area Forecast Discussion",
        ttaaii="SXUS44",
        delay_stamp=None,
        content_type="application/octet-stream",
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
        issue=datetime.fromisoformat("2023-07-12T12:00:00+00:00"),
        product=MagicMock(),
        subject="Test Message",
        ttaaii="TEST01",
        delay_stamp=None,
        noaaport="This is a test message that does not conform to NOAAPort format.",
        content_type="text/plain",
    )


class TestNoaaPortTransformer:
    """Test cases for NoaaPortTransformer."""

    @patch("nwws.transformers.noaa_port_transformer.create_ugc_provider")
    def test_init_default_id(self, mock_create_ugc_provider: MagicMock) -> None:
        """Test transformer initialization with default ID."""
        mock_ugc_provider = MagicMock(spec=UGCProvider)
        mock_create_ugc_provider.return_value = mock_ugc_provider

        transformer = NoaaPortTransformer()
        assert transformer.transformer_id == "noaaport"
        mock_create_ugc_provider.assert_called_once()

    @patch("nwws.transformers.noaa_port_transformer.create_ugc_provider")
    def test_init_custom_id(self, mock_create_ugc_provider: MagicMock) -> None:
        """Test transformer initialization with custom ID."""
        mock_ugc_provider = MagicMock(spec=UGCProvider)
        mock_create_ugc_provider.return_value = mock_ugc_provider

        custom_id = "custom-noaaport-transformer"
        transformer = NoaaPortTransformer(custom_id)
        assert transformer.transformer_id == custom_id
        mock_create_ugc_provider.assert_called_once()

    @patch("nwws.transformers.noaa_port_transformer.create_ugc_provider")
    def test_init_ugc_provider_failure(self, mock_create_ugc_provider: MagicMock) -> None:
        """Test transformer initialization when UGC provider creation fails."""
        mock_create_ugc_provider.side_effect = Exception("Failed to load UGC data")

        # Should not raise exception, should fallback to empty provider
        transformer = NoaaPortTransformer()
        assert transformer.transformer_id == "noaaport"

        # Should have fallback UGC provider
        ugc_provider = transformer.ugc_provider
        assert isinstance(ugc_provider, UGCProvider)

    @patch("nwws.transformers.noaa_port_transformer.create_ugc_provider")
    @patch("nwws.transformers.noaa_port_transformer.parser")
    @patch("nwws.transformers.noaa_port_transformer.convert_text_product_to_model")
    def test_transform_noaaport_event(
        self,
        mock_convert: MagicMock,
        mock_parser: MagicMock,
        mock_create_ugc_provider: MagicMock,
        noaaport_event_data: NoaaPortEventData,
    ) -> None:
        """Test transformation of NoaaPortEventData."""
        # Setup mocks
        mock_ugc_provider = MagicMock(spec=UGCProvider)
        mock_create_ugc_provider.return_value = mock_ugc_provider
        mock_parsed_product = MagicMock()
        mock_parser.return_value = mock_parsed_product
        mock_product_model = MagicMock()
        mock_convert.return_value = mock_product_model

        transformer = NoaaPortTransformer()
        result = transformer.transform(noaaport_event_data)

        # Verify parser was called with correct parameters
        mock_parser.assert_called_once_with(
            text=noaaport_event_data.noaaport,
            ugc_provider=mock_ugc_provider,
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

    @patch("nwws.transformers.noaa_port_transformer.create_ugc_provider")
    def test_transform_non_noaaport_event_passthrough(
        self, mock_create_ugc_provider: MagicMock, non_noaaport_event: TextProductEventData
    ) -> None:
        """Test that non-NoaaPortEventData events pass through unchanged."""
        mock_ugc_provider = MagicMock(spec=UGCProvider)
        mock_create_ugc_provider.return_value = mock_ugc_provider

        transformer = NoaaPortTransformer()
        result = transformer.transform(non_noaaport_event)

        # Should return the same event unchanged
        assert result is non_noaaport_event
        assert isinstance(result, TextProductEventData)
        assert result.metadata.event_id == non_noaaport_event.metadata.event_id

    @patch("nwws.transformers.noaa_port_transformer.create_ugc_provider")
    @patch("nwws.transformers.noaa_port_transformer.parser")
    def test_transform_parser_exception(
        self,
        mock_parser: MagicMock,
        mock_create_ugc_provider: MagicMock,
        noaaport_event_data: NoaaPortEventData,
    ) -> None:
        """Test handling of parser exceptions."""
        mock_ugc_provider = MagicMock(spec=UGCProvider)
        mock_create_ugc_provider.return_value = mock_ugc_provider
        mock_parser.side_effect = ValueError("Invalid text format")

        transformer = NoaaPortTransformer()

        with pytest.raises(ValueError, match="Invalid text format"):
            transformer.transform(noaaport_event_data)

    @patch("nwws.transformers.noaa_port_transformer.create_ugc_provider")
    @patch("nwws.transformers.noaa_port_transformer.parser")
    @patch("nwws.transformers.noaa_port_transformer.convert_text_product_to_model")
    def test_transform_convert_exception(
        self,
        mock_convert: MagicMock,
        mock_parser: MagicMock,
        mock_create_ugc_provider: MagicMock,
        noaaport_event_data: NoaaPortEventData,
    ) -> None:
        """Test handling of convert_text_product_to_model exceptions."""
        mock_ugc_provider = MagicMock(spec=UGCProvider)
        mock_create_ugc_provider.return_value = mock_ugc_provider
        mock_parser.return_value = MagicMock()
        mock_convert.side_effect = AttributeError("Missing attribute")

        transformer = NoaaPortTransformer()

        with pytest.raises(AttributeError, match="Missing attribute"):
            transformer.transform(noaaport_event_data)

    @patch("nwws.transformers.noaa_port_transformer.create_ugc_provider")
    @patch("nwws.transformers.noaa_port_transformer.parser")
    @patch("nwws.transformers.noaa_port_transformer.convert_text_product_to_model")
    def test_custom_metadata_preserved(
        self,
        mock_convert: MagicMock,
        mock_parser: MagicMock,
        mock_create_ugc_provider: MagicMock,
        noaaport_event_data: NoaaPortEventData,
    ) -> None:
        """Test that custom metadata is preserved during transformation."""
        # Setup mocks
        mock_ugc_provider = MagicMock(spec=UGCProvider)
        mock_create_ugc_provider.return_value = mock_ugc_provider
        mock_parser.return_value = MagicMock()
        mock_convert.return_value = MagicMock()

        # Add custom metadata
        noaaport_event_data.metadata.custom["custom_field"] = "custom_value"

        transformer = NoaaPortTransformer()
        result = transformer.transform(noaaport_event_data)

        # Verify custom metadata is preserved
        assert result.metadata.custom["custom_field"] == "custom_value"
        assert result.metadata.custom["test"] == "data"

    @patch("nwws.transformers.noaa_port_transformer.create_ugc_provider")
    def test_ugc_provider_property_lazy_initialization(
        self, mock_create_ugc_provider: MagicMock
    ) -> None:
        """Test that UGC provider property handles lazy initialization."""
        mock_ugc_provider = MagicMock(spec=UGCProvider)
        mock_create_ugc_provider.return_value = mock_ugc_provider

        # Create transformer with normal initialization first
        transformer = NoaaPortTransformer()
        
        # Reset the mock to prepare for lazy loading test
        mock_create_ugc_provider.reset_mock()

        # Access should return the provider without re-initialization
        provider = transformer.ugc_provider
        assert isinstance(provider, UGCProvider)
        # Should not call create_ugc_provider again since it's already initialized
        mock_create_ugc_provider.assert_not_called()

    @patch("nwws.transformers.noaa_port_transformer.create_ugc_provider")
    def test_ugc_provider_property_with_exception(
        self, mock_create_ugc_provider: MagicMock
    ) -> None:
        """Test UGC provider property when creation fails."""
        mock_create_ugc_provider.side_effect = Exception("UGC creation failed")

        # Transformer initialization should handle the exception
        transformer = NoaaPortTransformer()

        # Should return fallback provider even after initialization failure
        provider = transformer.ugc_provider
        assert isinstance(provider, UGCProvider)
