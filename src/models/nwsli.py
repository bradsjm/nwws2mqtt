"""NWSLI model."""

from pydantic import BaseModel, Field, ConfigDict


class NWSLIModel(BaseModel):
    """Pydantic model for an NWSLI identifier."""

    id: str = Field(description="The NWSLI identifier.", alias="nwsliId")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
