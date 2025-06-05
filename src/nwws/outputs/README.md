# NWWS Outputs Package

The outputs package provides pluggable output handlers for the NWWS2MQTT system. Output handlers are responsible for publishing processed weather data to various destinations such as MQTT brokers, databases, console output, and custom endpoints.

## Overview

The outputs system implements a flexible, extensible architecture that allows weather data to be published to multiple destinations simultaneously. Each output handler is independent and can be configured with specific settings, error handling strategies, and performance optimizations.

## Architecture

All output handlers implement the base `Output` interface from the pipeline framework:

```python
from nwws.pipeline.outputs import Output
from nwws.pipeline.types import PipelineEvent

class MyOutput(Output):
    def __init__(self, output_id: str, config: dict):
        super().__init__(output_id)
        self.config = config
    
    async def publish(self, event: PipelineEvent) -> bool:
        # Publish event to destination
        return True
    
    async def connect(self) -> None:
        # Establish connection to destination
        pass
    
    async def disconnect(self) -> None:
        # Clean up resources
        pass
```

## Available Output Handlers

### ConsoleOutput

Simple output handler that prints structured JSON data to stdout, primarily used for development and debugging.

**Key Features:**
- JSON formatted output with syntax highlighting
- Configurable verbosity levels
- Optional timestamp prefixing
- Error highlighting for failed events

**Usage Example:**
```python
from nwws.outputs import ConsoleOutput

# Create console output with default settings
console = ConsoleOutput("console-output")

# Create with custom formatting
console = ConsoleOutput(
    output_id="debug-console",
    config={
        "pretty_print": True,
        "include_metadata": True,
        "color_output": True,
        "timestamp_format": "%Y-%m-%d %H:%M:%S"
    }
)

# Publish event
await console.publish(weather_event)
```

**Configuration Options:**
- `pretty_print`: Enable pretty-printed JSON (default: True)
- `include_metadata`: Include pipeline metadata in output (default: False)
- `color_output`: Enable colored JSON output (default: True)
- `timestamp_format`: Timestamp format string (default: ISO format)
- `max_line_length`: Maximum line length for output wrapping

**Environment Variables:**
```bash
CONSOLE_PRETTY_PRINT=true
CONSOLE_INCLUDE_METADATA=false
CONSOLE_COLOR_OUTPUT=true
CONSOLE_TIMESTAMP_FORMAT="%Y-%m-%d %H:%M:%S"
```

### MQTTOutput

Production-ready MQTT client for publishing weather data to MQTT brokers with comprehensive connection management and error handling.

**Key Features:**
- Automatic reconnection with exponential backoff
- Configurable QoS levels and message retention
- Topic templating with dynamic values
- Connection pooling and session management
- SSL/TLS support with certificate validation
- Message queuing for offline periods

**Usage Example:**
```python
from nwws.outputs import MQTTOutput, MQTTConfig

# Create MQTT configuration
config = MQTTConfig(
    broker="mqtt.example.com",
    port=1883,
    username="weather_user",
    password="secure_password",
    topic_prefix="nwws",
    qos=1,
    retain=False,
    client_id="nwws2mqtt-instance-1"
)

# Create MQTT output
mqtt = MQTTOutput("mqtt-primary", config)

# Connect and publish
await mqtt.connect()
await mqtt.publish(weather_event)
```

**Configuration Options:**
```python
@dataclass
class MQTTConfig:
    broker: str                          # MQTT broker hostname
    port: int = 1883                     # MQTT broker port
    username: str | None = None          # Authentication username
    password: str | None = None          # Authentication password
    topic_prefix: str = "nwws"           # Base topic prefix
    qos: int = 1                         # Quality of Service (0, 1, or 2)
    retain: bool = False                 # Message retention flag
    client_id: str | None = None         # MQTT client identifier
    keepalive: int = 60                  # Keepalive interval in seconds
    clean_session: bool = True           # Clean session flag
    max_inflight: int = 20               # Maximum in-flight messages
    reconnect_delay: float = 5.0         # Initial reconnection delay
    max_reconnect_delay: float = 300.0   # Maximum reconnection delay
    ssl_enabled: bool = False            # Enable SSL/TLS
    ssl_ca_certs: str | None = None      # CA certificate file path
    ssl_certfile: str | None = None      # Client certificate file
    ssl_keyfile: str | None = None       # Client private key file
```

