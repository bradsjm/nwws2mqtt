"""Tests for MQTT topic structure logic."""

from datetime import datetime
from unittest.mock import MagicMock

from nwws.models.events import TextProductEventData
from nwws.models.weather import TextProductModel, TextProductSegmentModel, VTECModel
from nwws.outputs.mqtt import MQTTOutput, MQTTConfig
from nwws.pipeline import PipelineEventMetadata
from nwws.utils import build_topic


from typing import List, Optional, Dict, TypedDict

class TestMQTTTopicStructure:
    """Test MQTT topic structure construction."""

    config: MQTTConfig
    mqtt_output: MQTTOutput

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.config = MQTTConfig(
            mqtt_broker="localhost",
            mqtt_topic_prefix="nwws"
        )
        self.mqtt_output = MQTTOutput("test", config=self.config)

    def create_mock_event(
            self,
            cccc: str = "KALY",
            awipsid: Optional[str] = "TORALY",
            product_id: str = "test-id",
            vtec_records: Optional[List[VTECModel]] = None
        ) -> TextProductEventData:
            """Create a mock TextProductEventData for testing."""
            # Create mock product
            mock_product = MagicMock(spec=TextProductModel)
            mock_product.segments = []

            if vtec_records:
                mock_segment = MagicMock(spec=TextProductSegmentModel)
                mock_segment.vtec = vtec_records
                mock_product.segments = [mock_segment]

            # Create event metadata
            metadata = PipelineEventMetadata(
                event_id="test-event-123",
                timestamp=datetime(2023, 7, 13, 19, 15, 0).timestamp(),
                source="test"
            )

            # Ensure awipsid is a string for TextProductEventData constructor.
            # If the input awipsid is None, use an empty string. This maintains
            # compatibility with downstream logic that handles None or empty awipsid
            # (e.g., by defaulting to "GENERAL" or "NO_AWIPSID").
            awipsid_for_event_data = awipsid if awipsid is not None else ""

            # Create event
            return TextProductEventData(
                metadata=metadata,
                product=mock_product,
                cccc=cccc,
                awipsid=awipsid_for_event_data,
                id=product_id,
                issue=datetime(2023, 7, 13, 19, 15, 0),
                subject="Test Product",
                ttaaii="WFUS51",
                delay_stamp=None,
                content_type="text/plain",
                noaaport="Test message content"
            )

    def create_vtec_model(self, phenomena: str = "TO", significance: str = "W") -> VTECModel:
        """Create a mock VTEC model."""
        return VTECModel(
            line=f"/O.NEW.KALY.{phenomena}.{significance}.0001.230713T1915Z-230713T2000Z/",
            status="O",
            action="NEW",
            officeId="ALY",
            officeId4="KALY",
            phenomena=phenomena,
            significance=significance,
            eventTrackingNumber=1,
            beginTimestamp=datetime(2023, 7, 13, 19, 15, 0),
            endTimestamp=datetime(2023, 7, 13, 20, 0, 0),
            year=2023
        )

    def test_get_product_type_indicator_with_vtec(self) -> None:
        """Test product type indicator extraction with VTEC codes."""
        # Create VTEC records
        tornado_warning = self.create_vtec_model("TO", "W")
        severe_watch = self.create_vtec_model("SV", "A")

        # Test single VTEC
        event = self.create_mock_event(vtec_records=[tornado_warning])
        result = self.mqtt_output._get_product_type_indicator(event)  # type: ignore[protected-access]
        assert result == "TO.W"

        # Test multiple VTEC - should use first one
        event = self.create_mock_event(vtec_records=[tornado_warning, severe_watch])
        result = self.mqtt_output._get_product_type_indicator(event)  # type: ignore[protected-access]
        assert result == "TO.W"

    def test_get_product_type_indicator_without_vtec(self) -> None:
        """Test product type indicator extraction without VTEC codes."""
        # Test with standard AWIPS ID
        event = self.create_mock_event(awipsid="AFDDMX")
        result = self.mqtt_output._get_product_type_indicator(event)  # type: ignore[protected-access]
        assert result == "AFD"

        # Test with different AWIPS ID
        event = self.create_mock_event(awipsid="ZFPBOX")
        result = self.mqtt_output._get_product_type_indicator(event)  # type: ignore[protected-access]
        assert result == "ZFP"

        # Test with lowercase AWIPS ID (should be uppercase)
        event = self.create_mock_event(awipsid="nowphi")
        result = self.mqtt_output._get_product_type_indicator(event)  # type: ignore[protected-access]
        assert result == "NOW"

    def test_get_product_type_indicator_edge_cases(self) -> None:
        """Test product type indicator with edge cases."""
        # Test with short AWIPS ID
        event = self.create_mock_event(awipsid="AB")
        result = self.mqtt_output._get_product_type_indicator(event)  # type: ignore[protected-access]
        assert result == "GENERAL"

        # Test with None AWIPS ID
        event = self.create_mock_event(awipsid=None)
        result = self.mqtt_output._get_product_type_indicator(event)  # type: ignore[protected-access]
        assert result == "GENERAL"

        # Test with empty AWIPS ID
        event = self.create_mock_event(awipsid="")
        result = self.mqtt_output._get_product_type_indicator(event)  # type: ignore[protected-access]
        assert result == "GENERAL"

    def test_build_topic_with_vtec(self) -> None:
        """Test complete topic building with VTEC products."""
        tornado_warning = self.create_vtec_model("TO", "W")
        event = self.create_mock_event(
            cccc="KTBW",
            awipsid="TORALY",
            product_id="202307131915-KTBW-WFUS51-TORALY",
            vtec_records=[tornado_warning]
        )

        result = self.mqtt_output._build_topic(event)  # type: ignore[protected-access]
        expected = "nwws/KTBW/TO.W/TORALY/202307131915-KTBW-WFUS51-TORALY"
        assert result == expected

    def test_build_topic_without_vtec(self) -> None:
        """Test complete topic building without VTEC products."""
        event = self.create_mock_event(
            cccc="KDMX",
            awipsid="AFDDMX",
            product_id="202307131830-KDMX-FXUS63-AFDDMX"
        )

        result = self.mqtt_output._build_topic(event)  # type: ignore[protected-access]
        expected = "nwws/KDMX/AFD/AFDDMX/202307131830-KDMX-FXUS63-AFDDMX"
        assert result == expected

    def test_build_topic_with_missing_awipsid(self) -> None:
        """Test topic building with missing AWIPS ID."""
        event = self.create_mock_event(
            cccc="KPHI",
            awipsid=None,
            product_id="202307131700-KPHI-UNKNOWN"
        )

        result = self.mqtt_output._build_topic(event)  # type: ignore[protected-access]
        expected = "nwws/KPHI/GENERAL/NO_AWIPSID/202307131700-KPHI-UNKNOWN"
        assert result == expected

    def test_filtering_scenarios(self) -> None:
        """Test various filtering scenarios that users might want."""
        class TestCaseFilterDict(TypedDict):
            cccc: str
            awipsid: str
            vtec: Optional[List[VTECModel]]
            expected_topic: str
            filters: Dict[str, str]

        # Test data for different scenarios
        test_cases: List[TestCaseFilterDict] = [
            # Tornado Warning
            {
                "cccc": "KTBW",
                "awipsid": "TORALY",
                "vtec": [self.create_vtec_model("TO", "W")],
                "expected_topic": "nwws/KTBW/TO.W/TORALY/test-id",
                "filters": {
                    "station_all": "nwws/KTBW/#",
                    "tornado_warnings_all": "nwws/+/TO.W/#",
                    "warnings_from_station": "nwws/KTBW/+.W/#",
                    "specific_product": "nwws/KTBW/TO.W/TORALY/#"
                }
            },
            # Severe Thunderstorm Watch
            {
                "cccc": "KBOX",
                "awipsid": "SVSBOX",
                "vtec": [self.create_vtec_model("SV", "A")],
                "expected_topic": "nwws/KBOX/SV.A/SVSBOX/test-id",
                "filters": {
                    "station_all": "nwws/KBOX/#",
                    "severe_watches_all": "nwws/+/SV.A/#",
                    "watches_from_station": "nwws/KBOX/+.A/#"
                }
            },
            # Area Forecast Discussion (no VTEC)
            {
                "cccc": "KDMX",
                "awipsid": "AFDDMX",
                "vtec": None,
                "expected_topic": "nwws/KDMX/AFD/AFDDMX/test-id",
                "filters": {
                    "station_all": "nwws/KDMX/#",
                    "all_discussions": "nwws/+/AFD/#",
                    "discussions_from_station": "nwws/KDMX/AFD/#"
                }
            }
        ]

        for case in test_cases:
            event = self.create_mock_event(
                cccc=case["cccc"],
                awipsid=case["awipsid"],
                vtec_records=case["vtec"]
            )

            result = build_topic(event)  # type: ignore[protected-access]
            assert result == case["expected_topic"]

            # Verify that the topic would match expected filter patterns
            # (In real MQTT, these would be subscription patterns)
            for _filter_name, filter_pattern in case["filters"].items():
                # Basic pattern matching test (simplified)
                if filter_pattern.endswith("/#"):
                    prefix = filter_pattern[:-2]  # Remove /#
                    if "+" in prefix:
                        # For wildcard patterns, just verify structure matches
                        parts = result.split("/")
                        pattern_parts = prefix.split("/")
                        assert len(parts) >= len(pattern_parts)
                    else:
                        # For exact prefix patterns
                        assert result.startswith(prefix)

    def test_vtec_precedence_multiple_segments(self) -> None:
        """Test VTEC precedence when multiple segments exist."""
        # Create segments with different VTEC codes
        flood_advisory = self.create_vtec_model("FA", "Y")
        tornado_warning = self.create_vtec_model("TO", "W")

        # Create event with segments containing different VTEC codes
        event = self.create_mock_event(vtec_records=[flood_advisory])

        # Add another segment with tornado warning
        mock_segment2 = MagicMock(spec=TextProductSegmentModel)
        mock_segment2.vtec = [tornado_warning]
        event.product.segments.append(mock_segment2)

        # Should use the first VTEC found (flood advisory)
        result = self.mqtt_output._get_product_type_indicator(event)  # type: ignore[protected-access]
        assert result == "FA.Y"
