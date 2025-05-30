# pyright: strict
"""Pipeline package.

This package provides a flexible, extensible pipeline system for processing
through filters, transformers, and outputs.
"""

from .config import (
    PipelineBuilder,
    PipelineConfig,
    PipelineManagerConfig,
    create_manager_from_file,
    create_pipeline_from_file,
    load_config_from_file,
    load_manager_config,
    load_pipeline_config,
)
from .core import Pipeline, PipelineManager
from .errors import ErrorHandler, ErrorHandlingStrategy, PipelineError, PipelineErrorEvent
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
    "PipelineManagerConfig",
    # Configuration loading utilities
    "create_manager_from_file",
    "create_pipeline_from_file",
    "load_config_from_file",
    "load_manager_config",
    "load_pipeline_config",
    # Enums
    "ErrorHandlingStrategy",
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
    "ErrorHandler",
    "PipelineError",
    "PipelineStats",
]
