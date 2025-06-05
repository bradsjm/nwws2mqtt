# NWWS Pipeline Package

The pipeline package provides a flexible, extensible framework for processing weather data through configurable stages of filters, transformers, and outputs. It implements a robust event-driven architecture with comprehensive error handling, statistics collection, and performance monitoring.

## Overview

The pipeline system is designed to process weather data events through a series of configurable stages:

1. **Filters**: Determine whether events should be processed (early rejection)
2. **Transformers**: Modify, enrich, or restructure event data
3. **Outputs**: Publish processed events to various destinations

Each stage is pluggable and can be configured independently, allowing for flexible data processing workflows.

## Architecture

The pipeline framework consists of several core components:

```
pipeline/
├── __init__.py          # Package exports
├── config.py            # Configuration management
├── core.py              # Core pipeline implementations
├── errors.py            # Error handling and strategies
├── filters.py           # Filter base classes and registry
├── outputs.py           # Output base classes and registry
├── stats.py             # Statistics collection
├── transformers.py      # Transformer base classes and registry
└── types.py             # Core type definitions
```

## Core Components

### Pipeline

The main pipeline processor that orchestrates event flow through all stages:

```python
from nwws.pipeline import Pipeline, PipelineConfig

# Create pipeline configuration
config = PipelineConfig(
    pipeline_id="weather-processing",
    filters=[
        {"type": "DuplicateFilter", "config": {"window_seconds": 300}},
        {"type": "TestMessageFilter", "config": {}}
    ],
    transformers=[
        {"type": "NoaaPortTransformer", "config": {}},
        {"type": "XmlTransformer", "config": {}}
    ],
    outputs=[
        {"type": "MQTTOutput", "config": {"broker": "mqtt.example.com"}},
        {"type": "DatabaseOutput", "config": {"connection_string": "postgresql://..."}}
    ]
)

# Create and start pipeline
pipeline = Pipeline(config)
await pipeline.start()

# Process events
event = WeatherDataEvent(...)
result = await pipeline.process(event)
```

### PipelineManager

High-level manager for multiple pipelines with lifecycle management:

```python
from nwws.pipeline import PipelineManager, PipelineManagerConfig

# Create manager configuration
manager_config = PipelineManagerConfig(
    pipelines=[
        {"name": "forecast-pipeline", "config_file": "forecast.yaml"},
        {"name": "warning-pipeline", "config_file": "warnings.yaml"}
    ],
    global_settings={
        "error_strategy": "continue_on_error",
        "stats_interval": 60
    }
)

# Create and start manager
manager = PipelineManager(manager_config)
await manager.start()

# Process event through all pipelines
await manager.process_event(event)
```

### PipelineEvent

Base event structure for all pipeline processing:

```python
from nwws.pipeline.types import PipelineEvent, PipelineEventMetadata
from datetime import datetime

# Create event metadata
metadata = PipelineEventMetadata(
    event_id="evt_12345",
    timestamp=datetime.now(),
    source_stage="receiver",
    processing_start=datetime.now()
)

# Create pipeline event
event = PipelineEvent(
    metadata=metadata,
    data={"product_id": "FXUS61KBOU", "content": "..."}
)

# Events are immutable and track processing history
processed_event = event.with_stage_completed("filter", metadata={"filtered": False})
```

## Pipeline Stages

### Filters

Filters determine whether events should continue through the pipeline. They implement early rejection logic to improve performance.

**Base Filter Interface:**
```python
from nwws.pipeline.filters import Filter
from nwws.pipeline.types import PipelineEvent

class MyFilter(Filter):
    def __init__(self, filter_id: str = "my-filter"):
        super().__init__(filter_id)
    
    def should_process(self, event: PipelineEvent) -> bool:
        # Return True to continue processing, False to reject
        return True
    
    def get_filter_decision_metadata(self, event: PipelineEvent, *, result: bool) -> dict[str, Any]:
        metadata = super().get_filter_decision_metadata(event, result=result)
        metadata[f"{self.filter_id}_custom_info"] = "additional context"
        return metadata
```

**Filter Registry:**
```python
from nwws.pipeline.filters import FilterRegistry

# Register custom filter
FilterRegistry.register("my_filter", MyFilter)

# Create filter from registry
filter_instance = FilterRegistry.create("my_filter", {"filter_id": "instance-1"})
```

### Transformers

Transformers modify, enrich, or restructure event data. They can add metadata, parse content, or convert formats.

