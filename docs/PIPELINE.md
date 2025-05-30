# Pipeline Package

A flexible, extensible pipeline system for processing events through configurable filters, transformers, and outputs.

## Overview

The Pipeline package provides a robust framework for building event processing pipelines. It supports:

- **Event-driven architecture** with comprehensive metadata tracking
- **Modular components** that can be mixed and matched
- **Asynchronous processing** for high-performance applications
- **Built-in observability** with statistics and error handling
- **Registry system** for dynamic component discovery
- **Type-safe design** with full Python type hints

## Core Concepts

### Pipeline Architecture

A pipeline processes events through four distinct stages:

```
INGEST → FILTER → TRANSFORM → OUTPUT
```

1. **INGEST**: Events enter the pipeline with metadata
2. **FILTER**: Events are filtered based on configurable criteria
3. **TRANSFORM**: Events are transformed from one format to another
4. **OUTPUT**: Processed events are sent to one or more destinations

### Key Components

- **PipelineEvent**: Base class for all events flowing through pipelines
- **Filter**: Components that determine whether events should continue processing
- **Transformer**: Components that convert events from one format to another
- **Output**: Components that send processed events to external destinations
- **Pipeline**: Core engine that orchestrates event processing
- **PipelineManager**: Manages multiple pipelines with shared event queuing

## Quick Start

### Basic Usage

```python
import asyncio
from dataclasses import dataclass
from pipeline import Pipeline, PipelineEvent, PipelineEventMetadata

# Create a simple event
@dataclass
class TextEvent(PipelineEvent):
    text: str

# Create and run a pipeline
async def main():
    pipeline = Pipeline("my-pipeline")
    await pipeline.start()

    event = TextEvent(
        metadata=PipelineEventMetadata(source="user"),
        text="Hello, Pipeline!"
    )
    await pipeline.process(event)

    await pipeline.stop()

asyncio.run(main())
```
</edits>

<edits>

<old_text>
### Using Components

```python
from pipeline import Filter, Transformer, Output
from pipeline.types import PipelineEvent

# Custom filter
class TextLengthFilter(Filter):
    def __init__(self, min_length: int):
        super().__init__("text-length-filter")
        self.min_length = min_length

    def should_process(self, event: PipelineEvent) -> bool:
        if hasattr(event, 'text'):
            return len(event.text) >= self.min_length
        return True

# Custom transformer
class UppercaseTransformer(Transformer):
    def __init__(self):
        super().__init__("uppercase-transformer")

    def transform(self, event: PipelineEvent) -> PipelineEvent:
        if hasattr(event, 'text'):
            event.text = event.text.upper()
        return event

# Custom output
class LogOutput(Output):
    def __init__(self):
        super().__init__("log-output")

    async def send(self, event: PipelineEvent) -> None:
        print(f"Output: {getattr(event, 'text', 'Unknown event')}")

# Build pipeline with components
async def main():
    pipeline = Pipeline(
        pipeline_id="text-processor",
        filters=[TextLengthFilter(min_length=5)],
        transformer=UppercaseTransformer(),
        outputs=[LogOutput()]
    )

    await pipeline.start()

    # This will be processed (length >= 5)
    event1 = TextEvent("Hello, World!")
    await pipeline.process(event1)

    # This will be filtered out (length < 5)
    event2 = TextEvent("Hi")
    await pipeline.process(event2)

    await pipeline.stop()
```

### Using Components

```python
from pipeline import Filter, Transformer, Output
from pipeline.types import PipelineEvent

# Custom filter
class TextLengthFilter(Filter):
    def __init__(self, min_length: int):
        super().__init__("text-length-filter")
        self.min_length = min_length

    def should_process(self, event: PipelineEvent) -> bool:
        if hasattr(event, 'text'):
            return len(event.text) >= self.min_length
        return True

# Custom transformer
class UppercaseTransformer(Transformer):
    def __init__(self):
        super().__init__("uppercase-transformer")

    def transform(self, event: PipelineEvent) -> PipelineEvent:
        if hasattr(event, 'text'):
            event.text = event.text.upper()
        return event

# Custom output
class LogOutput(Output):
    def __init__(self):
        super().__init__("log-output")

    async def send(self, event: PipelineEvent) -> None:
        print(f"Output: {getattr(event, 'text', 'Unknown event')}")

# Build pipeline with components
async def main():
    pipeline = Pipeline(
        pipeline_id="text-processor",
        filters=[TextLengthFilter(min_length=5)],
        transformer=UppercaseTransformer(),
        outputs=[LogOutput()]
    )

    await pipeline.start()

    # This will be processed (length >= 5)
    event1 = TextEvent("Hello, World!")
    await pipeline.process(event1)

    # This will be filtered out (length < 5)
    event2 = TextEvent("Hi")
    await pipeline.process(event2)

    await pipeline.stop()
```

