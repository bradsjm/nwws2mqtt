# pyright: strict
"""Pipeline package for NWWS2MQTT application.

This package provides a flexible, extensible pipeline system for processing
weather data from NWWS-OI through filters, transformers, and outputs.
"""

from .config import PipelineBuilder, PipelineConfig
from .core import Pipeline, PipelineManager
from .errors import PipelineError, PipelineErrorEvent
from .filters import Filter, FilterRegistry
from .outputs import Output, OutputRegistry
from .stats import PipelineStats, PipelineStatsEvent
from .transformers import Transformer, TransformerRegistry
from .types import PipelineEvent, PipelineEventMetadata, PipelineStage

__all__ = [  # noqa: RUF022
    # Base interfaces
    "Filter",
    "Output",
    "Transformer",
    # Core pipeline components
    "Pipeline",
    "PipelineBuilder",
    "PipelineConfig",
    "PipelineManager",
    # Enums
    "PipelineStage",
    # Event types
    "PipelineEvent",
    "PipelineEventMetadata",
    "PipelineErrorEvent",
    "PipelineStatsEvent",
    # Registries
    "FilterRegistry",
    "OutputRegistry",
    "TransformerRegistry",
    # Stats and errors
    "PipelineError",
    "PipelineStats",
]
