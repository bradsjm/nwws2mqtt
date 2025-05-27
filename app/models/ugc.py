"""UGC (Universal Geographic Code) model."""

from pydantic import BaseModel, Field, ConfigDict


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
