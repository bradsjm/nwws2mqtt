"""VTEC (Valid Time Event Code) model."""

import datetime

from pydantic import BaseModel, ConfigDict, Field


class VTECModel(BaseModel):
    """Pydantic model for a VTEC (Valid Time Event Code) entry."""

    line: str = Field(description="The raw VTEC line string.")
    status: str = Field(description="VTEC status code (e.g., NEW, CON, EXP).")
    action: str = Field(description="VTEC action code (e.g., NEW, CON, CAN).")
    office: str = Field(description="Issuing NWS office ID (3-letter).", alias="officeId")
    office4: str = Field(
        description="Issuing NWS office ID (4-letter, including leading K/P).",
        alias="officeId4",
    )
    phenomena: str = Field(description="VTEC phenomena code (e.g., TO, SV, FF).")
    significance: str = Field(description="VTEC significance code (e.g., W, A, Y).")
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
    year: int | None = Field(default=None, description="Year of the event, if explicitly set.")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