**Base Transformer Interface:**
```python
from nwws.pipeline.transformers import Transformer
from nwws.pipeline.types import PipelineEvent

class MyTransformer(Transformer):
    def __init__(self, transformer_id: str = "my-transformer"):
        super().__init__(transformer_id)
    
    async def transform(self, event: PipelineEvent) -> PipelineEvent:
        # Modify event data
        new_data = self.process_data(event.data)
        
        # Return new event with updated data
        return event.with_updated_data(new_data)
    
    def process_data(self, data: dict) -> dict:
        # Custom data processing logic
        return {**data, "transformed": True}
```

**Transformer Registry:**
```python
from nwws.pipeline.transformers import TransformerRegistry

# Register custom transformer
TransformerRegistry.register("my_transformer", MyTransformer)

# Create transformer from registry
transformer = TransformerRegistry.create("my_transformer", {"transformer_id": "instance-1"})
```

### Outputs

Outputs publish processed events to various destinations such as MQTT brokers, databases, or external APIs.

**Base Output Interface:**
```python
from nwws.pipeline.outputs import Output
from nwws.pipeline.types import PipelineEvent

class MyOutput(Output):
    def __init__(self, output_id: str, config: dict):
        super().__init__(output_id)
        self.config = config
        self.connected = False
    
    async def connect(self) -> None:
        # Establish connection to destination
        self.connected = True
    
    async def disconnect(self) -> None:
        # Clean up resources
        self.connected = False
    
    async def publish(self, event: PipelineEvent) -> bool:
        if not self.connected:
            await self.connect()
        
        try:
            # Publish event to destination
            await self.send_data(event.data)
            return True
        except Exception as e:
            self.logger.error("Failed to publish event", error=str(e))
            return False
    
    def is_connected(self) -> bool:
        return self.connected
```

**Output Registry:**
```python
from nwws.pipeline.outputs import OutputRegistry

# Register custom output
OutputRegistry.register("my_output", MyOutput)

# Create output from registry
output = OutputRegistry.create("my_output", {"output_id": "instance-1", "endpoint": "http://api.example.com"})
```

## Configuration System

### Pipeline Configuration

**YAML Configuration Example:**
```yaml
pipeline:
  pipeline_id: "weather-processing"
  
  filters:
    - type: "DuplicateFilter"
      config:
        filter_id: "duplicate-filter"
        window_seconds: 300.0
    
    - type: "TestMessageFilter"
      config:
        filter_id: "test-filter"
  
  transformers:
    - type: "NoaaPortTransformer"
      config:
        transformer_id: "noaa-parser"
        enable_geocoding: true
    
    - type: "XmlTransformer"
      config:
        transformer_id: "xml-parser"
        validate_schema: true
  
  outputs:
    - type: "MQTTOutput"
      config:
        output_id: "mqtt-primary"
        broker: "mqtt.example.com"
        port: 1883
        topic_prefix: "nwws"
    
    - type: "DatabaseOutput"
      config:
        output_id: "archive-db"
        connection_string: "postgresql://user:pass@localhost/weather"
        batch_size: 100

  settings:
    error_strategy: "continue_on_error"
    stats_interval: 60
    max_concurrent_events: 100
    event_timeout: 30.0
```

**Programmatic Configuration:**
```python
from nwws.pipeline import PipelineConfig, FilterConfig, TransformerConfig, OutputConfig

config = PipelineConfig(
    pipeline_id="my-pipeline",
    filters=[
        FilterConfig(type="DuplicateFilter", config={"window_seconds": 300})
    ],
    transformers=[
        TransformerConfig(type="NoaaPortTransformer", config={})
    ],
    outputs=[
        OutputConfig(type="MQTTOutput", config={"broker": "mqtt.example.com"})
    ]
)
```

### Configuration Loading

```python
from nwws.pipeline.config import load_pipeline_config, create_pipeline_from_file

# Load configuration from file
config = load_pipeline_config("pipeline.yaml")

# Create pipeline directly from file
pipeline = create_pipeline_from_file("pipeline.yaml")

# Load manager configuration
manager_config = load_manager_config("manager.yaml")
manager = create_manager_from_file("manager.yaml")
```

## Error Handling

### Error Handling Strategies

The pipeline supports multiple error handling strategies:

```python
from nwws.pipeline.errors import ErrorHandlingStrategy

class ErrorStrategies:
    FAIL_FAST = "fail_fast"              # Stop on first error
    CONTINUE_ON_ERROR = "continue_on_error"  # Log and continue
    RETRY_ON_ERROR = "retry_on_error"    # Retry failed operations
    DEAD_LETTER_QUEUE = "dead_letter"    # Send failed events to DLQ
```

