# pyright: strict
"""Type definitions for the pipeline package."""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Iterator

# Type variables for generic pipeline stages
T = TypeVar("T", bound="PipelineEvent")
U = TypeVar("U", bound="PipelineEvent")

# Type aliases
type EventId = str
type StageId = str
type Timestamp = float
type Metadata = dict[str, Any]


class PipelineStage(Enum):
    """Pipeline processing stages."""

    INGEST = "ingest"
    FILTER = "filter"
    TRANSFORM = "transform"
    OUTPUT = "output"


@dataclass(frozen=True)
class PipelineEventMetadata:
    """Metadata for pipeline events."""

    event_id: EventId = field(default_factory=lambda: str(uuid.uuid4()))
    """Unique identifier for this event."""

    timestamp: Timestamp = field(default_factory=time.time)
    """When this event was created."""

    source: str = "unknown"
    """Source component that created this event."""

    stage: PipelineStage = PipelineStage.INGEST
    """Current pipeline stage."""

    trace_id: str | None = None
    """Trace ID for distributed tracing."""

    custom: Metadata = field(default_factory=dict)
    """Custom metadata fields."""

    def with_custom_updates(self, **updates: Any) -> PipelineEventMetadata:
        """Create a new metadata instance with custom field updates.

        Args:
            **updates: Key-value pairs to add/update in custom metadata.

        Returns:
            New metadata instance with updated custom fields.

        """
        updated_custom = self.custom.copy()
        updated_custom.update(updates)

        return PipelineEventMetadata(
            event_id=self.event_id,
            timestamp=self.timestamp,
            source=self.source,
            stage=self.stage,
            trace_id=self.trace_id,
            custom=updated_custom,
        )

    def with_source_and_stage(
        self, source: str, stage: PipelineStage, **custom_updates: Any
    ) -> PipelineEventMetadata:
        """Create new metadata with updated source, stage, timestamp, and optional custom data.

        Args:
            source: New source component identifier.
            stage: New pipeline stage.
            **custom_updates: Additional custom metadata updates.

        Returns:
            New metadata instance with updates.

        """
        updated_custom = self.custom.copy()
        updated_custom.update(custom_updates)

        return PipelineEventMetadata(
            event_id=self.event_id,
            timestamp=time.time(),  # Update timestamp
            source=source,
            stage=stage,
            trace_id=self.trace_id,
            custom=updated_custom,
        )

    @property
    def age_seconds(self) -> float:
        """Get the age of this event in seconds."""
        return time.time() - self.timestamp

    def get_custom_value(self, key: str, default: Any = None) -> Any:
        """Safely get a value from custom metadata."""
        return self.custom.get(key, default)


@dataclass
class PipelineEvent:
    """Base class for all pipeline events."""

    metadata: PipelineEventMetadata
    """Event metadata for tracking and observability."""

    def with_stage(
        self, stage: PipelineStage, source: str | None = None, **custom_updates: Any
    ) -> PipelineEvent:
        """Create a copy of this event with updated stage information.

        Args:
            stage: New pipeline stage.
            source: Optional new source (defaults to current source).
            **custom_updates: Additional custom metadata to add.

        Returns:
            New event instance with updated metadata.

        """
        new_metadata = self.metadata.with_source_and_stage(
            source=source or self.metadata.source, stage=stage, **custom_updates
        )

        # Create a copy with new metadata
        event_copy = type(self).__new__(type(self))
        event_copy.__dict__.update(self.__dict__)
        event_copy.metadata = new_metadata
        return event_copy

    def with_custom_metadata(self, **updates: Any) -> PipelineEvent:
        """Create a copy of this event with updated custom metadata.

        Args:
            **updates: Custom metadata updates.

        Returns:
            New event instance with updated custom metadata.

        """
        new_metadata = self.metadata.with_custom_updates(**updates)

        # Create a copy with new metadata
        event_copy = type(self).__new__(type(self))
        event_copy.__dict__.update(self.__dict__)
        event_copy.metadata = new_metadata
        return event_copy

    @contextmanager
    def processing_context(
        self, component_id: str, component_type: str
    ) -> Iterator[dict[str, Any]]:
        """Context manager for automatic processing metadata tracking.

        Args:
            component_id: ID of the processing component.
            component_type: Type of component (filter, transformer, output).

        Yields:
            Dictionary for adding processing-specific metadata.

        """
        start_time = time.time()
        processing_metadata: dict[str, Any] = {
            f"{component_type}_applied": component_id,
            f"{component_type}_start_time": start_time,
        }

        try:
            yield processing_metadata
        finally:
            processing_metadata[f"{component_type}_duration_ms"] = (
                time.time() - start_time
            ) * 1000

    def create_derived_event(
        self,
        event_class: type[U],
        source: str,
        stage: PipelineStage | None = None,
        **event_kwargs: Any,
    ) -> U:
        """Create a new event of a different type with inherited metadata.

        Args:
            event_class: Class of the new event to create.
            source: Source component creating the new event.
            stage: Optional stage override (defaults to TRANSFORM).
            **event_kwargs: Additional arguments for the new event constructor.

        Returns:
            New event instance with inherited metadata.

        """
        new_metadata = self.metadata.with_source_and_stage(
            source=source,
            stage=stage or PipelineStage.TRANSFORM,
            derived_from=type(self).__name__,
            transformation_applied=True,
        )

        return event_class(metadata=new_metadata, **event_kwargs)
