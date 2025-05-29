# pyright: strict
"""Pipeline transformers for event processing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

from loguru import logger

from .errors import TransformerError
from .types import PipelineEvent

if TYPE_CHECKING:
    from collections.abc import Callable

# Type variables for transformer input/output
T = TypeVar("T", bound=PipelineEvent)
U = TypeVar("U", bound=PipelineEvent)


class Transformer(ABC):
    """Base class for pipeline transformers."""

    def __init__(self, transformer_id: str) -> None:
        """Initialize the transformer with an identifier."""
        self.transformer_id = transformer_id

    @abstractmethod
    def transform(self, event: PipelineEvent) -> PipelineEvent:
        """Transform the input event to an output event.

        Args:
            event: The pipeline event to transform.

        Returns:
            The transformed pipeline event.

        Raises:
            TransformerError: If an error occurs during transformation.

        """

    def __call__(self, event: PipelineEvent) -> PipelineEvent:
        """Make the transformer callable."""
        try:
            result = self.transform(event)
            logger.debug(
                "Transformer applied",
                transformer_id=self.transformer_id,
                input_event_id=event.metadata.event_id,
                output_event_id=result.metadata.event_id,
                input_type=type(event).__name__,
                output_type=type(result).__name__,
            )
        except Exception as e:
            logger.error(
                "Transformer error",
                transformer_id=self.transformer_id,
                event_id=event.metadata.event_id,
                error=str(e),
            )
            msg = f"Transformer {self.transformer_id} failed: {e}"
            raise TransformerError(msg, self.transformer_id) from e
        else:
            return result


class PassThroughTransformer(Transformer):
    """Transformer that passes events through unchanged."""

    def __init__(self) -> None:
        """Initialize the pass-through transformer."""
        super().__init__("passthrough")

    def transform(self, event: PipelineEvent) -> PipelineEvent:
        """Return the event unchanged."""
        return event


class AttributeMapperTransformer(Transformer):
    """Transformer that maps attributes from input to output event."""

    def __init__(
        self,
        transformer_id: str,
        output_event_type: type[PipelineEvent],
        attribute_mapping: dict[str, str],
        default_values: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the attribute mapper transformer.

        Args:
            transformer_id: Unique identifier for this transformer.
            output_event_type: Type of event to create.
            attribute_mapping: Mapping from output attribute to input attribute.
            default_values: Default values for output attributes.

        """
        super().__init__(transformer_id)
        self.output_event_type = output_event_type
        self.attribute_mapping = attribute_mapping
        self.default_values = default_values or {}

    def transform(self, event: PipelineEvent) -> PipelineEvent:
        """Transform event by mapping attributes."""
        kwargs: dict[str, Any] = {}

        # Map attributes from input to output
        for output_attr, input_attr in self.attribute_mapping.items():
            if hasattr(event, input_attr):
                kwargs[output_attr] = getattr(event, input_attr)
            elif output_attr in self.default_values:
                kwargs[output_attr] = self.default_values[output_attr]
            else:
                logger.warning(
                    "Missing attribute in transformation",
                    transformer_id=self.transformer_id,
                    input_attribute=input_attr,
                    output_attribute=output_attr,
                    event_type=type(event).__name__,
                )

        # Add default values for any missing attributes
        for attr, default_value in self.default_values.items():
            if attr not in kwargs:
                kwargs[attr] = default_value

        # Preserve metadata from input event
        if hasattr(event, "metadata"):
            kwargs["metadata"] = event.metadata

        try:
            return self.output_event_type(**kwargs)
        except TypeError as e:
            error_msg = f"Failed to create {self.output_event_type.__name__}: {e}"
            raise TransformerError(
                error_msg,
                self.transformer_id,
            ) from e


class ChainTransformer(Transformer):
    """Transformer that chains multiple transformers together."""

    def __init__(
        self,
        transformer_id: str,
        transformers: list[Transformer],
    ) -> None:
        """Initialize the chain transformer.

        Args:
            transformer_id: Unique identifier for this transformer.
            transformers: List of transformers to chain together.

        """
        super().__init__(transformer_id)
        self.transformers = transformers

    def transform(self, event: PipelineEvent) -> PipelineEvent:
        """Apply all transformers in sequence."""
        result = event
        for transformer in self.transformers:
            result = transformer.transform(result)
        return result


