"""Text product models."""

import datetime

from pydantic import BaseModel, ConfigDict, Field

from .hvtec import HVTECModel
from .ugc import UGCModel
from .vtec import VTECModel
from .wmo import WMOModel


class TextProductSegmentModel(BaseModel):
    """Pydantic model for a segment of a Text Product."""

    unixtext: str = Field(
        description="The text content of this segment with Unix line endings.",
        alias="segmentText",
    )
    vtec: list[VTECModel] = Field(
        description="List of VTEC entries found in this segment.",
        alias="vtecRecords",
        default_factory=list[VTECModel],
    )
    ugcs: list[UGCModel] = Field(
        description="List of UGCs (Universal Geographic Codes) covered by this segment.",
        default_factory=list[UGCModel],
        alias="ugcRecords",
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
        default_factory=list[HVTECModel],
    )
    tml_giswkt: str | None = Field(
        default=None,
        description="TIME...MOT...LOC geometry as Well-Known Text (WKT).",
        alias="timeMotLocGisWkt",
    )
    tml_valid: datetime.datetime | None = Field(
        default=None,
        description="TIME...MOT...LOC valid timestamp (UTC).",
        alias="timeMotLocValidTime",
    )
    tml_sknt: int | None = Field(
        default=None,
        description="TIME...MOT...LOC speed in knots.",
        alias="timeMotLocSpeedKnots",
    )
    tml_dir: int | None = Field(
        default=None,
        description="TIME...MOT...LOC direction in degrees.",
        alias="timeMotLocDirectionDegrees",
    )
    giswkt: str | None = Field(
        default=None,
        description="Storm Based Warning (SBW) polygon as Well-Known Text (WKT), SRID=4326.",
        alias="stormBasedWarningGisWkt",
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
        default=None,
        description="Hail threat level.",
        alias="hailThreat",
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
        description="Flag indicating segment represents a Particularly Dangerous Situation (PDS).",
        alias="isPDS",
    )
    bullets: list[str] = Field(
        description="List of bulleted text items extracted from the segment.",
        alias="bulletPoints",
        default_factory=list,
    )
    affected_wfos: list[str] = Field(
        description="List of WFOs affected by this segment based on its UGCs.",
        alias="affectedWfoList",
        default_factory=list,
    )
    special_tags_text: str | None = Field(
        default=None,
        description="Human-readable text representation of special weather tags.",
        alias="specialTagsText",
    )

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class TextProductModel(WMOModel):
    """Pydantic model for a Text Product."""

    afos: str | None = Field(
        default=None,
        description="AFOS PIL (Product Identifier Line) for the product.",
        alias="afosPil",
    )

    segments: list[TextProductSegmentModel] = Field(
        description="List of parsed product segments.",
        alias="productSegments",
        default_factory=list[TextProductSegmentModel],
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
        alias="mainHeadline",
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
        alias="isCorrection",
    )
    is_resent: bool | None = Field(
        default=None,
        description="Flag indicating if this product is a resend.",
        alias="isResent",
    )
    attn_wfo: list[str] = Field(
        description="List of WFOs found in ATTN...WFO line.",
        alias="attentionWfoList",
        default_factory=list,
    )
    attn_rfc: list[str] = Field(
        description="List of RFCs found in ATTN...RFC line.",
        alias="attentionRfcList",
        default_factory=list,
    )


    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
