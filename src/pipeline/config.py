# pyright: strict
"""Pipeline configuration and builder utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from .core import Pipeline, PipelineManager
from .errors import ErrorHandler, PipelineError
from .filters import FilterConfig, FilterRegistry
from .outputs import OutputConfig, OutputRegistry
from .stats import PipelineStats, StatsCollector
from .transformers import TransformerConfig, TransformerRegistry


@dataclass
class PipelineConfig:
    """Configuration for a single pipeline."""

    pipeline_id: str
    """Unique identifier for the pipeline."""

    filters: list[FilterConfig] = field(default_factory=list)
    """List of filter configurations."""

    transformer: TransformerConfig | None = None
    """Transformer configuration."""

    outputs: list[OutputConfig] = field(default_factory=list)
    """List of output configurations."""

    enable_stats: bool = True
    """Whether to enable statistics collection."""

    enable_error_handling: bool = True
    """Whether to enable error handling."""

    config: dict[str, Any] = field(default_factory=dict)
    """Additional pipeline-specific configuration."""


@dataclass
class PipelineManagerConfig:
    """Configuration for the pipeline manager."""

    pipelines: list[PipelineConfig] = field(default_factory=list)
    """List of pipeline configurations."""

    max_queue_size: int = 1000
    """Maximum size of the event queue."""

    processing_timeout_seconds: float = 30.0
    """Timeout for processing events."""

    enable_metrics: bool = True
    """Whether to enable metrics collection."""

    config: dict[str, Any] = field(default_factory=dict)
    """Additional manager-specific configuration."""


class PipelineBuilder:
    """Builder for creating pipelines from configuration."""

    def __init__(
        self,
        filter_registry: FilterRegistry | None = None,
        transformer_registry: TransformerRegistry | None = None,
        output_registry: OutputRegistry | None = None,
    ) -> None:
        """Initialize the pipeline builder.

        Args:
            filter_registry: Registry for creating filters.
            transformer_registry: Registry for creating transformers.
            output_registry: Registry for creating outputs.

        """
        # Import here to avoid circular imports
        from .filters import filter_registry as default_filter_registry
        from .outputs import output_registry as default_output_registry
        from .transformers import transformer_registry as default_transformer_registry

        self.filter_registry = filter_registry or default_filter_registry
        self.transformer_registry = transformer_registry or default_transformer_registry
        self.output_registry = output_registry or default_output_registry

    def build_pipeline(self, config: PipelineConfig) -> Pipeline:
        """Build a pipeline from configuration.

        Args:
            config: Pipeline configuration.

        Returns:
            Configured pipeline instance.

        Raises:
            PipelineError: If pipeline creation fails.

        """
        try:
            # Create filters
            filters = [self.filter_registry.create(filter_config) for filter_config in config.filters]

            # Create transformer
            transformer = None
            if config.transformer:
                transformer = self.transformer_registry.create(config.transformer)

            # Create outputs
            outputs = [self.output_registry.create(output_config) for output_config in config.outputs]

            # Create stats collector
            stats_collector = None
            if config.enable_stats:
                stats = PipelineStats()
                stats_collector = StatsCollector(stats)

            # Create error handler
            error_handler = None
            if config.enable_error_handling:
                error_handler = ErrorHandler()

            # Create pipeline
            pipeline = Pipeline(
                pipeline_id=config.pipeline_id,
                filters=filters,
                transformer=transformer,
                outputs=outputs,
                stats_collector=stats_collector,
                error_handler=error_handler,
            )

            logger.info(
                "Pipeline built successfully",
                pipeline_id=config.pipeline_id,
                filter_count=len(filters),
                has_transformer=transformer is not None,
                output_count=len(outputs),
                stats_enabled=config.enable_stats,
                error_handling_enabled=config.enable_error_handling,
            )

        except Exception as e:
            error_msg = f"Failed to build pipeline {config.pipeline_id}: {e}"
            raise PipelineError(error_msg) from e

        return pipeline

    def build_manager(self, config: PipelineManagerConfig) -> PipelineManager:
        """Build a pipeline manager from configuration.

        Args:
            config: Pipeline manager configuration.

        Returns:
            Configured pipeline manager instance.

        Raises:
            PipelineError: If manager creation fails.

        """
        try:
            manager = PipelineManager()

            # Build and add all pipelines
            for pipeline_config in config.pipelines:
                pipeline = self.build_pipeline(pipeline_config)
                manager.add_pipeline(pipeline)

            logger.info(
                "Pipeline manager built successfully",
                pipeline_count=len(config.pipelines),
                max_queue_size=config.max_queue_size,
                metrics_enabled=config.enable_metrics,
            )

        except Exception as e:
            error_msg = f"Failed to build pipeline manager: {e}"
            raise PipelineError(error_msg) from e

        return manager


class ConfigValidator:
    """Validates pipeline configurations."""

    @staticmethod
    def validate_pipeline_config(config: PipelineConfig) -> list[str]:
        """Validate a pipeline configuration.

        Args:
            config: Pipeline configuration to validate.

        Returns:
            List of validation error messages (empty if valid).

        """
        errors: list[str] = []

        # Validate pipeline ID
        if not config.pipeline_id:
            errors.append("Pipeline ID cannot be empty")

        # Validate filters
        for i, filter_config in enumerate(config.filters):
            filter_errors = ConfigValidator.validate_filter_config(filter_config)
            errors.extend([f"Filter {i}: {error}" for error in filter_errors])

        # Validate transformer
        if config.transformer:
            transformer_errors = ConfigValidator.validate_transformer_config(config.transformer)
            errors.extend([f"Transformer: {error}" for error in transformer_errors])

        # Validate outputs
        if not config.outputs:
            errors.append("At least one output must be configured")
        else:
            for i, output_config in enumerate(config.outputs):
                output_errors = ConfigValidator.validate_output_config(output_config)
                errors.extend([f"Output {i}: {error}" for error in output_errors])

        return errors

    @staticmethod
    def validate_filter_config(config: FilterConfig) -> list[str]:
        """Validate a filter configuration.

        Args:
            config: Filter configuration to validate.

        Returns:
            List of validation error messages (empty if valid).

        """
        errors: list[str] = []

        if not config.filter_type:
            errors.append("Filter type cannot be empty")

        if not config.filter_id:
            errors.append("Filter ID cannot be empty")

        return errors

    @staticmethod
    def validate_transformer_config(config: TransformerConfig) -> list[str]:
        """Validate a transformer configuration.

        Args:
            config: Transformer configuration to validate.

        Returns:
            List of validation error messages (empty if valid).

        """
        errors: list[str] = []

        if not config.transformer_type:
            errors.append("Transformer type cannot be empty")

        if not config.transformer_id:
            errors.append("Transformer ID cannot be empty")

        return errors

    @staticmethod
    def validate_output_config(config: OutputConfig) -> list[str]:
        """Validate an output configuration.

        Args:
            config: Output configuration to validate.

        Returns:
            List of validation error messages (empty if valid).

        """
        errors: list[str] = []

        if not config.output_type:
            errors.append("Output type cannot be empty")

        if not config.output_id:
            errors.append("Output ID cannot be empty")

        return errors

    @staticmethod
    def validate_manager_config(config: PipelineManagerConfig) -> list[str]:
        """Validate a pipeline manager configuration.

        Args:
            config: Pipeline manager configuration to validate.

        Returns:
            List of validation error messages (empty if valid).

        """
        errors: list[str] = []

        if not config.pipelines:
            errors.append("At least one pipeline must be configured")
        else:
            for i, pipeline_config in enumerate(config.pipelines):
                pipeline_errors = ConfigValidator.validate_pipeline_config(pipeline_config)
                errors.extend([f"Pipeline {i}: {error}" for error in pipeline_errors])

        if config.max_queue_size <= 0:
            errors.append("Max queue size must be positive")

        if config.processing_timeout_seconds <= 0:
            errors.append("Processing timeout must be positive")

        return errors


def create_simple_pipeline(
    pipeline_id: str,
    filter_configs: list[dict[str, Any]] | None = None,
    transformer_config: dict[str, Any] | None = None,
    output_configs: list[dict[str, Any]] | None = None,
) -> Pipeline:
    """Create a simple pipeline with minimal configuration.

    Args:
        pipeline_id: Unique identifier for the pipeline.
        filter_configs: List of filter configurations.
        transformer_config: Transformer configuration.
        output_configs: List of output configurations.

    Returns:
        Configured pipeline instance.

    Raises:
        PipelineError: If pipeline creation fails.

    """
    # Convert dict configs to dataclass configs
    filters: list[FilterConfig] = []
    if filter_configs:
        for i, filter_dict in enumerate(filter_configs):
            filter_config = FilterConfig(
                filter_type=filter_dict.get("type", "passthrough"),
                filter_id=filter_dict.get("id", f"filter_{i}"),
                config=filter_dict.get("config", {}),
            )
            filters.append(filter_config)

    transformer = None
    if transformer_config:
        transformer = TransformerConfig(
            transformer_type=transformer_config.get("type", "passthrough"),
            transformer_id=transformer_config.get("id", "transformer"),
            config=transformer_config.get("config", {}),
        )

    outputs: list[OutputConfig] = []
    if output_configs:
        for i, output_dict in enumerate(output_configs):
            output_config = OutputConfig(
                output_type=output_dict.get("type", "log"),
                output_id=output_dict.get("id", f"output_{i}"),
                config=output_dict.get("config", {}),
            )
            outputs.append(output_config)
    else:
        # Default to log output
        outputs.append(
            OutputConfig(
                output_type="log",
                output_id="default_log",
                config={},
            ),
        )

    # Create pipeline config
    pipeline_config = PipelineConfig(
        pipeline_id=pipeline_id,
        filters=filters,
        transformer=transformer,
        outputs=outputs,
    )

    # Build and return pipeline
    builder = PipelineBuilder()
    return builder.build_pipeline(pipeline_config)
