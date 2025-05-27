"""Base model classes."""

import datetime

from pydantic import BaseModel, ConfigDict, Field


class WMOProductBaseModel(BaseModel):
    """Base Pydantic model for WMO Product attributes."""

    text: str = Field(
        description="The full text content of the product.",
        alias="fullText",
    )
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
    wmo: str | None = Field(default=None, description="WMO TTAAii heading.", alias="wmoHeader")
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
    z: str | None = Field(  # Timezone abbreviation string
        default=None,
        description="Timezone abbreviation string if product time is localized.",
        alias="timezoneAbbreviation",
    )

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
