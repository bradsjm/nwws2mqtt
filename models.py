import datetime
from pydantic import BaseModel, Field, ConfigDict
from pyiem.nws.ugc import UGC
from pyiem.nws.vtec import VTEC
from pyiem.nws.hvtec import HVTEC
from pyiem.nws.product import TextProduct, TextProductSegment


class NWSLIModel(BaseModel):
    """Pydantic model for an NWSLI identifier."""

    id: str = Field(description="The NWSLI identifier.", alias="nwsliId")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class UGCModel(BaseModel):
    """Pydantic model for a UGC (Universal Geographic Code)."""

    state: str = Field(description="State abbreviation for the UGC.")
    geoclass: str = Field(
        description="Geographic class of the UGC (e.g., C for County, Z for Zone).",
        alias="geoClass",
    )
    number: int = Field(description="Numeric part of the UGC.")
    name: str = Field(description="Descriptive name of the UGC area.")
    wfos: list[str] = Field(
        description="List of Weather Forecast Offices (WFOs) associated with this UGC.",
        default_factory=list,
    )

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class VTECModel(BaseModel):
    """Pydantic model for a VTEC (Valid Time Event Code) entry."""

    status: str = Field(
        description="VTEC status code (e.g., NEW, CON, EXP)."
    )
    action: str = Field(
        description="VTEC action code (e.g., NEW, CON, CAN)."
    )
    office: str = Field(
        description="Issuing NWS office ID (3-letter).", alias="officeId"
    )
    office4: str = Field(
        description="Issuing NWS office ID (4-letter, including leading K/P).",
        alias="officeId4",
    )
    phenomena: str = Field(
        description="VTEC phenomena code (e.g., TO, SV, FF)."
    )
    significance: str = Field(
        description="VTEC significance code (e.g., W, A, Y)."
    )
    etn: int = Field(description="Event Tracking Number.", alias="eventTrackingNumber")
    begints: datetime.datetime | None = Field(
        default=None,
        description="Event begin timestamp (UTC).",
        alias="beginTimestamp",
    )
    endts: datetime.datetime | None = Field(
        default=None,
        description="Event end timestamp (UTC).",
        alias="endTimestamp",
    )
    year: int | None = Field(
        default=None, description="Year of the event, if explicitly set."
    )

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class HVTECModel(BaseModel):
    """Pydantic model for an HVTEC (Hydrologic VTEC) entry."""

    nwsli_id: str = Field(
        description="NWSLI (National Weather Service Location Identifier) for the hydrologic point.",
        alias="nwsliId",
    )
    severity: str = Field(description="HVTEC severity code.")
    cause: str = Field(description="HVTEC cause code.")
    beginTS: datetime.datetime | None = Field(
        default=None,
        description="Begin timestamp for the hydrologic event (UTC).",
        alias="beginTimestamp",
    )
    crestTS: datetime.datetime | None = Field(
        default=None,
        description="Crest timestamp for the hydrologic event (UTC).",
        alias="crestTimestamp",
    )
    endTS: datetime.datetime | None = Field(
        default=None,
        description="End timestamp for the hydrologic event (UTC).",
        alias="endTimestamp",
    )
    record: str = Field(description="HVTEC record code.")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class WMOProductBaseModel(BaseModel):
    """Base Pydantic model for WMO Product attributes."""

    warnings: list[str] = Field(
        description="List of parsing warnings encountered.",
        alias="parsingWarnings",
        default_factory=list,
    )
    source: str | None = Field(
        default=None,
        description="Issuing source/center identifier (e.g., KJAN).",
        alias="sourceId",
    )
    wmo: str | None = Field(
        default=None, description="WMO TTAAii heading.", alias="wmoHeader"
    )
    ddhhmm: str | None = Field(
        default=None,
        description="Day-Hour-Minute group from the WMO header.",
        alias="wmoDdhhmm",
    )
    bbb: str | None = Field(
        default=None,
        description="Optional BBB group (correction indicator) from the WMO header.",
        alias="bbbIndicator",
    )
    valid: datetime.datetime | None = Field(
        default=None,
        description="Potentially localized timestamp of product validity/issuance.",
        alias="validTime",
    )
    wmo_valid: datetime.datetime | None = Field(
        default=None,
        description="WMO header based timestamp (UTC).",
        alias="wmoValidTime",
    )
    utcnow: datetime.datetime = Field(
        description="Timestamp (UTC) when the product was processed or received.",
        alias="processedUtcTimestamp",
    )
    z: str | None = Field( # Timezone abbreviation string
        default=None,
        description="Timezone abbreviation string if product time is localized.",
        alias="timezoneAbbreviation",
    )

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class TextProductSegmentModel(BaseModel):
    """Pydantic model for a segment of a Text Product."""

    unixtext: str = Field(
        description="The text content of this segment with Unix line endings.",
        alias="segmentText",
    )
    vtec: list[VTECModel] = Field(
        description="List of VTEC entries found in this segment.",
        alias="vtecRecords",
        default_factory=list,
    )
    ugcs: list[UGCModel] = Field(
        description="List of UGCs (Universal Geographic Codes) covered by this segment.",
        default_factory=list,
    )
    ugcexpire: datetime.datetime | None = Field(
        default=None,
        description="Expiration time for the UGCs in this segment (UTC).",
        alias="ugcExpireTime",
    )
    headlines: list[str] = Field(
        description="List of headlines extracted from this segment.",
        default_factory=list,
    )
    hvtec: list[HVTECModel] = Field(
        description="List of HVTEC entries found in this segment.",
        alias="hvtecRecords",
        default_factory=list,
    )
    tml_giswkt: str | None = Field(
        default=None,
        description="TIME...MOT...LOC geometry as Well-Known Text (WKT).",
        alias="tmlGisWkt",
    )
    tml_valid: datetime.datetime | None = Field(
        default=None,
        description="TIME...MOT...LOC valid timestamp (UTC).",
        alias="tmlValidTime",
    )
    tml_sknt: int | None = Field(
        default=None,
        description="TIME...MOT...LOC speed in knots.",
        alias="tmlSpeedKnots",
    )
    tml_dir: int | None = Field(
        default=None,
        description="TIME...MOT...LOC direction in degrees.",
        alias="tmlDirectionDegrees",
    )
    giswkt: str | None = Field(
        default=None,
        description="Storm Based Warning (SBW) polygon as Well-Known Text (WKT), SRID=4326.",
        alias="sbwGisWkt",
    )
    windtag: str | None = Field(
        default=None,
        description="Wind speed tag value (e.g., '60 MPH').",
        alias="windTag",
    )
    windtagunits: str | None = Field(
        default=None,
        description="Units for the wind speed tag (e.g., 'MPH', 'KT').",
        alias="windTagUnits",
    )
    windthreat: str | None = Field(
        default=None,
        description="Wind threat level (e.g., 'RADAR INDICATED', 'OBSERVED').",
        alias="windThreat",
    )
    hailtag: str | None = Field(
        default=None,
        description="Hail size tag value (e.g., '1.00 INCH').",
        alias="hailTag",
    )
    haildirtag: str | None = Field(
        default=None,
        description="Hail size direction/comparison (e.g., '>', '<=').",
        alias="hailDirectionTag",
    )
    hailthreat: str | None = Field(
        default=None, description="Hail threat level.", alias="hailThreat"
    )
    winddirtag: str | None = Field(
        default=None,
        description="Wind speed direction/comparison (e.g., '>', '<=').",
        alias="windDirectionTag",
    )
    tornadotag: str | None = Field(
        default=None,
        description="Tornado presence/threat tag.",
        alias="tornadoTag",
    )
    waterspouttag: str | None = Field(
        default=None,
        description="Waterspout presence/threat tag.",
        alias="waterspoutTag",
    )
    landspouttag: str | None = Field(
        default=None,
        description="Landspout presence/threat tag.",
        alias="landspoutTag",
    )
    damagetag: str | None = Field(
        default=None,
        description="Damage threat tag (e.g., 'CONSIDERABLE', 'DESTRUCTIVE').",
        alias="damageThreatTag",
    )
    squalltag: str | None = Field(
        default=None,
        description="Snow squall specific tag.",
        alias="squallTag",
    )
    flood_tags: dict[str, str] = Field(
        description="Key-value pairs of flood-related tags.",
        alias="floodTags",
        default_factory=dict,
    )
    is_emergency: bool = Field(
        default=False,
        description="Flag indicating if this segment represents an emergency.",
        alias="isEmergency",
    )
    is_pds: bool = Field(
        default=False,
        description="Flag indicating if this segment represents a Particularly Dangerous Situation (PDS).",
        alias="isPds",
    )
    bullets: list[str] = Field(
        description="List of bulleted text items extracted from the segment.",
        alias="bulletPoints",
        default_factory=list,
    )

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class TextProductModel(WMOProductBaseModel):
    """Pydantic model for a Text Product."""

    afos: str | None = Field(
        default=None,
        description="AFOS PIL (Product Identifier Line) for the product.",
        alias="afosPil",
    )
    unixtext: str = Field(
        description="The full product text with Unix line endings.",
        alias="fullProductText",
    )
    sections: list[str] = Field(
        description="List of text sections, typically split by double newlines.",
        alias="textSections",
        default_factory=list,
    )
    segments: list[TextProductSegmentModel] = Field(
        description="List of parsed product segments.",
        alias="productSegments",
        default_factory=list,
    )
    geometry: str | None = Field(
        default=None,
        description="Overall product geometry, if applicable (e.g., WKT).",
        alias="productGeometry",
    )

    # Derived fields from methods
    product_id: str | None = Field(
        default=None,
        description="IEM-specific unique product identifier.",
        alias="productId",
    )
    nicedate: str | None = Field(
        default=None,
        description="User-friendly formatted issuance date and time.",
        alias="formattedIssuanceTime",
    )
    main_headline: str | None = Field(
        default=None,
        description="The primary headline from the product segments.",
    )
    signature: str | None = Field(
        default=None,
        description="Forecaster signature or sign-off line from the product.",
        alias="forecasterSignature",
    )
    channels: list[str] = Field(
        description="List of distribution channels for this product.",
        alias="distributionChannels",
        default_factory=list,
    )
    is_correction: bool | None = Field(
        default=None,
        description="Flag indicating if this product is a correction.",
    )
    is_resent: bool | None = Field(
        default=None, description="Flag indicating if this product is a resend."
    )
    attn_wfo: list[str] = Field(
        description="List of WFOs found in ATTN...WFO line.",
        alias="attentionWfos",
        default_factory=list,
    )
    attn_rfc: list[str] = Field(
        description="List of RFCs found in ATTN...RFC line.",
        alias="attentionRfcs",
        default_factory=list,
    )

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

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