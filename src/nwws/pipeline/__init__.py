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
from .errors import (
    ErrorHandlingStrategy,
    PipelineError,
    PipelineErrorEvent,
    PipelineErrorHandler,
)
from .filters import Filter, FilterConfig, FilterRegistry
from .outputs import Output, OutputConfig, OutputRegistry
from .stats import PipelineStatsCollector, PipelineStatsEvent
from .transformers import Transformer, TransformerConfig, TransformerRegistry
from .types import PipelineEvent, PipelineEventMetadata, PipelineStage

__all__ = [  # noqa: RUF022
    # Base interfaces
    "Filter",
    "FilterConfig",
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
    "OutputConfig",
    "TransformerRegistry",
    "TransformerConfig",
    # Stats and errors
    "PipelineErrorHandler",
    "PipelineError",
    "PipelineStatsCollector",
]