class ConditionalTransformer(Transformer):
    """Transformer that applies different transformations based on conditions."""

    def __init__(
        self,
        transformer_id: str,
        conditions: list[tuple[Callable[[PipelineEvent], bool], Transformer]],
        default_transformer: Transformer | None = None,
    ) -> None:
        """Initialize the conditional transformer.

        Args:
            transformer_id: Unique identifier for this transformer.
            conditions: List of (condition_func, transformer) tuples.
            default_transformer: Transformer to use if no conditions match.

        """
        super().__init__(transformer_id)
        self.conditions = conditions
        self.default_transformer = default_transformer or PassThroughTransformer()

    def transform(self, event: PipelineEvent) -> PipelineEvent:
        """Apply the first matching transformer."""
        for condition, transformer in self.conditions:
            if condition(event):
                return transformer.transform(event)

        return self.default_transformer.transform(event)


class AttributeTransformer(Transformer):
    """Transformer that modifies specific attributes of an event."""

    def __init__(
        self,
        transformer_id: str,
        attribute_transforms: dict[str, Callable[[Any], Any]],
    ) -> None:
        """Initialize the attribute transformer.

        Args:
            transformer_id: Unique identifier for this transformer.
            attribute_transforms: Mapping of attribute names to transformation functions.

        """
        super().__init__(transformer_id)
        self.attribute_transforms = attribute_transforms

    def transform(self, event: PipelineEvent) -> PipelineEvent:
        """Transform specific attributes of the event."""
        # Create a copy of the event
        event_dict = event.__dict__.copy()

        for attr_name, transform_func in self.attribute_transforms.items():
            if hasattr(event, attr_name):
                try:
                    current_value = getattr(event, attr_name)
                    new_value = transform_func(current_value)
                    event_dict[attr_name] = new_value
                except (ValueError, TypeError, AttributeError) as e:
                    logger.warning(
                        "Failed to transform attribute",
                        transformer_id=self.transformer_id,
                        attribute=attr_name,
                        error=str(e),
                    )

        # Create new event instance with modified attributes
        try:
            return type(event)(**event_dict)
        except TypeError as e:
            msg = f"Failed to create modified event: {e}"
            raise TransformerError(
                msg,
                self.transformer_id,
            ) from e


@dataclass
class TransformerConfig:
    """Configuration for a transformer."""

    transformer_type: str
    """Type of transformer to create."""

    transformer_id: str
    """Unique identifier for the transformer."""

    config: dict[str, Any]
    """Transformer-specific configuration."""


class TransformerRegistry:
    """Registry for managing and creating transformers."""

    def __init__(self) -> None:
        """Initialize the transformer registry."""
        self._transformer_factories: dict[str, Callable[..., Transformer]] = {}
        self._register_builtin_transformers()

    def register(self, transformer_type: str, factory: Callable[..., Transformer]) -> None:
        """Register a transformer factory.

        Args:
            transformer_type: String identifier for the transformer type.
            factory: Factory function that creates the transformer.

        """
        self._transformer_factories[transformer_type] = factory

    def create(self, config: TransformerConfig) -> Transformer:
        """Create a transformer from configuration.

        Args:
            config: Transformer configuration.

        Returns:
            Configured transformer instance.

        Raises:
            TransformerError: If the transformer type is not registered or creation fails.

        """
        if config.transformer_type not in self._transformer_factories:
            msg = f"Unknown transformer type: {config.transformer_type}"
            raise TransformerError(
                msg,
                config.transformer_id,
            )

        try:
            factory = self._transformer_factories[config.transformer_type]
            return factory(config.transformer_id, **config.config)
        except Exception as e:
            msg = f"Failed to create transformer {config.transformer_id}: {e}"
            raise TransformerError(
                msg,
                config.transformer_id,
            ) from e

    def get_available_types(self) -> list[str]:
        """Get a list of available transformer types."""
        return list(self._transformer_factories.keys())

    def _register_builtin_transformers(self) -> None:
        """Register built-in transformer types."""
        self.register("passthrough", PassThroughTransformer)
        self.register("attribute_mapper", AttributeMapperTransformer)
        self.register("chain", ChainTransformer)
        self.register("conditional", ConditionalTransformer)
        self.register("attribute", AttributeTransformer)


# Global transformer registry instance
transformer_registry = TransformerRegistry()
