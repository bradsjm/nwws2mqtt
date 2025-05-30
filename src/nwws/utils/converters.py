"""Converter functions for transforming pyiem objects to Pydantic models."""

from typing import TYPE_CHECKING

from nwws.models.weather import HVTECModel, TextProductModel, TextProductSegmentModel, UGCModel, VTECModel

if TYPE_CHECKING:
    from pyiem.nws.hvtec import HVTEC
    from pyiem.nws.product import TextProduct, TextProductSegment
    from pyiem.nws.ugc import UGC
    from pyiem.nws.vtec import VTEC


def convert_ugc_to_model(ugc_obj: "UGC") -> UGCModel:
    """Convert a UGC object to its Pydantic model."""
    return UGCModel(
        state=getattr(ugc_obj, "state", ""),
        geoClass=getattr(ugc_obj, "geoclass", ""),
        number=getattr(ugc_obj, "number", 0),
        name=getattr(ugc_obj, "name", ""),
        wfoIdList=list(getattr(ugc_obj, "wfos", [])),
    )


def convert_vtec_to_model(vtec_obj: "VTEC") -> VTECModel:
    """Convert a VTEC object to its Pydantic model."""
    return VTECModel(
        line=getattr(vtec_obj, "line", ""),
        status=getattr(vtec_obj, "status", ""),
        action=getattr(vtec_obj, "action", ""),
        officeId=getattr(vtec_obj, "office", ""),
        officeId4=getattr(vtec_obj, "office4", ""),
        phenomena=getattr(vtec_obj, "phenomena", ""),
        significance=getattr(vtec_obj, "significance", ""),
        eventTrackingNumber=getattr(vtec_obj, "etn", 0),
        year=getattr(vtec_obj, "year", 0),
    )


def convert_hvtec_to_model(hvtec_obj: "HVTEC") -> HVTECModel:
    """Convert an HVTEC object to its Pydantic model."""
    nwsli_id_val = ""
    nwsli_attr = getattr(hvtec_obj, "nwsli", None)
    if nwsli_attr is not None:
        nwsli_id_val = getattr(nwsli_attr, "id", "") if hasattr(nwsli_attr, "id") else str(nwsli_attr)

    return HVTECModel(
        line=getattr(hvtec_obj, "line", ""),
        nwsliId=nwsli_id_val,
        severity=getattr(hvtec_obj, "severity", ""),
        cause=getattr(hvtec_obj, "cause", ""),
        beginTimestamp=getattr(hvtec_obj, "beginTS", None),
        crestTimestamp=getattr(hvtec_obj, "crestTS", None),
        endTimestamp=getattr(hvtec_obj, "endTS", None),
        record=getattr(hvtec_obj, "record", ""),
    )


def convert_text_product_segment_to_model(
    segment_obj: "TextProductSegment",
) -> TextProductSegmentModel:
    """Convert a TextProductSegment object to its Pydantic model."""
    hvtec_list = []
    hvtec_attr = getattr(segment_obj, "hvtec", None)
    if hvtec_attr:
        hvtec_list = [convert_hvtec_to_model(h) for h in hvtec_attr if h]

    return TextProductSegmentModel(
        segmentText=getattr(segment_obj, "unixtext", ""),
        ugcRecords=[convert_ugc_to_model(u) for u in getattr(segment_obj, "ugcs", []) if u],
        ugcExpireTime=getattr(segment_obj, "ugcexpire", None),
        headlines=list(getattr(segment_obj, "headlines", [])),
        hvtecRecords=hvtec_list,
        timeMotLocGisWkt=getattr(segment_obj, "tml_giswkt", None),
        timeMotLocValidTime=getattr(segment_obj, "tml_valid", None),
        timeMotLocSpeedKnots=getattr(segment_obj, "tml_sknt", None),
        timeMotLocDirectionDegrees=getattr(segment_obj, "tml_dir", None),
        stormBasedWarningGisWkt=getattr(segment_obj, "giswkt", None),
        windTag=getattr(segment_obj, "windtag", None),
        windTagUnits=getattr(segment_obj, "windtagunits", None),
        windThreat=getattr(segment_obj, "windthreat", None),
        hailTag=getattr(segment_obj, "hailtag", None),
        hailDirectionTag=getattr(segment_obj, "haildirtag", None),
        hailThreat=getattr(segment_obj, "hailthreat", None),
        windDirectionTag=getattr(segment_obj, "winddirtag", None),
        tornadoTag=getattr(segment_obj, "tornadotag", None),
        waterspoutTag=getattr(segment_obj, "waterspouttag", None),
        landspoutTag=getattr(segment_obj, "landspouttag", None),
        damageThreatTag=getattr(segment_obj, "damagetag", None),
        squallTag=getattr(segment_obj, "squalltag", None),
        floodTags=dict(getattr(segment_obj, "flood_tags", {})),
        isEmergency=getattr(segment_obj, "is_emergency", False),
        isPDS=getattr(segment_obj, "is_pds", False),
        bulletPoints=list(getattr(segment_obj, "bullets", [])),
    )