**Environment Variables:**
```bash
MQTT_BROKER=mqtt.example.com
MQTT_PORT=1883
MQTT_USERNAME=weather_user
MQTT_PASSWORD=secure_password
MQTT_TOPIC_PREFIX=nwws
MQTT_QOS=1
MQTT_RETAIN=false
MQTT_CLIENT_ID=nwws2mqtt-client
MQTT_SSL_ENABLED=false
```

**Topic Structure:**
Topics are automatically generated based on weather product metadata:
```
{topic_prefix}/{product_type}/{source}/{awipsid}
# Examples:
nwws/forecast/KBOU/FXUS61
nwws/warning/KDEN/WWUS81
nwws/observation/KGJT/METAR
```

**Message Format:**
```json
{
  "id": "FXUS61KBOU20231215120000",
  "awipsid": "FXUS61",
  "source": "KBOU",
  "wmo_id": "FXUS61KBOU",
  "timestamp": "2023-12-15T12:00:00Z",
  "product_type": "forecast",
  "text_content": "Weather forecast text...",
  "metadata": {
    "urgency": "routine",
    "certainty": "likely",
    "geographic_scope": "local"
  },
  "geographic_data": {
    "coordinates": [-105.0178, 39.7392],
    "geohash": "9xj648",
    "counties": ["CO-013", "CO-059"],
    "zones": ["COZ040", "COZ039"]
  }
}
```

### DatabaseOutput

Persistent storage output handler for archiving weather data to relational databases with optimized batch operations.

**Key Features:**
- Support for PostgreSQL, MySQL, and SQLite
- Batch insert operations for high throughput
- Automatic table creation and schema migration
- Connection pooling with health monitoring
- Transactional integrity for data consistency
- Configurable retention policies

**Usage Example:**
```python
from nwws.outputs import DatabaseOutput, DatabaseConfig

# Create database configuration
config = DatabaseConfig(
    connection_string="postgresql://user:pass@localhost:5432/weather",
    table_name="weather_products",
    batch_size=100,
    flush_interval=30.0,
    create_tables=True
)

# Create database output
database = DatabaseOutput("db-archive", config)

# Connect and publish
await database.connect()
await database.publish(weather_event)
```

**Configuration Options:**
```python
@dataclass
class DatabaseConfig:
    connection_string: str               # Database connection URL
    table_name: str = "weather_products" # Target table name
    batch_size: int = 100                # Batch insert size
    flush_interval: float = 30.0         # Flush interval in seconds
    max_retries: int = 3                 # Connection retry attempts
    retry_delay: float = 5.0             # Retry delay in seconds
    create_tables: bool = True           # Auto-create tables
    pool_size: int = 5                   # Connection pool size
    max_overflow: int = 10               # Pool overflow size
    pool_timeout: float = 30.0           # Pool checkout timeout
    pool_recycle: int = 3600             # Connection recycle time
```

**Database Schema:**
```sql
CREATE TABLE weather_products (
    id VARCHAR(255) PRIMARY KEY,
    awipsid VARCHAR(10) NOT NULL,
    source VARCHAR(10) NOT NULL,
    wmo_id VARCHAR(255),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    product_type VARCHAR(50),
    text_content TEXT,
    metadata JSONB,
    geographic_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_awipsid (awipsid),
    INDEX idx_source (source),
    INDEX idx_timestamp (timestamp),
    INDEX idx_product_type (product_type)
);
```

**Environment Variables:**
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/weather
DATABASE_TABLE_NAME=weather_products
DATABASE_BATCH_SIZE=100
DATABASE_FLUSH_INTERVAL=30.0
DATABASE_CREATE_TABLES=true
```

## Output Handler Features

### Connection Management

All output handlers implement robust connection management:

```python
from nwws.outputs import MQTTOutput

mqtt = MQTTOutput("mqtt-output", config)

# Connection lifecycle
await mqtt.connect()        # Establish connection
await mqtt.health_check()   # Verify connection health
await mqtt.reconnect()      # Force reconnection
await mqtt.disconnect()     # Clean shutdown

# Connection status
if mqtt.is_connected():
    await mqtt.publish(event)
else:
    logger.warning("Output handler disconnected", handler=mqtt.output_id)
```

### Error Handling and Resilience

Comprehensive error handling with configurable strategies:

```python
from nwws.pipeline.errors import ErrorHandlingStrategy