## Configuration-Based Setup

### Loading from Configuration Files

```python
from pipeline.config import create_pipeline_from_file, create_manager_from_file

# Create pipeline from JSON/YAML/TOML file
pipeline = create_pipeline_from_file("config/pipeline.yaml")

# Create manager from configuration file
manager = create_manager_from_file("config/manager.json")
```

### Using PipelineBuilder

```python
from pipeline import PipelineBuilder, PipelineConfig, ErrorHandlingStrategy
from pipeline.filters import FilterConfig
from pipeline.transformers import TransformerConfig
from pipeline.outputs import OutputConfig

# Define configuration
config = PipelineConfig(
    pipeline_id="configured-pipeline",
    filters=[
        FilterConfig(filter_type="attribute", filter_id="length-filter", 
                    config={"attribute_name": "text", "allowed_values": {"long_text"}})
    ],
    transformer=TransformerConfig(transformer_type="passthrough", transformer_id="pass"),
    outputs=[
        OutputConfig(output_type="log", output_id="console"),
        OutputConfig(output_type="file", output_id="file-out", 
                    config={"filename": "output.txt"})
    ],
    error_handling_strategy=ErrorHandlingStrategy.RETRY,
    max_retries=3
)

# Build pipeline from config
builder = PipelineBuilder()
pipeline = builder.build_pipeline(config)
```

### Multiple Pipelines with PipelineManager

```python
from pipeline import PipelineManager, PipelineManagerConfig

# Create manager configuration
manager_config = PipelineManagerConfig(
    pipelines=[
        PipelineConfig(pipeline_id="pipeline-1", ...),
        PipelineConfig(pipeline_id="pipeline-2", ...),
    ],
    max_queue_size=5000,
    processing_timeout_seconds=60.0
)

# Start manager
manager = PipelineManager(config=manager_config)
await manager.start()

# Submit events to specific pipelines
await manager.submit_event("pipeline-1", event1)
await manager.submit_event("pipeline-2", event2)

# Or submit to all pipelines
await manager.submit_event_to_all(event3)

await manager.stop()
```

### Configuration File Examples

#### JSON Configuration

```json
{
  "pipeline_id": "example-pipeline",
  "filters": [
    {
      "filter_type": "regex",
      "filter_id": "text-filter",
      "config": {
        "attribute_name": "message",
        "pattern": "^(WARNING|ERROR)",
        "match_mode": "search"
      }
    }
  ],
  "transformer": {
    "transformer_type": "property",
    "transformer_id": "uppercase",
    "config": {
      "property_transforms": {
        "message": "str.upper"
      }
    }
  },
  "outputs": [
    {
      "output_type": "log",
      "output_id": "console",
      "config": {
        "log_level": "info"
      }
    },
    {
      "output_type": "file",
      "output_id": "file-logger",
      "config": {
        "filename": "logs/pipeline.log",
        "mode": "a"
      }
    }
  ],
  "enable_stats": true,
  "enable_error_handling": true,
  "error_handling_strategy": "retry",
  "max_retries": 3,
  "retry_delay_seconds": 1.0
}
```

#### YAML Configuration

```yaml
pipeline_id: "example-pipeline"
filters:
  - filter_type: "attribute"
    filter_id: "priority-filter"
    config:
      attribute_name: "priority"
      allowed_values: ["high", "critical"]
      case_sensitive: false

transformer:
  transformer_type: "attribute_mapper"
  transformer_id: "event-mapper"
  config:
    output_event_type: "AlertEvent"
    attribute_mapping:
      alert_message: "message"
      severity: "priority"
    default_values:
      timestamp: "now"

outputs:
  - output_type: "http"
    output_id: "webhook"
    config:
      url: "https://api.example.com/alerts"
      method: "POST"
      headers:
        Content-Type: "application/json"
        Authorization: "Bearer token123"
      timeout: 30.0

enable_stats: true
enable_error_handling: true
error_handling_strategy: "circuit_breaker"
max_retries: 5
retry_delay_seconds: 2.0
```

#### Pipeline Manager Configuration

