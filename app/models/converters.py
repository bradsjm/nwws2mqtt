"""Converter functions for transforming pyiem objects to Pydantic models."""

from typing import TYPE_CHECKING

from .ugc import UGCModel
from .vtec import VTECModel
from .hvtec import HVTECModel
from .product import TextProductSegmentModel, TextProductModel

if TYPE_CHECKING:
    from pyiem.nws.ugc import UGC
    from pyiem.nws.vtec import VTEC
    from pyiem.nws.hvtec import HVTEC
    from pyiem.nws.product import TextProduct, TextProductSegment


def convert_ugc_to_model(ugc_obj: "UGC") -> UGCModel:
    """Converts a UGC object to its Pydantic model."""
    return UGCModel(
        state=ugc_obj.state,
        geoclass=ugc_obj.geoclass,
        number=ugc_obj.number,
        name=ugc_obj.name,
        wfos=list(ugc_obj.wfos),
    )


def convert_vtec_to_model(vtec_obj: "VTEC") -> VTECModel:
    """Converts a VTEC object to its Pydantic model."""
    return VTECModel(
        line=vtec_obj.line,
        status=vtec_obj.status,
        action=vtec_obj.action,
        office=vtec_obj.office,
        office4=vtec_obj.office4,
        phenomena=vtec_obj.phenomena,
        significance=vtec_obj.significance,
        etn=vtec_obj.etn,
        begints=vtec_obj.begints,
        endts=vtec_obj.endts,
        year=vtec_obj.year,
    )


def convert_hvtec_to_model(hvtec_obj: "HVTEC") -> HVTECModel:
    """Converts an HVTEC object to its Pydantic model."""
    # Assumes hvtec_obj.nwsli is an object with an 'id' attribute
    # or hvtec_obj.nwsli itself is the ID string if NWSLI class is simple.
    nwsli_id_val = ""
    if hasattr(hvtec_obj, "nwsli"):
        if hasattr(hvtec_obj.nwsli, "id"):
            nwsli_id_val = hvtec_obj.nwsli.id
        else:
            # Fallback if nwsli object doesn't have .id but might be the ID itself
            nwsli_id_val = str(hvtec_obj.nwsli)

    return HVTECModel(
        line=hvtec_obj.line,
        nwsli_id=nwsli_id_val,
        severity=hvtec_obj.severity,
        cause=hvtec_obj.cause,
        beginTS=hvtec_obj.beginTS,
        crestTS=hvtec_obj.crestTS,
        endTS=hvtec_obj.endTS,
        record=hvtec_obj.record,
    )


def convert_text_product_segment_to_model(
    segment_obj: "TextProductSegment",
) -> TextProductSegmentModel:
    """Converts a TextProductSegment object to its Pydantic model."""
    hvtec_list = []
    if segment_obj.hvtec: # Check if hvtec is not None and not empty
        hvtec_list = [
            convert_hvtec_to_model(h) for h in segment_obj.hvtec if h
        ]

    return TextProductSegmentModel(
        unixtext=segment_obj.unixtext,
        vtec=[convert_vtec_to_model(v) for v in segment_obj.vtec if v],
        ugcs=[convert_ugc_to_model(u) for u in segment_obj.ugcs if u],
        ugcexpire=segment_obj.ugcexpire,
        headlines=list(segment_obj.headlines),
        hvtec=hvtec_list,
        tml_giswkt=segment_obj.tml_giswkt,
        tml_valid=segment_obj.tml_valid,
        tml_sknt=segment_obj.tml_sknt,
        tml_dir=segment_obj.tml_dir,
        giswkt=segment_obj.giswkt,
        windtag=segment_obj.windtag,
        windtagunits=segment_obj.windtagunits,
        windthreat=segment_obj.windthreat,
        hailtag=segment_obj.hailtag,
        haildirtag=segment_obj.haildirtag,
        hailthreat=segment_obj.hailthreat,
        winddirtag=segment_obj.winddirtag,
        tornadotag=segment_obj.tornadotag,
        waterspouttag=segment_obj.waterspouttag,
        landspouttag=segment_obj.landspouttag,
        damagetag=segment_obj.damagetag,
        squalltag=segment_obj.squalltag,
        flood_tags=dict(segment_obj.flood_tags),
        is_emergency=segment_obj.is_emergency,
        is_pds=segment_obj.is_pds,
        bullets=list(segment_obj.bullets),
    )


def convert_text_product_to_model(
    product_obj: "TextProduct",
) -> TextProductModel:
    """Converts a TextProduct object to its Pydantic model."""

    # WMOProduct base attributes
    wmo_base_attrs = {
        "text": product_obj.text,
        "warnings": list(product_obj.warnings),
        "source": product_obj.source,
        "wmo": product_obj.wmo,
        "ddhhmm": product_obj.ddhhmm,
        "bbb": product_obj.bbb,
        "valid": product_obj.valid,
        "wmo_valid": product_obj.wmo_valid,
        "utcnow": product_obj.utcnow,
        "z": product_obj.z,
    }

    # TextProduct specific attributes and derived values
    product_id_val = None
    try:
        # get_product_id might fail if constituent parts (valid, afos, etc.) are None
        if all(
            [
                product_obj.valid,
                product_obj.source,
                product_obj.wmo,
                product_obj.afos,
            ]
        ):
            product_id_val = product_obj.get_product_id()
    except AttributeError: # Catch if methods or attributes are missing (should not happen with correct type)
        product_id_val = None
    except Exception: # Catch any other error during get_product_id()
        product_id_val = None


    text_product_specific_attrs = {
        "afos": product_obj.afos,
        "unixtext": product_obj.unixtext,
        "sections": list(product_obj.sections),
        "segments": [
            convert_text_product_segment_to_model(s)
            for s in product_obj.segments
        ],
        "geometry": product_obj.geometry,
        "product_id": product_id_val,
        "nicedate": product_obj.get_nicedate() if hasattr(product_obj, 'get_nicedate') else None,
        "main_headline": product_obj.get_main_headline("") if hasattr(product_obj, 'get_main_headline') else "",
        "signature": product_obj.get_signature() if hasattr(product_obj, 'get_signature') else None,
        "channels": product_obj.get_channels() if hasattr(product_obj, 'get_channels') and product_obj.afos else [],
        "is_correction": product_obj.is_correction() if hasattr(product_obj, 'is_correction') else None,
        "is_resent": product_obj.is_resent() if hasattr(product_obj, 'is_resent') else None,
        "attn_wfo": product_obj.parse_attn_wfo() if hasattr(product_obj, 'parse_attn_wfo') else [],
        "attn_rfc": product_obj.parse_attn_rfc() if hasattr(product_obj, 'parse_attn_rfc') else [],
    }

    # Pydantic V2: model_validate combines dicts automatically
    combined_attrs = {**wmo_base_attrs, **text_product_specific_attrs}
    return TextProductModel.model_validate(combined_attrs)
