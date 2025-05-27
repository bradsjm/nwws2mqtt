"""Models package for NWWS-OI message processing."""

from .base import WMOProductBaseModel
from .nwsli import NWSLIModel
from .ugc import UGCModel
from .vtec import VTECModel
from .hvtec import HVTECModel
from .product import TextProductModel, TextProductSegmentModel
from .output_config import OutputConfig
from .config import Config
from .xmpp_config import XMPPConfig
from .converters import (
    convert_ugc_to_model,
    convert_vtec_to_model,
    convert_hvtec_to_model,
    convert_text_product_segment_to_model,
    convert_text_product_to_model,
)

__all__ = [
    "Config",
    "WMOProductBaseModel",
    "NWSLIModel",
    "UGCModel",
    "VTECModel",
    "HVTECModel",
    "TextProductModel",
    "TextProductSegmentModel",
    "OutputConfig",
    "XMPPConfig",
    "convert_ugc_to_model",
    "convert_vtec_to_model",
    "convert_hvtec_to_model",
    "convert_text_product_segment_to_model",
    "convert_text_product_to_model",
]
