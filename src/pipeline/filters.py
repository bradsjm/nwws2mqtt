# pyright: strict
"""Pipeline filters for event processing."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from loguru import logger

from .errors import FilterError

if TYPE_CHECKING:
    from collections.abc import Callable

    from .types import PipelineEvent


class Filter(ABC):
    """Base class for pipeline filters."""

    def __init__(self, filter_id: str) -> None:
        """Initialize the filter with an identifier."""
        self.filter_id = filter_id

    @abstractmethod
    def should_process(self, event: PipelineEvent) -> bool:
        """Determine if the event should be processed.

        Args:
            event: The pipeline event to evaluate.

        Returns:
            True if the event should continue through the pipeline, False to filter out.

        Raises:
            FilterError: If an error occurs during filtering.

        """

    def __call__(self, event: PipelineEvent) -> bool:
        """Make the filter callable."""
        try:
            result = self.should_process(event)
            logger.debug(
                "Filter applied",
                filter_id=self.filter_id,
                event_id=event.metadata.event_id,
                result=result,
            )
        except Exception as e:
            logger.error(
                "Filter error",
                filter_id=self.filter_id,
                event_id=event.metadata.event_id,
                error=str(e),
            )
            msg = f"Filter {self.filter_id} failed: {e}"
            raise FilterError(msg, self.filter_id) from e

        return result


class PassThroughFilter(Filter):
    """Filter that allows all events to pass through."""

    def __init__(self) -> None:
        """Initialize the pass-through filter."""
        super().__init__("passthrough")

    def should_process(self, event: PipelineEvent) -> bool:  # noqa: ARG002
        """Return True."""
        return True


class AttributeFilter(Filter):
    """Filter events based on attribute values."""

    def __init__(
        self,
        filter_id: str,
        attribute_name: str,
        allowed_values: set[Any],
        *,
        case_sensitive: bool = True,
    ) -> None:
        """Initialize the attribute filter.

        Args:
            filter_id: Unique identifier for this filter.
            attribute_name: Name of the attribute to check.
            allowed_values: Set of allowed values for the attribute.
            case_sensitive: Whether string comparisons should be case-sensitive.

        """
        super().__init__(filter_id)
        self.attribute_name = attribute_name
        self.allowed_values = allowed_values
        self.case_sensitive = case_sensitive

    def should_process(self, event: PipelineEvent) -> bool:
        """Check if the event's attribute value is in the allowed set."""
        if not hasattr(event, self.attribute_name):
            logger.warning(
                "Attribute not found in event",
                filter_id=self.filter_id,
                attribute=self.attribute_name,
                event_type=type(event).__name__,
            )
            return False

        value = getattr(event, self.attribute_name)

        if not self.case_sensitive and isinstance(value, str):
            value = value.lower()
            comparison_set = {str(v).lower() for v in self.allowed_values}
        else:
            comparison_set = self.allowed_values

        return value in comparison_set


class RegexFilter(Filter):
    """Filter events based on regex pattern matching."""

    def __init__(
        self,
        filter_id: str,
        attribute_name: str,
        pattern: str,
        match_mode: str = "search",
        flags: int = 0,
    ) -> None:
        """Initialize the regex filter.

        Args:
            filter_id: Unique identifier for this filter.
            attribute_name: Name of the attribute to match against.
            pattern: Regular expression pattern.
            match_mode: Either 'search', 'match', or 'fullmatch'.
            flags: Regex flags (e.g., re.IGNORECASE).

        """
        super().__init__(filter_id)
        self.attribute_name = attribute_name
        self.pattern = pattern
        self.match_mode = match_mode
        self.regex = re.compile(pattern, flags)

    def should_process(self, event: PipelineEvent) -> bool:
        """Check if the event's attribute matches the regex pattern."""
        if not hasattr(event, self.attribute_name):
            logger.warning(
                "Attribute not found in event",
                filter_id=self.filter_id,
                attribute=self.attribute_name,
                event_type=type(event).__name__,
            )
            return False

        value = str(getattr(event, self.attribute_name))

        if self.match_mode == "match":
            return self.regex.match(value) is not None
        if self.match_mode == "fullmatch":
            return self.regex.fullmatch(value) is not None
        # search
        return self.regex.search(value) is not None


class CompositeFilter(Filter):
    """Composite filter that combines multiple filters with logical operations."""

    def __init__(
        self,
        filter_id: str,
        filters: list[Filter],
        operation: str = "and",
    ) -> None:
        """Initialize the composite filter.

        Args:
            filter_id: Unique identifier for this filter.
            filters: List of filters to combine.
            operation: Either 'and' or 'or'.

        """
        super().__init__(filter_id)
        self.filters = filters
        self.operation = operation.lower()

        if self.operation not in ("and", "or"):
            msg = f"Operation must be 'and' or 'or', got: {self.operation}"
            raise ValueError(msg)

    def should_process(self, event: PipelineEvent) -> bool:
        """Apply all filters with the specified logical operation."""
        if not self.filters:
            return True

        if self.operation == "and":
            return all(f.should_process(event) for f in self.filters)
        # or
        return any(f.should_process(event) for f in self.filters)


@dataclass
class FilterConfig:
    """Configuration for a filter."""

    filter_type: str
    """Type of filter to create."""

    filter_id: str
    """Unique identifier for the filter."""

    config: dict[str, Any] = field(default_factory=dict[str, Any])
    """Filter-specific configuration."""


class FilterRegistry:
    """Registry for managing and creating filters."""

    def __init__(self) -> None:
        """Initialize the filter registry."""
        self._filter_factories: dict[str, Callable[..., Filter]] = {}
        self._register_builtin_filters()

    def register(self, filter_type: str, factory: Callable[..., Filter]) -> None:
        """Register a filter factory.

        Args:
            filter_type: String identifier for the filter type.
            factory: Factory function that creates the filter.

        """
        self._filter_factories[filter_type] = factory

    def create(self, config: FilterConfig) -> Filter:
        """Create a filter from configuration.

        Args:
            config: Filter configuration.

        Returns:
            Configured filter instance.

        Raises:
            FilterError: If the filter type is not registered or creation fails.

        """
        if config.filter_type not in self._filter_factories:
            msg = f"Unknown filter type: {config.filter_type}"
            raise FilterError(
                msg,
                config.filter_id,
            )

        try:
            factory = self._filter_factories[config.filter_type]
            return factory(config.filter_id, **config.config)
        except Exception as e:
            msg = f"Failed to create filter {config.filter_id}: {e}"
            raise FilterError(
                msg,
                config.filter_id,
            ) from e

    def get_available_types(self) -> list[str]:
        """Get a list of available filter types."""
        return list(self._filter_factories.keys())

    def _register_builtin_filters(self) -> None:
        """Register built-in filter types."""
        self.register("passthrough", PassThroughFilter)
        self.register("attribute", AttributeFilter)
        self.register("regex", RegexFilter)
        self.register("composite", CompositeFilter)


# Global filter registry instance
filter_registry = FilterRegistry()