**Configuration Example:**
```yaml
pipeline:
  settings:
    error_strategy: "continue_on_error"
    max_retries: 3
    retry_delay: 5.0
    dead_letter_queue: "failed-events"
```

### Error Handler

Custom error handling logic:

```python
from nwws.pipeline.errors import PipelineErrorHandler, PipelineError

class CustomErrorHandler(PipelineErrorHandler):
    async def handle_filter_error(self, error: PipelineError, event: PipelineEvent) -> bool:
        # Custom filter error handling
        self.logger.error("Filter error", error=str(error.exception))
        return True  # Continue processing
    
    async def handle_transformer_error(self, error: PipelineError, event: PipelineEvent) -> PipelineEvent | None:
        # Custom transformer error handling
        if isinstance(error.exception, ValidationError):
            # Return original event for validation errors
            return event
        return None  # Skip transformation
    
    async def handle_output_error(self, error: PipelineError, event: PipelineEvent) -> bool:
        # Custom output error handling
        await self.send_to_dead_letter_queue(event, error)
        return False  # Don't retry
```

## Statistics and Monitoring

### Statistics Collection

The pipeline automatically collects comprehensive statistics:

```python
from nwws.pipeline.stats import PipelineStatsCollector

# Access pipeline statistics
stats = await pipeline.get_statistics()
print(f"Events processed: {stats.events_processed}")
print(f"Success rate: {stats.success_rate:.2%}")
print(f"Average processing time: {stats.avg_processing_time_ms:.2f}ms")

# Filter statistics
filter_stats = stats.filter_stats["duplicate-filter"]
print(f"Events filtered: {filter_stats.events_filtered}")
print(f"Filter rate: {filter_stats.filter_rate:.2%}")

# Transformer statistics
transformer_stats = stats.transformer_stats["noaa-parser"]
print(f"Transformations: {transformer_stats.transformations}")
print(f"Transformation errors: {transformer_stats.errors}")

# Output statistics
output_stats = stats.output_stats["mqtt-primary"]
print(f"Published: {output_stats.published}")
print(f"Failed: {output_stats.failed}")
```

### Statistics Events

Pipeline generates statistics events for monitoring:

```python
from nwws.pipeline.stats import PipelineStatsEvent

# Subscribe to statistics events
async def handle_stats_event(event: PipelineStatsEvent):
    print(f"Pipeline: {event.pipeline_id}")
    print(f"Processing rate: {event.events_per_second:.2f}/sec")
    print(f"Error rate: {event.error_rate:.2%}")

pipeline.subscribe_stats_events(handle_stats_event)
```

## Performance Considerations

### Concurrency Control

```python
from nwws.pipeline import PipelineConfig

config = PipelineConfig(
    pipeline_id="high-throughput",
    settings={
        "max_concurrent_events": 500,      # Concurrent event limit
        "event_timeout": 30.0,             # Event processing timeout
        "batch_size": 100,                 # Batch processing size
        "worker_pool_size": 10             # Worker thread pool size
    }
)
```

### Memory Management

```python
# Configure memory limits
config.settings.update({
    "max_queue_size": 10000,           # Event queue size limit
    "event_retention_seconds": 300,    # How long to keep processed events
    "gc_interval": 60,                 # Garbage collection interval
    "memory_threshold_mb": 1024        # Memory usage threshold
})
```

### Performance Monitoring

```python
# Performance metrics
performance = await pipeline.get_performance_metrics()
print(f"CPU usage: {performance.cpu_percent:.1f}%")
print(f"Memory usage: {performance.memory_mb:.1f}MB")
print(f"Queue depth: {performance.queue_depth}")
print(f"Processing latency p99: {performance.latency_p99_ms:.2f}ms")

# Performance alerts
if performance.queue_depth > 1000:
    logger.warning("High queue depth detected", depth=performance.queue_depth)

if performance.latency_p99_ms > 5000:
    logger.warning("High processing latency", latency=performance.latency_p99_ms)
```

## Advanced Features

### Pipeline Chaining

Connect multiple pipelines for complex workflows:

```python
from nwws.pipeline import PipelineChain

# Create pipeline chain
chain = PipelineChain([
    ("preprocessing", preprocess_pipeline),
    ("analysis", analysis_pipeline),
    ("publishing", output_pipeline)
])

# Process through entire chain
result = await chain.process(event)
```

