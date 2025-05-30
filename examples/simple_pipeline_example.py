#!/usr/bin/env python3
"""Simple pipeline example demonstrating basic functionality."""

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pipeline import (
    Filter,
    Output,
    Pipeline,
    PipelineEvent,
    PipelineEventMetadata,
    Transformer,
)


@dataclass
class TextEvent(PipelineEvent):
    """Example event containing text data."""
    
    text: str
    priority: str = "normal"


class LengthFilter(Filter):
    """Filter events based on text length."""
    
    def __init__(self, min_length: int = 5):
        super().__init__("length-filter")
        self.min_length = min_length
    
    def should_process(self, event: PipelineEvent) -> bool:
        """Check if event has sufficient text length."""
        if isinstance(event, TextEvent):
            return len(event.text) >= self.min_length
        return True


class UppercaseTransformer(Transformer):
    """Transform text to uppercase."""
    
    def __init__(self):
        super().__init__("uppercase-transformer")
    
    def transform(self, event: PipelineEvent) -> PipelineEvent:
        """Convert text to uppercase."""
        if isinstance(event, TextEvent):
            event.text = event.text.upper()
        return event


class PrintOutput(Output):
    """Output that prints events to console."""
    
    def __init__(self):
        super().__init__("print-output")
    
    async def send(self, event: PipelineEvent) -> None:
        """Print the event."""
        if isinstance(event, TextEvent):
            print(f"[{event.priority.upper()}] {event.text}")
        else:
            print(f"Event: {type(event).__name__}")


async def main():
    """Run the pipeline example."""
    print("=== Simple Pipeline Example ===\n")
    
    # Create pipeline with components
    pipeline = Pipeline(
        pipeline_id="example-pipeline",
        filters=[LengthFilter(min_length=3)],
        transformer=UppercaseTransformer(),
        outputs=[PrintOutput()],
    )
    
    # Start the pipeline
    await pipeline.start()
    
    # Create some test events
    events = [
        TextEvent(
            metadata=PipelineEventMetadata(source="user"),
            text="Hello, World!",
            priority="high"
        ),
        TextEvent(
            metadata=PipelineEventMetadata(source="user"),
            text="Hi",  # This will be filtered out (too short)
            priority="low"
        ),
        TextEvent(
            metadata=PipelineEventMetadata(source="system"),
            text="Pipeline processing example",
            priority="normal"
        ),
    ]
    
    # Process events through the pipeline
    print("Processing events through pipeline:\n")
    
    for i, event in enumerate(events, 1):
        print(f"Processing event {i}: '{event.text}' (priority: {event.priority})")
        try:
            success = await pipeline.process(event)
            if not success:
                print("  -> Event was filtered out")
        except Exception as e:
            print(f"  -> Error processing event: {e}")
        print()
    
    # Get pipeline statistics
    stats = pipeline.get_stats_summary()
    if stats:
        print("Pipeline Statistics:")
        print(f"- Events processed: {stats.get('counters', {})}")
        print(f"- Processing times: {stats.get('timers', {})}")
    
    # Stop the pipeline
    await pipeline.stop()
    print("Pipeline stopped.")


if __name__ == "__main__":
    asyncio.run(main())