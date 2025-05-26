"""HVTEC (Hydrologic VTEC) model."""

import datetime
from pydantic import BaseModel, Field, ConfigDict


class HVTECModel(BaseModel):
    """Pydantic model for an HVTEC (Hydrologic VTEC) entry."""

    line: str = Field(description="The raw HVTEC line string.")
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