```json
{
  "pipelines": [
    {
      "pipeline_id": "alerts-pipeline",
      "filters": [
        {
          "filter_type": "attribute",
          "filter_id": "alert-filter",
          "config": {
            "attribute_name": "type",
            "allowed_values": ["alert", "warning", "error"]
          }
        }
      ],
      "outputs": [
        {
          "output_type": "log",
          "output_id": "alert-logger",
          "config": {
            "log_level": "warning"
          }
        }
      ]
    },
    {
      "pipeline_id": "metrics-pipeline",
      "filters": [
        {
          "filter_type": "attribute",
          "filter_id": "metric-filter",
          "config": {
            "attribute_name": "type",
            "allowed_values": ["metric", "gauge", "counter"]
          }
        }
      ],
      "outputs": [
        {
          "output_type": "file",
          "output_id": "metrics-file",
          "config": {
            "filename": "metrics/pipeline-metrics.log"
          }
        }
      ]
    }
  ],
  "max_queue_size": 5000,
  "processing_timeout_seconds": 60.0,
  "enable_metrics": true
}
```

## Advanced Features

### Event Metadata and Tracing

Every event carries comprehensive metadata for observability:

```python
from pipeline.types import PipelineEventMetadata

metadata = PipelineEventMetadata(
    source="api-endpoint",
    trace_id="trace-123",
    custom={"user_id": "user-456", "priority": "high"}
)

event = CustomEvent(metadata=metadata, data="payload")
```

### Statistics Collection

Monitor pipeline performance with built-in statistics:

```python
from pipeline.stats import StatsCollector

stats_collector = StatsCollector()
pipeline = Pipeline(
    pipeline_id="monitored-pipeline",
    stats_collector=stats_collector
)

# Get statistics
stats = pipeline.get_stats_summary()
print(f"Events processed: {stats.events_processed}")
print(f"Average processing time: {stats.avg_processing_time_ms}ms")
```

### Error Handling

```python
from pipeline.errors import ErrorHandler, ErrorHandlingStrategy

error_handler = ErrorHandler(
    strategy=ErrorHandlingStrategy.RETRY,
    max_retries=3,
    retry_delay_seconds=1.0,
    backoff_multiplier=2.0,
    circuit_breaker_threshold=5,
    circuit_breaker_timeout_seconds=60.0
)

pipeline = Pipeline(
    pipeline_id="resilient-pipeline",
    error_handler=error_handler
)
```

### Component Registries

Register and discover components dynamically:

```python
from pipeline import FilterRegistry, TransformerRegistry, OutputRegistry

# Register custom components
filter_registry = FilterRegistry()
filter_registry.register("custom-filter", CustomFilter)

transformer_registry = TransformerRegistry()
transformer_registry.register("custom-transformer", CustomTransformer)

output_registry = OutputRegistry()
output_registry.register("custom-output", CustomOutput)

# Use in builder
builder = PipelineBuilder(
    filter_registry=filter_registry,
    transformer_registry=transformer_registry,
    output_registry=output_registry
)
```

## API Reference

### Core Classes

#### PipelineEvent

Base class for all pipeline events.

```python
@dataclass
class PipelineEvent:
    metadata: PipelineEventMetadata

    def with_stage(self, stage: PipelineStage, source: str | None = None) -> PipelineEvent:
        """Create a copy with updated stage information."""
```

#### Pipeline

Core pipeline processor.

```python
class Pipeline:
    def __init__(
        self,
        pipeline_id: str,
        filters: list[Filter] | None = None,
        transformer: Transformer | None = None,
        outputs: list[Output] | None = None,
        stats_collector: StatsCollector | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:

    async def start(self) -> None:
        """Start the pipeline and all outputs."""

    async def stop(self) -> None:
        """Stop the pipeline and all outputs."""

    async def process(self, event: PipelineEvent) -> None:
        """Process an event through the pipeline."""
```

#### PipelineManager

Manages multiple pipelines with shared event processing.

```python
class PipelineManager:
    def __init__(self, config: PipelineManagerConfig | None = None) -> None:

    def add_pipeline(self, pipeline: Pipeline) -> None:
        """Add a pipeline to the manager."""

    async def start(self) -> None:
        """Start the manager and all pipelines."""

    async def submit_event(self, pipeline_id: str, event: PipelineEvent) -> None:
        """Submit an event to a specific pipeline."""

    async def submit_event_to_all(self, event: PipelineEvent) -> None:
        """Submit an event to all pipelines."""
```

### Component Interfaces

#### Filter

```python
class Filter(ABC):
    def __init__(self, filter_id: str) -> None:

    @abstractmethod
    def should_process(self, event: PipelineEvent) -> bool:
        """Determine if the event should be processed."""
```

#### Transformer

```python
class Transformer(ABC):
    def __init__(self, transformer_id: str) -> None:

    @abstractmethod
    def transform(self, event: PipelineEvent) -> PipelineEvent:
        """Transform the input event to an output event."""
```

#### Output