# Configure error handling
output_config = {
    "error_strategy": ErrorHandlingStrategy.RETRY_WITH_BACKOFF,
    "max_retries": 3,
    "retry_delay": 5.0,
    "circuit_breaker_threshold": 10,
    "circuit_breaker_timeout": 60.0
}

# Error handling in action
try:
    success = await output.publish(event)
    if not success:
        # Handle publication failure
        await output.handle_publish_error(event, error)
except ConnectionError as e:
    # Handle connection failures
    await output.handle_connection_error(e)
```

### Performance Monitoring

Built-in metrics collection for monitoring output performance:

```python
from nwws.metrics import MetricsCollector

# Metrics are automatically collected
metrics = await output.get_performance_metrics()
print(f"Messages published: {metrics['published_count']}")
print(f"Success rate: {metrics['success_rate']:.2%}")
print(f"Average latency: {metrics['avg_latency_ms']:.2f}ms")

# Custom metrics
with output.timer("custom_operation"):
    await perform_custom_operation()
```

### Batch Processing

Efficient batch operations for high-throughput scenarios:

```python
from typing import List
from nwws.pipeline.types import PipelineEvent

# Batch publishing
events: List[PipelineEvent] = [...]
results = await output.publish_batch(events)

# Check results
for i, success in enumerate(results):
    if not success:
        logger.error("Failed to publish event", event_id=events[i].metadata.event_id)
```

## Configuration Integration

### Pipeline Configuration

Output handlers are typically configured in the pipeline configuration:

```yaml
outputs:
  - type: ConsoleOutput
    config:
      output_id: "debug-console"
      pretty_print: true
      color_output: true
  
  - type: MQTTOutput
    config:
      output_id: "mqtt-primary"
      broker: "mqtt.example.com"
      port: 1883
      topic_prefix: "nwws"
      qos: 1
  
  - type: DatabaseOutput
    config:
      output_id: "archive-db"
      connection_string: "postgresql://user:pass@localhost/weather"
      batch_size: 100
```

### Environment-Based Configuration

```bash
# Multiple output handlers
OUTPUT_HANDLERS=console,mqtt,database

# Handler-specific configuration
CONSOLE_PRETTY_PRINT=true
MQTT_BROKER=mqtt.example.com
DATABASE_URL=postgresql://localhost/weather
```

### Dynamic Configuration

Runtime configuration updates:

```python
from nwws.outputs import MQTTOutput

# Update configuration at runtime
mqtt_output = MQTTOutput("mqtt-primary", initial_config)

# Update broker settings
new_config = mqtt_output.config.copy(update={
    "broker": "new-broker.example.com",
    "port": 8883,
    "ssl_enabled": True
})

await mqtt_output.update_configuration(new_config)
```

## Custom Output Development

### Creating Custom Outputs

Implement the base `Output` interface for custom destinations:

```python
from nwws.pipeline.outputs import Output
from nwws.pipeline.types import PipelineEvent
from typing import Dict, Any
import aiohttp

class WebhookOutput(Output):
    def __init__(self, output_id: str, config: Dict[str, Any]):
        super().__init__(output_id)
        self.webhook_url = config["webhook_url"]
        self.headers = config.get("headers", {})
        self.timeout = config.get("timeout", 30.0)
        self.session: aiohttp.ClientSession | None = None
    
    async def connect(self) -> None:
        """Establish HTTP session."""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout
            )
    
    async def disconnect(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def publish(self, event: PipelineEvent) -> bool:
        """Publish event to webhook endpoint."""
        try:
            if not self.session:
                await self.connect()
            
            # Serialize event data
            payload = {
                "event_id": event.metadata.event_id,
                "timestamp": event.metadata.timestamp.isoformat(),
                "data": event.dict()
            }
            
            # Send HTTP POST request
            async with self.session.post(
                self.webhook_url,
                json=payload
            ) as response:
                response.raise_for_status()
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to publish to webhook",
                output_id=self.output_id,
                error=str(e),
                webhook_url=self.webhook_url
            )
            return False
    
    def is_connected(self) -> bool:
        """Check connection status."""
        return self.session is not None and not self.session.closed
```

### Output Registration

Register custom outputs with the pipeline:

```python
from nwws.pipeline.outputs import OutputRegistry

# Register custom output
OutputRegistry.register("webhook", WebhookOutput)