### Conditional Processing

Route events based on conditions:

```python
from nwws.pipeline import ConditionalPipeline

# Create conditional routing
conditional = ConditionalPipeline({
    lambda event: event.data.get("urgency") == "immediate": urgent_pipeline,
    lambda event: event.data.get("type") == "forecast": forecast_pipeline,
    lambda event: True: default_pipeline  # Fallback
})

await conditional.process(event)
```

### Event Streaming

Process continuous event streams:

```python
from nwws.pipeline import EventStream

# Create event stream
stream = EventStream(pipeline)

# Process events asynchronously
async for result in stream.process_events(event_source):
    if result.success:
        logger.info("Event processed", event_id=result.event.metadata.event_id)
    else:
        logger.error("Event failed", error=result.error)
```

## Testing Support

### Pipeline Testing

```python
import pytest
from nwws.pipeline.testing import PipelineTester, MockOutput

@pytest.mark.asyncio
async def test_pipeline_processing():
    # Create test pipeline
    tester = PipelineTester()
    pipeline = tester.create_test_pipeline([
        {"type": "TestFilter", "config": {}},
        {"type": "TestTransformer", "config": {}},
        {"type": "MockOutput", "config": {}}
    ])
    
    # Create test event
    event = tester.create_test_event({"product_id": "TEST123"})
    
    # Process event
    result = await pipeline.process(event)
    
    # Verify results
    assert result.success
    assert result.processed_event.data["transformed"] is True
    
    # Check mock output
    mock_output = pipeline.get_output("mock-output")
    assert len(mock_output.published_events) == 1
```

### Component Testing

```python
from nwws.pipeline.testing import ComponentTester

def test_custom_filter():
    tester = ComponentTester()
    filter_instance = MyFilter("test-filter")
    
    # Test filter logic
    event = tester.create_test_event({"valid": True})
    assert filter_instance.should_process(event) is True
    
    invalid_event = tester.create_test_event({"valid": False})
    assert filter_instance.should_process(invalid_event) is False

def test_custom_transformer():
    tester = ComponentTester()
    transformer = MyTransformer("test-transformer")
    
    # Test transformation
    event = tester.create_test_event({"data": "original"})
    result = await transformer.transform(event)
    
    assert result.data["data"] == "transformed"
    assert result.data["processed_by"] == "test-transformer"
```

## Best Practices

1. **Immutable Events**: Keep events immutable to prevent side effects
2. **Error Handling**: Always handle errors gracefully and provide meaningful messages
3. **Performance**: Monitor pipeline performance and optimize bottlenecks
4. **Configuration**: Use configuration files for complex setups
5. **Testing**: Test each component individually and in integration
6. **Logging**: Use structured logging with contextual information
7. **Monitoring**: Implement comprehensive monitoring and alerting
8. **Documentation**: Document custom components and their configurations

## Integration Examples

### Real-time Weather Processing

```python
# Complete weather processing pipeline
pipeline_config = {
    "pipeline_id": "weather-realtime",
    "filters": [
        {"type": "DuplicateFilter", "config": {"window_seconds": 300}},
        {"type": "TestMessageFilter", "config": {}},
        {"type": "UrgencyFilter", "config": {"min_urgency": "routine"}}
    ],
    "transformers": [
        {"type": "NoaaPortTransformer", "config": {"enable_geocoding": True}},
        {"type": "GeographicEnrichment", "config": {"include_counties": True}},
        {"type": "MetadataExtractor", "config": {"extract_all": True}}
    ],
    "outputs": [
        {"type": "MQTTOutput", "config": {"broker": "mqtt.weather.gov", "topic_prefix": "nwws"}},
        {"type": "DatabaseOutput", "config": {"table": "weather_products"}},
        {"type": "WebhookOutput", "config": {"url": "https://api.alerts.com/webhook"}}
    ]
}
```

### Multi-tenant Processing

```python
# Pipeline manager for multiple tenants
manager_config = {
    "pipelines": [
        {"name": "tenant-a", "config": tenant_a_config},
        {"name": "tenant-b", "config": tenant_b_config},
        {"name": "shared", "config": shared_config}
    ],
    "routing": {
        "tenant_id_field": "metadata.tenant",
        "default_pipeline": "shared"
    }
}
```

This pipeline package provides a comprehensive framework for building flexible, scalable weather data processing systems with excellent observability and error handling capabilities.