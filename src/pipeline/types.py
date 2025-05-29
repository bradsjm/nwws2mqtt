# pyright: strict
"""Type definitions for the pipeline package."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

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

    event_id: EventId = field(default=str(uuid.uuid4()))
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


@dataclass
class PipelineEvent:
    """Base class for all pipeline events."""

    metadata: PipelineEventMetadata
    """Event metadata for tracking and observability."""

    def with_stage(self, stage: PipelineStage, source: str | None = None) -> PipelineEvent:
        """Create a copy of this event with updated stage information."""
        new_metadata = PipelineEventMetadata(
            event_id=self.metadata.event_id,
            timestamp=time.time(),
            source=source or self.metadata.source,
            stage=stage,
            trace_id=self.metadata.trace_id,
            custom=self.metadata.custom.copy(),
        )
        # Create a copy with new metadata
        event_copy = type(self).__new__(type(self))
        event_copy.__dict__.update(self.__dict__)
        event_copy.metadata = new_metadata
        return event_copy