```python
class Output(ABC):
    def __init__(self, output_id: str) -> None:

    @abstractmethod
    async def send(self, event: PipelineEvent) -> None:
        """Send the event to the output destination."""

    async def start(self) -> None:
        """Start the output."""

    async def stop(self) -> None:
        """Stop the output."""
```

### Built-in Components

### Filters

- **PassThroughFilter**: Allow all events to pass through
- **AttributeFilter**: Filter events based on attribute values
- **PropertyFilter**: Filter events based on property values (alias for AttributeFilter)
- **RegexFilter**: Filter events based on regex patterns
- **CompositeFilter**: Combine multiple filters with logical operations
- **FunctionFilter**: Filter events using custom functions

### Transformers

- **PassThroughTransformer**: Pass events through unchanged
- **AttributeMapperTransformer**: Map attributes from input to output event
- **ChainTransformer**: Chain multiple transformers together
- **ConditionalTransformer**: Apply different transformations based on conditions
- **AttributeTransformer**: Modify specific attributes of an event
- **PropertyTransformer**: Transform specific event properties (alias for AttributeTransformer)
- **FunctionTransformer**: Transform events using custom functions

### Outputs

- **LogOutput**: Send events to logger
- **FileOutput**: Write events to files (requires aiofiles package)
- **HttpOutput**: Send events to HTTP endpoints (requires aiohttp package)
- **FunctionOutput**: Process events with custom functions
- **BatchOutput**: Batch events and send them in groups
- **ConditionalOutput**: Send events to different outputs based on conditions
- **MulticastOutput**: Send events to multiple outputs simultaneously

## Best Practices

### Event Design

1. **Keep events immutable** when possible
2. **Use meaningful event types** for better type safety
3. **Include relevant metadata** for tracing and debugging
4. **Avoid large payloads** in events to prevent memory issues

### Component Design

1. **Make components stateless** when possible
2. **Handle errors gracefully** and provide meaningful error messages
3. **Log important operations** for debugging
4. **Use dependency injection** for external dependencies

### Pipeline Configuration

1. **Start with simple pipelines** and add complexity gradually
2. **Use configuration files** for production deployments
3. **Monitor pipeline performance** with statistics
4. **Implement circuit breakers** for external dependencies

### Performance Considerations

1. **Batch events** when possible to improve throughput
2. **Use async/await** properly to avoid blocking
3. **Configure appropriate queue sizes** for your workload
4. **Monitor memory usage** in long-running pipelines

## Error Handling

The pipeline system provides comprehensive error handling with multiple strategies:

- **FAIL_FAST**: Stop processing immediately on first error
- **CONTINUE**: Log error and continue processing (default)
- **RETRY**: Automatic retries with configurable exponential backoff
- **CIRCUIT_BREAKER**: Circuit breaker patterns for external dependencies
- **Error event propagation** for monitoring and observability
- **Graceful degradation** strategies for resilient processing

### Error Handling Strategies

```python
from pipeline.errors import ErrorHandlingStrategy

# Available strategies
ErrorHandlingStrategy.FAIL_FAST        # Stop on first error
ErrorHandlingStrategy.CONTINUE         # Log and continue
ErrorHandlingStrategy.RETRY            # Retry with backoff
ErrorHandlingStrategy.CIRCUIT_BREAKER  # Circuit breaker pattern
```

## Observability

Built-in observability features include:

- **Event tracing** with trace IDs
- **Performance metrics** collection
- **Error rate monitoring**
- **Pipeline health checks**

## Examples

### Complete Working Example

See the `examples/` directory for complete working examples:

- `simple_pipeline_example.py` - Basic pipeline with custom components
- `config_pipeline_example.py` - Configuration-based pipeline setup
- `pipeline_config.yaml` - Example YAML configuration file

### Running Examples

```bash
# From the project root
cd examples/

# Run the simple example
python simple_pipeline_example.py

# Run the configuration example
python config_pipeline_example.py
```

## Extension Points

The pipeline system is designed for extensibility:

1. **Custom event types** for domain-specific data
2. **Custom filters** for business logic
3. **Custom transformers** for data processing
4. **Custom outputs** for integration with external systems
5. **Custom error handlers** for specialized error handling
6. **Custom statistics collectors** for metrics

## Dependencies

### Required
- Python 3.12+
- loguru

### Optional
- `aiofiles` - For FileOutput functionality
- `aiohttp` - For HttpOutput functionality  
- `pyyaml` - For YAML configuration file support
- `tomli` - For TOML configuration file support (Python < 3.11)

Install optional dependencies:
```bash
pip install aiofiles aiohttp pyyaml tomli
```

## License

The majority of the pipeline package was written by Claude 4 using prompts written by Jonathan Bradshaw and is licensed under the Apache License 2.0.
</edits>

</edits>
