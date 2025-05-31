"""Pipeline event data for WMO Products."""

from dataclasses import dataclass

from nwws.models.weather.product import TextProductModel

from .noaa_port_event_data import NoaaPortEventData


@dataclass
class TextProductEventData(NoaaPortEventData):
    """Pipeline event wrapper for WeatherWire events."""

    product: TextProductModel
    """WeatherWire text product model converted from raw data."""

    def __str__(self) -> str:
        """Return a string representation of the text product event."""
        return self.product.model_dump_json(
            indent=2,
            exclude_defaults=True,
            exclude_unset=True,
            exclude_none=True,
            by_alias=True,
        )