# Use in configuration
pipeline_config = {
    "outputs": [
        {
            "type": "webhook",
            "config": {
                "output_id": "alerts-webhook",
                "webhook_url": "https://api.example.com/alerts",
                "headers": {"Authorization": "Bearer token123"},
                "timeout": 30.0
            }
        }
    ]
}
```

## Performance Considerations

### Throughput Optimization

- **Batch Operations**: Use batch publishing for high-volume scenarios
- **Connection Pooling**: Maintain persistent connections to reduce overhead
- **Async Operations**: Leverage async/await for concurrent processing
- **Message Queuing**: Buffer messages during temporary outages

### Memory Management

- **Stream Processing**: Process events as streams to minimize memory usage
- **Connection Limits**: Configure appropriate connection pool sizes
- **Message Buffering**: Implement bounded queues to prevent memory leaks
- **Resource Cleanup**: Ensure proper cleanup of connections and resources

### Monitoring and Alerting

```python
# Performance metrics
output_metrics = {
    "published_count": 1500,
    "failed_count": 2,
    "success_rate": 0.9987,
    "avg_latency_ms": 45.2,
    "connection_uptime": 3600.0,
    "queue_size": 0
}

# Health checks
health_status = await output.health_check()
if health_status.status != "healthy":
    logger.warning(
        "Output handler unhealthy",
        output_id=output.output_id,
        status=health_status.status,
        details=health_status.details
    )
```

## Error Handling Strategies

### Retry Logic

```python
from nwws.pipeline.errors import ErrorHandlingStrategy

# Exponential backoff retry
@retry(
    strategy=ErrorHandlingStrategy.RETRY_WITH_BACKOFF,
    max_retries=3,
    initial_delay=1.0,
    max_delay=30.0,
    backoff_factor=2.0
)
async def publish_with_retry(event: PipelineEvent) -> bool:
    return await output.publish(event)
```

### Circuit Breaker

```python
from nwws.utils.circuit_breaker import CircuitBreaker

# Circuit breaker for external services
circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=60.0,
    expected_exception=ConnectionError
)

@circuit_breaker
async def publish_with_circuit_breaker(event: PipelineEvent) -> bool:
    return await output.publish(event)
```

### Dead Letter Queue

```python
from nwws.outputs import DeadLetterQueue

# Handle permanent failures
dead_letter_queue = DeadLetterQueue("failed-events")

async def publish_with_dlq(event: PipelineEvent) -> bool:
    try:
        return await output.publish(event)
    except PermanentError as e:
        await dead_letter_queue.enqueue(event, error=e)
        return False
```

## Testing

### Unit Testing

```python
import pytest
from unittest.mock import AsyncMock, Mock
from nwws.outputs import MQTTOutput

@pytest.mark.asyncio
async def test_mqtt_publish_success():
    # Mock MQTT client
    mock_client = AsyncMock()
    mock_client.publish.return_value = Mock(rc=0)
    
    # Create output with mock client
    output = MQTTOutput("test-mqtt", config)
    output._client = mock_client
    
    # Test publish
    event = create_test_event()
    result = await output.publish(event)
    
    assert result is True
    mock_client.publish.assert_called_once()

@pytest.mark.asyncio
async def test_mqtt_connection_failure():
    # Mock connection failure
    mock_client = AsyncMock()
    mock_client.connect.side_effect = ConnectionError("Connection failed")
    
    output = MQTTOutput("test-mqtt", config)
    output._client = mock_client
    
    # Test connection handling
    with pytest.raises(ConnectionError):
        await output.connect()
```

### Integration Testing

```python
import pytest
from testcontainers.compose import DockerCompose

@pytest.mark.integration
async def test_mqtt_integration():
    # Start MQTT broker in container
    with DockerCompose("tests/fixtures", compose_file_name="mqtt.yml") as compose:
        # Wait for broker to be ready
        mqtt_port = compose.get_service_port("mosquitto", 1883)
        
        # Create real MQTT output
        config = MQTTConfig(
            broker="localhost",
            port=mqtt_port,
            topic_prefix="test"
        )
        output = MQTTOutput("integration-test", config)
        
        # Test real publishing
        await output.connect()
        event = create_test_event()
        result = await output.publish(event)
        
        assert result is True
        await output.disconnect()
```

This outputs package provides a robust, extensible foundation for publishing weather data to various destinations while maintaining high performance and reliability.