def convert_text_product_to_model(
    product_obj: "TextProduct",
) -> TextProductModel:
    """Convert a TextProduct object to its Pydantic model."""
    # TextProduct specific attributes and derived values
    product_id_val: str | None = None
    try:
        # get_product_id might fail if constituent parts (valid, afos, etc.) are None
        if all(
            [
                getattr(product_obj, "valid", None),
                getattr(product_obj, "source", None),
                getattr(product_obj, "wmo", None),
                getattr(product_obj, "afos", None),
            ],
        ) and hasattr(product_obj, "get_product_id"):
            product_id_val = product_obj.get_product_id()  # type: ignore[union-attr]
    except (AttributeError, TypeError, ValueError):
        product_id_val = None

    # Pydantic V2: model_validate with direct dict construction
    return TextProductModel.model_validate(
        {
            # WMOProduct base attributes
            "text": getattr(product_obj, "text", ""),
            "warnings": list(getattr(product_obj, "warnings", [])),
            "source": getattr(product_obj, "source", None),
            "wmo": getattr(product_obj, "wmo", None),
            "ddhhmm": getattr(product_obj, "ddhhmm", None),
            "bbb": getattr(product_obj, "bbb", None),
            "valid": getattr(product_obj, "valid", None),
            "wmo_valid": getattr(product_obj, "wmo_valid", None),
            "utcnow": getattr(product_obj, "utcnow", None),
            "z": getattr(product_obj, "z", None),
            # TextProduct specific attributes
            "afos": getattr(product_obj, "afos", None),
            "sections": list(getattr(product_obj, "sections", [])),
            "segments": [convert_text_product_segment_to_model(s) for s in getattr(product_obj, "segments", [])],
            "geometry": getattr(product_obj, "geometry", None),
            "product_id": product_id_val,
            "nicedate": product_obj.get_nicedate()  # type: ignore[union-attr]
            if hasattr(product_obj, "get_nicedate")
            else None,  # type: ignore[union-attr]
            "main_headline": product_obj.get_main_headline("")  # type: ignore[union-attr]
            if hasattr(product_obj, "get_main_headline")
            else "",  # type: ignore[union-attr]
            "signature": product_obj.get_signature() if hasattr(product_obj, "get_signature") else None,
            "channels": product_obj.get_channels()  # type: ignore[union-attr]
            if hasattr(product_obj, "get_channels") and getattr(product_obj, "afos", None)
            else [],
            "is_correction": product_obj.is_correction()  # type: ignore[union-attr]
            if hasattr(product_obj, "is_correction")
            else None,  # type: ignore[union-attr]
            "is_resent": product_obj.is_resent() if hasattr(product_obj, "is_resent") else None,  # type: ignore[union-attr]
            "attn_wfo": product_obj.parse_attn_wfo()  # type: ignore[union-attr]
            if hasattr(product_obj, "parse_attn_wfo")
            else [],  # type: ignore[union-attr]
            "attn_rfc": product_obj.parse_attn_rfc()  # type: ignore[union-attr]
            if hasattr(product_obj, "parse_attn_rfc")
            else [],  # type: ignore[union-attr]
        },
    )
