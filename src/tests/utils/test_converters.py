# pyright: strict
"""Tests for converter functions."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock

from nwws.models.weather import (
    HVTECModel,
    TextProductModel,
    TextProductSegmentModel,
    UGCModel,
    VTECModel,
)
from nwws.utils.converters import (
    convert_hvtec_to_model,
    convert_text_product_segment_to_model,
    convert_text_product_to_model,
    convert_ugc_to_model,
    convert_vtec_to_model,
)


class TestConvertUGCToModel:
    """Test convert_ugc_to_model function."""

    def test_convert_ugc_basic_attributes(self) -> None:
        """Test conversion with basic UGC attributes."""
        mock_ugc = MagicMock()
        mock_ugc.state = "NY"
        mock_ugc.geoclass = "C"
        mock_ugc.number = 123
        mock_ugc.name = "Test County"
        mock_ugc.wfos = ["KALY", "KBGM"]

        result = convert_ugc_to_model(mock_ugc)

        assert isinstance(result, UGCModel)
        assert result.state == "NY"
        assert result.geoclass == "C"
        assert result.number == 123
        assert result.name == "Test County"
        assert result.wfos == ["KALY", "KBGM"]

    def test_convert_ugc_missing_attributes(self) -> None:
        """Test conversion with missing UGC attributes uses defaults."""
        mock_ugc = MagicMock()
        # Remove all attributes to test getattr defaults
        del mock_ugc.state
        del mock_ugc.geoclass
        del mock_ugc.number
        del mock_ugc.name
        del mock_ugc.wfos

        result = convert_ugc_to_model(mock_ugc)

        assert isinstance(result, UGCModel)
        assert result.state == ""
        assert result.geoclass == ""
        assert result.number == 0
        assert result.name == ""
        assert result.wfos == []

    def test_convert_ugc_empty_wfos(self) -> None:
        """Test conversion with empty wfos list."""
        mock_ugc = MagicMock()
        mock_ugc.state = "CA"
        mock_ugc.geoclass = "Z"
        mock_ugc.number = 456
        mock_ugc.name = "Test Zone"
        mock_ugc.wfos = []

        result = convert_ugc_to_model(mock_ugc)

        assert isinstance(result, UGCModel)
        assert result.wfos == []


class TestConvertVTECToModel:
    """Test convert_vtec_to_model function."""

    def test_convert_vtec_basic_attributes(self) -> None:
        """Test conversion with basic VTEC attributes."""
        mock_vtec = MagicMock()
        mock_vtec.line = "/O.NEW.KALY.TO.W.0001.230712T1800Z-230712T2000Z/"
        mock_vtec.status = "O"
        mock_vtec.action = "NEW"
        mock_vtec.office = "ALY"
        mock_vtec.office4 = "KALY"
        mock_vtec.phenomena = "TO"
        mock_vtec.significance = "W"
        mock_vtec.etn = 1
        mock_vtec.year = 2023

        result = convert_vtec_to_model(mock_vtec)

        assert isinstance(result, VTECModel)
        assert result.line == "/O.NEW.KALY.TO.W.0001.230712T1800Z-230712T2000Z/"
        assert result.status == "O"
        assert result.action == "NEW"
        assert result.office == "ALY"
        assert result.office4 == "KALY"
        assert result.phenomena == "TO"
        assert result.significance == "W"
        assert result.etn == 1
        assert result.year == 2023

    def test_convert_vtec_missing_attributes(self) -> None:
        """Test conversion with missing VTEC attributes uses defaults."""
        mock_vtec = MagicMock()
        # Remove attributes to test getattr defaults
        del mock_vtec.line
        del mock_vtec.status
        del mock_vtec.action
        del mock_vtec.office
        del mock_vtec.office4
        del mock_vtec.phenomena
        del mock_vtec.significance
        del mock_vtec.etn
        del mock_vtec.year

        result = convert_vtec_to_model(mock_vtec)

        assert isinstance(result, VTECModel)
        assert result.line == ""
        assert result.status == ""
        assert result.action == ""
        assert result.office == ""
        assert result.office4 == ""
        assert result.phenomena == ""
        assert result.significance == ""
        assert result.etn == 0
        assert result.year == 0


class TestConvertHVTECToModel:
    """Test convert_hvtec_to_model function."""

    def test_convert_hvtec_basic_attributes(self) -> None:
        """Test conversion with basic HVTEC attributes."""
        mock_nwsli = MagicMock()
        mock_nwsli.id = "ALBR6"

        mock_hvtec = MagicMock()
        mock_hvtec.line = "/ALBR6.1.ER.230712T1800Z.230712T2000Z.230712T1900Z.NO/"
        mock_hvtec.nwsli = mock_nwsli
        mock_hvtec.severity = "1"
        mock_hvtec.cause = "ER"
        mock_hvtec.beginTS = datetime.datetime(2023, 7, 12, 18, 0, 0)
        mock_hvtec.crestTS = datetime.datetime(2023, 7, 12, 19, 0, 0)
        mock_hvtec.endTS = datetime.datetime(2023, 7, 12, 20, 0, 0)
        mock_hvtec.record = "NO"

        result = convert_hvtec_to_model(mock_hvtec)

        assert isinstance(result, HVTECModel)
        assert result.line == "/ALBR6.1.ER.230712T1800Z.230712T2000Z.230712T1900Z.NO/"
        assert result.nwsli_id == "ALBR6"
        assert result.severity == "1"
        assert result.cause == "ER"
        assert result.beginTS == datetime.datetime(2023, 7, 12, 18, 0, 0)
        assert result.crestTS == datetime.datetime(2023, 7, 12, 19, 0, 0)
        assert result.endTS == datetime.datetime(2023, 7, 12, 20, 0, 0)
        assert result.record == "NO"

    def test_convert_hvtec_nwsli_as_string(self) -> None:
        """Test conversion when nwsli is a string instead of object."""
        mock_hvtec = MagicMock()
        mock_hvtec.line = "/ALBR6.1.ER.230712T1800Z.230712T2000Z.230712T1900Z.NO/"
        mock_hvtec.nwsli = "ALBR6"  # String instead of object
        mock_hvtec.severity = "1"
        mock_hvtec.cause = "ER"
        mock_hvtec.beginTS = None
        mock_hvtec.crestTS = None
        mock_hvtec.endTS = None
        mock_hvtec.record = "NO"

        result = convert_hvtec_to_model(mock_hvtec)

        assert isinstance(result, HVTECModel)
        assert result.nwsli_id == "ALBR6"

    def test_convert_hvtec_missing_nwsli(self) -> None:
        """Test conversion with missing nwsli attribute."""
        mock_hvtec = MagicMock()
        mock_hvtec.line = ""
        mock_hvtec.nwsli = None
        mock_hvtec.severity = ""
        mock_hvtec.cause = ""
        mock_hvtec.beginTS = None
        mock_hvtec.crestTS = None
        mock_hvtec.endTS = None
        mock_hvtec.record = ""

        result = convert_hvtec_to_model(mock_hvtec)

        assert isinstance(result, HVTECModel)
        assert result.nwsli_id == ""

    def test_convert_hvtec_missing_attributes(self) -> None:
        """Test conversion with missing HVTEC attributes uses defaults."""
        mock_hvtec = MagicMock()
        # Remove attributes to test getattr defaults
        del mock_hvtec.line
        del mock_hvtec.nwsli
        del mock_hvtec.severity
        del mock_hvtec.cause
        del mock_hvtec.beginTS
        del mock_hvtec.crestTS
        del mock_hvtec.endTS
        del mock_hvtec.record

        result = convert_hvtec_to_model(mock_hvtec)

        assert isinstance(result, HVTECModel)
        assert result.line == ""
        assert result.nwsli_id == ""
        assert result.severity == ""
        assert result.cause == ""
        assert result.beginTS is None
        assert result.crestTS is None
        assert result.endTS is None
        assert result.record == ""


class TestConvertTextProductSegmentToModel:
    """Test convert_text_product_segment_to_model function."""

    def test_convert_segment_basic_attributes(self) -> None:
        """Test conversion with basic segment attributes."""
        mock_ugc = MagicMock()
        mock_ugc.state = "NY"
        mock_ugc.geoclass = "C"
        mock_ugc.number = 123
        mock_ugc.name = "Test County"
        mock_ugc.wfos = ["KALY"]

        mock_hvtec = MagicMock()
        mock_hvtec.line = "/ALBR6.1.ER/"
        mock_hvtec.nwsli = "ALBR6"
        mock_hvtec.severity = "1"
        mock_hvtec.cause = "ER"
        mock_hvtec.beginTS = None
        mock_hvtec.crestTS = None
        mock_hvtec.endTS = None
        mock_hvtec.record = "NO"

        mock_segment = MagicMock()
        mock_segment.unixtext = "This is test segment text."
        mock_segment.ugcs = [mock_ugc]
        mock_segment.ugcexpire = datetime.datetime(2023, 7, 12, 20, 0, 0)
        mock_segment.headlines = ["TORNADO WARNING"]
        mock_segment.hvtec = [mock_hvtec]
        mock_segment.tml_giswkt = "POINT(-73.75 42.65)"
        mock_segment.tml_valid = datetime.datetime(2023, 7, 12, 18, 0, 0)
        mock_segment.tml_sknt = 35
        mock_segment.tml_dir = 270
        mock_segment.giswkt = "POLYGON((-73.8 42.6, -73.7 42.6, -73.7 42.7, -73.8 42.7, -73.8 42.6))"
        mock_segment.windtag = "65 MPH"
        mock_segment.windtagunits = "MPH"
        mock_segment.windthreat = "RADAR INDICATED"
        mock_segment.hailtag = "1.00 IN"
        mock_segment.haildirtag = "WEST"
        mock_segment.hailthreat = "RADAR INDICATED"
        mock_segment.winddirtag = "WEST"
        mock_segment.tornadotag = "RADAR INDICATED"
        mock_segment.waterspouttag = None
        mock_segment.landspouttag = None
        mock_segment.damagetag = "CONSIDERABLE"
        mock_segment.squalltag = None
        mock_segment.flood_tags = {"dam": "LEVEE", "source": "RADAR"}
        mock_segment.is_emergency = True
        mock_segment.is_pds = False
        mock_segment.bullets = ["* TORNADO CONFIRMED", "* TAKE COVER NOW"]

        result = convert_text_product_segment_to_model(mock_segment)

        assert isinstance(result, TextProductSegmentModel)
        assert result.unixtext == "This is test segment text."
        assert len(result.ugcs) == 1
        assert result.ugcs[0].state == "NY"
        assert result.ugcexpire == datetime.datetime(2023, 7, 12, 20, 0, 0)
        assert result.headlines == ["TORNADO WARNING"]
        assert len(result.hvtec) == 1
        assert result.hvtec[0].nwsli_id == "ALBR6"
        assert result.is_emergency is True
        assert result.is_pds is False
        assert len(result.bullets) == 2

    def test_convert_segment_empty_collections(self) -> None:
        """Test conversion with empty collections."""
        mock_segment = MagicMock()
        mock_segment.unixtext = ""
        mock_segment.ugcs = []
        mock_segment.ugcexpire = None
        mock_segment.headlines = []
        mock_segment.hvtec = []
        mock_segment.tml_giswkt = None
        mock_segment.tml_valid = None
        mock_segment.tml_sknt = None
        mock_segment.tml_dir = None
        mock_segment.giswkt = None
        mock_segment.windtag = None
        mock_segment.windtagunits = None
        mock_segment.windthreat = None
        mock_segment.hailtag = None
        mock_segment.haildirtag = None
        mock_segment.hailthreat = None
        mock_segment.winddirtag = None
        mock_segment.tornadotag = None
        mock_segment.waterspouttag = None
        mock_segment.landspouttag = None
        mock_segment.damagetag = None
        mock_segment.squalltag = None
        mock_segment.flood_tags = {}
        mock_segment.is_emergency = False
        mock_segment.is_pds = False
        mock_segment.bullets = []

        result = convert_text_product_segment_to_model(mock_segment)

        assert isinstance(result, TextProductSegmentModel)
        assert result.ugcs == []
        assert result.headlines == []
        assert result.hvtec == []
        assert result.bullets == []

    def test_convert_segment_missing_attributes(self) -> None:
        """Test conversion with missing segment attributes uses defaults."""
        mock_segment = MagicMock()
        # Remove most attributes to test getattr defaults
        del mock_segment.unixtext
        del mock_segment.ugcs
        del mock_segment.ugcexpire
        del mock_segment.headlines
        del mock_segment.hvtec
        # Ensure all optional attributes are properly handled
        for attr in [
            "tml_giswkt", "tml_valid", "tml_sknt", "tml_dir", "giswkt",
            "windtag", "windtagunits", "windthreat", "hailtag", "haildirtag",
            "hailthreat", "winddirtag", "tornadotag", "waterspouttag",
            "landspouttag", "damagetag", "squalltag", "flood_tags",
            "is_emergency", "is_pds", "bullets"
        ]:
            delattr(mock_segment, attr)

        result = convert_text_product_segment_to_model(mock_segment)

        assert isinstance(result, TextProductSegmentModel)
        assert result.unixtext == ""
        assert result.ugcs == []
        assert result.headlines == []
        assert result.hvtec == []


class TestConvertTextProductToModel:
    """Test convert_text_product_to_model function."""

    def test_convert_product_basic_attributes(self) -> None:
        """Test conversion with basic product attributes."""
        mock_product = MagicMock()
        mock_product.text = "TORNADO WARNING TEXT"
        mock_product.warnings = ["Warning 1", "Warning 2"]
        mock_product.source = "KALY"
        mock_product.wmo = "WFUS51"
        mock_product.ddhhmm = "121200"
        mock_product.bbb = None
        mock_product.valid = datetime.datetime(2023, 7, 12, 12, 0, 0)
        mock_product.wmo_valid = datetime.datetime(2023, 7, 12, 12, 0, 0)
        mock_product.utcnow = datetime.datetime(2023, 7, 12, 12, 0, 0)
        mock_product.z = "Z"
        mock_product.afos = "TORALY"
        mock_product.sections = ["SECTION1", "SECTION2"]
        mock_product.segments = []
        mock_product.geometry = None
        mock_product.get_product_id.return_value = "202307121200-KALY-WFUS51-TORALY"
        mock_product.get_nicedate.return_value = "July 12, 2023 12:00 PM UTC"
        mock_product.get_main_headline.return_value = "TORNADO WARNING"
        mock_product.get_signature.return_value = "Forecaster Smith"
        mock_product.get_channels.return_value = ["TORALY"]
        mock_product.is_correction.return_value = False
        mock_product.is_resent.return_value = False
        mock_product.parse_attn_wfo.return_value = ["ALY", "BGM"]
        mock_product.parse_attn_rfc.return_value = []

        result = convert_text_product_to_model(mock_product)

        assert isinstance(result, TextProductModel)
        assert result.text == "TORNADO WARNING TEXT"
        assert result.warnings == ["Warning 1", "Warning 2"]
        assert result.source == "KALY"
        assert result.afos == "TORALY"
        assert result.sections == ["SECTION1", "SECTION2"]
        assert result.product_id == "202307121200-KALY-WFUS51-TORALY"
        assert result.nicedate == "July 12, 2023 12:00 PM UTC"
        assert result.main_headline == "TORNADO WARNING"
        assert result.signature == "Forecaster Smith"
        assert result.channels == ["TORALY"]
        assert result.is_correction is False
        assert result.is_resent is False
        assert result.attn_wfo == ["ALY", "BGM"]
        assert result.attn_rfc == []

    def test_convert_product_missing_required_for_id(self) -> None:
        """Test conversion when required attributes for product_id are missing."""
        mock_product = MagicMock()
        mock_product.text = "TEXT"
        mock_product.warnings = []
        mock_product.source = None  # Missing required for ID
        mock_product.wmo = None  # Missing required for ID
        mock_product.ddhhmm = None
        mock_product.bbb = None
        mock_product.valid = None  # Missing required for ID
        mock_product.wmo_valid = None
        mock_product.utcnow = datetime.datetime(2023, 7, 12, 12, 0, 0)  # Required field
        mock_product.z = None
        mock_product.afos = None  # Missing required for ID
        mock_product.sections = []
        mock_product.segments = []
        mock_product.geometry = None
        # get_product_id should not be called due to missing attributes
        mock_product.get_nicedate.return_value = None
        mock_product.get_main_headline.return_value = ""
        mock_product.get_signature.return_value = None
        mock_product.get_channels.return_value = []
        mock_product.is_correction.return_value = None
        mock_product.is_resent.return_value = None
        mock_product.parse_attn_wfo.return_value = []
        mock_product.parse_attn_rfc.return_value = []

        result = convert_text_product_to_model(mock_product)

        assert isinstance(result, TextProductModel)
        assert result.product_id is None

    def test_convert_product_method_exceptions(self) -> None:
            """Test conversion when product methods raise exceptions."""
            # Use MagicMock and configure methods to raise exceptions
            mock_product = MagicMock()
            mock_product.text = "TEXT"
            mock_product.warnings = []
            mock_product.source = "KALY"
            mock_product.wmo = "WFUS51"
            mock_product.ddhhmm = "121200"
            mock_product.bbb = None
            mock_product.valid = datetime.datetime(2023, 7, 12, 12, 0, 0)
            mock_product.wmo_valid = None
            mock_product.utcnow = datetime.datetime(2023, 7, 12, 12, 0, 0)
            mock_product.z = None
            mock_product.afos = "TORALY"
            mock_product.sections = []
            mock_product.segments = []
            mock_product.geometry = None

            mock_product.get_product_id.side_effect = ValueError("Test error")
            mock_product.get_nicedate.side_effect = Exception("Test error")
            mock_product.get_main_headline.side_effect = Exception("Test error")
            mock_product.get_signature.side_effect = Exception("Test error")
            mock_product.get_channels.side_effect = Exception("Test error")
            mock_product.is_correction.side_effect = Exception("Test error")
            mock_product.is_resent.side_effect = Exception("Test error")
            mock_product.parse_attn_wfo.side_effect = Exception("Test error")
            mock_product.parse_attn_rfc.side_effect = Exception("Test error")

            result = convert_text_product_to_model(mock_product)

            assert isinstance(result, TextProductModel)
            assert result.product_id is None
            assert result.nicedate is None
            assert result.main_headline == ""
            assert result.signature is None
            assert result.channels == []
            assert result.is_correction is None
            assert result.is_resent is None
            assert result.attn_wfo == []
            assert result.attn_rfc == []

    def test_convert_product_missing_afos_for_channels(self) -> None:
        """Test conversion when afos is None but get_channels exists."""
        mock_product = MagicMock()
        mock_product.text = "TEXT"
        mock_product.warnings = []
        mock_product.source = "KALY"
        mock_product.wmo = "WFUS51"
        mock_product.ddhhmm = "121200"
        mock_product.bbb = None
        mock_product.valid = datetime.datetime(2023, 7, 12, 12, 0, 0)
        mock_product.wmo_valid = None
        mock_product.utcnow = datetime.datetime(2023, 7, 12, 12, 0, 0)  # Required field
        mock_product.z = None
        mock_product.afos = None  # No afos
        mock_product.sections = []
        mock_product.segments = []
        mock_product.geometry = None
        mock_product.get_product_id.return_value = "TEST-ID"
        mock_product.get_nicedate.return_value = None
        mock_product.get_main_headline.return_value = ""
        mock_product.get_signature.return_value = None
        mock_product.get_channels.return_value = ["CHANNEL1"]  # This should not be called
        mock_product.is_correction.return_value = None
        mock_product.is_resent.return_value = None
        mock_product.parse_attn_wfo.return_value = []
        mock_product.parse_attn_rfc.return_value = []

        result = convert_text_product_to_model(mock_product)

        assert isinstance(result, TextProductModel)
        assert result.channels == []  # Should be empty due to missing afos
