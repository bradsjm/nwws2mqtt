#!/usr/bin/env python3
"""Configuration-based pipeline example."""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from nwws.pipeline import (
    PipelineBuilder,
    PipelineEvent,
    PipelineEventMetadata,
    create_pipeline_from_file,
)


@dataclass
class LogEvent(PipelineEvent):
    """Example log event."""

    text: str
    priority: str = "normal"
    level: str = "INFO"


async def main():
    """Run the configuration-based pipeline example."""
    print("=== Configuration-Based Pipeline Example ===\n")

    # Example 1: Load from configuration file
    config_file = Path(__file__).parent / "pipeline_config.yaml"

    if config_file.exists():
        print("Loading pipeline from YAML configuration file...")
        try:
            pipeline = create_pipeline_from_file(config_file)
            print(f"Pipeline '{pipeline.pipeline_id}' loaded successfully!")
            print(f"- Filters: {len(pipeline.filters)}")
            print(f"- Transformer: {pipeline.transformer is not None}")
            print(f"- Outputs: {len(pipeline.outputs)}")
        except Exception as e:
            print(f"Failed to load from config file: {e}")
            pipeline = None
    else:
        print("Config file not found, creating pipeline programmatically...")
        pipeline = None

    # Example 2: Create from dict configuration
    if not pipeline:
        from nwws.pipeline import (
            FilterConfig,
            OutputConfig,
            PipelineConfig,
            TransformerConfig,
        )
        from nwws.pipeline.errors import ErrorHandlingStrategy

        config = PipelineConfig(
            pipeline_id="programmatic-pipeline",
            filters=[
                FilterConfig(
                    filter_type="attribute",
                    filter_id="level-filter",
                    config={
                        "attribute_name": "level",
                        "allowed_values": {"INFO", "WARNING", "ERROR"},
                        "case_sensitive": True,
                    },
                )
            ],
            transformer=TransformerConfig(
                transformer_type="passthrough", transformer_id="pass-through"
            ),
            outputs=[
                OutputConfig(
                    output_type="log", output_id="console", config={"log_level": "info"}
                )
            ],
            error_handling_strategy=ErrorHandlingStrategy.CONTINUE,
            enable_stats=True,
        )

        builder = PipelineBuilder()
        pipeline = builder.build_pipeline(config)
        print("Pipeline created from programmatic configuration!")

    # Start and test the pipeline
    await pipeline.start()

    # Create test events
    events = [
        LogEvent(
            metadata=PipelineEventMetadata(source="app"),
            text="INFO: Application started successfully",
            priority="normal",
            level="INFO",
        ),
        LogEvent(
            metadata=PipelineEventMetadata(source="app"),
            text="WARNING: Low memory detected",
            priority="high",
            level="WARNING",
        ),
        LogEvent(
            metadata=PipelineEventMetadata(source="app"),
            text="DEBUG: Verbose debugging information",
            priority="low",
            level="DEBUG",  # This may be filtered out
        ),
        LogEvent(
            metadata=PipelineEventMetadata(source="system"),
            text="ERROR: Database connection failed",
            priority="critical",
            level="ERROR",
        ),
    ]

    print(f"\nProcessing {len(events)} events through the pipeline:\n")

    for i, event in enumerate(events, 1):
        print(f"Event {i}: [{event.level}] {event.text}")
        try:
            success = await pipeline.process(event)
            if success:
                print("  ✓ Processed successfully")
            else:
                print("  ✗ Filtered out")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        print()

    # Display statistics
    stats = pipeline.get_stats_summary()
    if stats:
        print("Pipeline Statistics:")
        counters = stats.get("counters", {})
        if counters:
            print("- Event counts:")
            for metric, count in counters.items():
                print(f"  {metric}: {count}")

        timers = stats.get("timers", {})
        if timers:
            print("- Processing times:")
            for metric, timer_data in timers.items():
                avg_time = timer_data.get("avg", 0)
                print(f"  {metric}: {avg_time:.2f}ms average")

    # Stop the pipeline
    await pipeline.stop()
    print("\nPipeline stopped.")


if __name__ == "__main__":
    asyncio.run(main())
