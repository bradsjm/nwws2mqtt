# NWWS Receiver Package

The receiver package provides XMPP client functionality for connecting to the NWWS-OI (National Weather Service Weather Wire Service - Open Interface) feed. It handles connection management, message processing, and statistics collection for real-time weather data ingestion.

## Overview

The receiver package implements a robust XMPP client that connects to the NWWS-OI service to receive real-time weather products. It provides automatic reconnection, comprehensive error handling, and detailed statistics collection to ensure reliable data ingestion from the National Weather Service.

## Architecture

The package consists of several key components:

```
receiver/
├── __init__.py          # Package exports
├── config.py            # Configuration models
├── stats.py             # Statistics collection
└── weather_wire.py      # Main XMPP client implementation
```

## Core Components

### WeatherWire

The main XMPP client that handles connection to the NWWS-OI service:

```python
from nwws.receiver import WeatherWire, WeatherWireConfig

# Create configuration
config = WeatherWireConfig(
    username="your_username",
    password="your_password",
    server="nwws-oi.weather.gov",
    port=5222,
    conference_server="conference.nwws-oi.weather.gov"
)

# Create and start client
client = WeatherWire(config)
await client.connect()

# Subscribe to messages
async def handle_message(message: WeatherWireMessage):
    print(f"Received: {message.product_id}")
    print(f"Content: {message.text_content}")

client.subscribe_messages(handle_message)

# Start processing
await client.start_processing()
```

**Key Features:**
- Automatic connection management with exponential backoff
- Conference room joining for weather data feeds
- Message parsing and validation
- Comprehensive error handling and recovery
- Performance monitoring and statistics
- Graceful shutdown with resource cleanup

### WeatherWireMessage

Structured representation of NWWS-OI messages:

```python
from nwws.receiver import WeatherWireMessage

# Message structure
message = WeatherWireMessage(
    message_id="msg_12345",
    product_id="FXUS61KBOU",
    awipsid="FXUS61", 
    source="KBOU",
    wmo_id="FXUS61KBOU",
    timestamp=datetime.now(),
    text_content="Weather forecast content...",
    raw_xml="<message>...</message>",
    metadata={
        "urgency": "routine",
        "certainty": "likely",
        "scope": "public"
    }
)

# Access parsed data
print(f"Product: {message.product_id}")
print(f"Source: {message.source}")
print(f"Type: {message.get_product_type()}")
print(f"Is urgent: {message.is_urgent()}")
```

**Message Features:**
- Automatic parsing of NWWS-OI XML format
- Metadata extraction from message headers
- Product type classification
- Validation of required fields
- Rich accessor methods for common operations

### WeatherWireConfig

Configuration model for XMPP connection parameters:

```python
from nwws.receiver import WeatherWireConfig

config = WeatherWireConfig(
    # Connection settings
    username="nwws_username",           # NWWS-OI username
    password="nwws_password",           # NWWS-OI password  
    server="nwws-oi.weather.gov",       # XMPP server hostname
    port=5222,                          # XMPP server port
    conference_server="conference.nwws-oi.weather.gov",  # Conference server
    
    # Connection behavior
    auto_reconnect=True,                # Enable automatic reconnection
    reconnect_delay=5.0,                # Initial reconnection delay (seconds)
    max_reconnect_delay=300.0,          # Maximum reconnection delay (seconds)
    reconnect_backoff_factor=2.0,       # Backoff multiplier
    max_reconnect_attempts=None,        # Max attempts (None = unlimited)
    
    # Message processing
    message_timeout=30.0,               # Message processing timeout
    max_queue_size=10000,               # Internal message queue size
    enable_message_validation=True,     # Validate incoming messages
    
    # Performance settings
    keepalive_interval=60,              # XMPP keepalive interval
    ping_interval=30,                   # Ping interval for latency monitoring
    connection_timeout=30.0,            # Connection establishment timeout
    
    # Logging and debugging
    log_raw_messages=False,             # Log raw XMPP messages
    log_statistics_interval=60.0,       # Statistics logging interval
    enable_performance_monitoring=True  # Enable performance metrics
)
```

**Environment Variables:**
```bash
NWWS_USERNAME=your_username
NWWS_PASSWORD=your_password
NWWS_SERVER=nwws-oi.weather.gov
NWWS_PORT=5222
NWWS_CONFERENCE_SERVER=conference.nwws-oi.weather.gov
NWWS_AUTO_RECONNECT=true
NWWS_RECONNECT_DELAY=5.0
NWWS_MAX_RECONNECT_DELAY=300.0
NWWS_MESSAGE_TIMEOUT=30.0
NWWS_KEEPALIVE_INTERVAL=60
```

## Connection Management

### Automatic Reconnection

The WeatherWire client implements robust reconnection logic:

```python
# Reconnection is automatic by default
client = WeatherWire(config)

# Monitor connection status
@client.on_connected
async def on_connected():
    print("Connected to NWWS-OI")

@client.on_disconnected  
async def on_disconnected(reason: str):
    print(f"Disconnected: {reason}")
    # Automatic reconnection will begin

@client.on_reconnected
async def on_reconnected(attempt: int):
    print(f"Reconnected after {attempt} attempts")

# Manual connection control
await client.connect()           # Initial connection
await client.disconnect()        # Graceful disconnect
await client.reconnect()         # Force reconnection
```

**Reconnection Strategy:**
- Exponential backoff with configurable parameters
- Jitter to avoid thundering herd problems
- Maximum retry limits with circuit breaker patterns
- Persistent connection state tracking
- Graceful handling of network interruptions

### Connection Health Monitoring

```python
# Check connection status
if client.is_connected():
    print("Client is connected")
    
# Get connection statistics
stats = client.get_connection_stats()
print(f"Uptime: {stats.uptime_seconds}s")
print(f"Reconnections: {stats.reconnection_count}")
print(f"Last ping: {stats.last_ping_ms}ms")

# Health check with diagnostics
health = await client.health_check()
if health.is_healthy:
    print("Connection is healthy")
else:
    print(f"Health issues: {health.issues}")
```

## Message Processing

### Message Flow

1. **Reception**: XMPP messages received from conference room
2. **Parsing**: XML parsing and validation
3. **Transformation**: Convert to WeatherWireMessage objects
4. **Validation**: Check required fields and format
5. **Distribution**: Send to registered message handlers

### Message Handling

```python
from nwws.receiver import WeatherWire, WeatherWireMessage

client = WeatherWire(config)

# Simple message handler
async def basic_handler(message: WeatherWireMessage):
    print(f"Product: {message.product_id}")

# Advanced message handler with error handling
async def advanced_handler(message: WeatherWireMessage):
    try:
        # Process the message
        if message.is_urgent():
            await process_urgent_message(message)
        else:
            await process_routine_message(message)
            
    except Exception as e:
        logger.error("Message processing failed", 
                    product_id=message.product_id,
                    error=str(e))

# Multiple handlers
client.subscribe_messages(basic_handler)
client.subscribe_messages(advanced_handler)

# Conditional handlers
@client.message_handler(condition=lambda msg: msg.source == "KBOU")
async def boulder_handler(message: WeatherWireMessage):
    print(f"Boulder message: {message.product_id}")

@client.message_handler(condition=lambda msg: msg.is_urgent())
async def urgent_handler(message: WeatherWireMessage):
    await send_alert(message)
```

### Message Filtering

```python
from nwws.receiver import MessageFilter

# Built-in filters
source_filter = MessageFilter.by_source(["KBOU", "KDEN", "KGJT"])
product_filter = MessageFilter.by_product_type(["forecast", "warning"])
urgency_filter = MessageFilter.by_urgency(["immediate", "urgent"])

# Combine filters
combined_filter = source_filter & product_filter & urgency_filter

# Apply filter to client
client.add_message_filter(combined_filter)

# Custom filter
def custom_filter(message: WeatherWireMessage) -> bool:
    return (message.source.startswith("K") and 
            len(message.text_content) > 100)

client.add_message_filter(custom_filter)
```

## Statistics Collection

### WeatherWireStatsCollector

Comprehensive statistics collection for monitoring receiver performance:

```python
from nwws.receiver import WeatherWireStatsCollector

# Create stats collector
stats_collector = WeatherWireStatsCollector(client)

# Get current statistics
stats = stats_collector.get_current_stats()
print(f"Messages received: {stats.messages_received}")
print(f"Messages processed: {stats.messages_processed}")  
print(f"Processing rate: {stats.messages_per_minute:.1f}/min")
print(f"Error rate: {stats.error_rate:.2%}")

# Connection statistics
conn_stats = stats.connection_stats
print(f"Connection uptime: {conn_stats.uptime_seconds}s")
print(f"Reconnections: {conn_stats.reconnection_count}")
print(f"Authentication failures: {conn_stats.auth_failures}")

# Performance statistics
perf_stats = stats.performance_stats
print(f"Average latency: {perf_stats.avg_latency_ms:.2f}ms")
print(f"Peak memory usage: {perf_stats.peak_memory_mb:.1f}MB")
print(f"CPU usage: {perf_stats.cpu_percent:.1f}%")
```

### Statistics Events

```python
from nwws.receiver import ReceiverStatsEvent

# Subscribe to statistics events
async def handle_stats(event: ReceiverStatsEvent):
    print(f"Receiver: {event.receiver_id}")
    print(f"Messages/sec: {event.messages_per_second:.2f}")
    print(f"Error rate: {event.error_rate:.2%}")
    
    # Alert on high error rates
    if event.error_rate > 0.05:  # 5% error rate
        await send_alert(f"High error rate: {event.error_rate:.2%}")

stats_collector.subscribe_events(handle_stats)
```

**Available Statistics:**
- **Message Counts**: Received, processed, failed, filtered
- **Performance Metrics**: Processing rate, latency, throughput
- **Connection Stats**: Uptime, reconnections, ping latency
- **Error Statistics**: Error rates, error types, failure reasons
- **Resource Usage**: Memory, CPU, queue depths
- **Product Statistics**: Top sources, product types, AFOS codes

## Error Handling

### Connection Errors

```python
from nwws.receiver.errors import ConnectionError, AuthenticationError

try:
    await client.connect()
except AuthenticationError as e:
    logger.error("Authentication failed", error=str(e))
    # Check credentials
except ConnectionError as e:
    logger.error("Connection failed", error=str(e))
    # Check network connectivity
except Exception as e:
    logger.error("Unexpected error", error=str(e))
```

### Message Processing Errors

```python
from nwws.receiver.errors import MessageParsingError, ValidationError

async def robust_message_handler(message: WeatherWireMessage):
    try:
        # Process message
        await process_weather_data(message)
        
    except MessageParsingError as e:
        logger.warning("Failed to parse message", 
                      message_id=message.message_id,
                      error=str(e))
        # Continue with next message
        
    except ValidationError as e:
        logger.warning("Message validation failed",
                      product_id=message.product_id,
                      error=str(e))
        # Send to error queue
        
    except Exception as e:
        logger.error("Unexpected processing error",
                    message_id=message.message_id,
                    error=str(e))
        # Re-raise for error handling strategy
        raise
```

### Error Recovery Strategies

```python
from nwws.receiver import ErrorRecoveryStrategy

# Configure error recovery
recovery_config = {
    "max_consecutive_errors": 10,
    "error_window_seconds": 60,
    "recovery_actions": [
        ErrorRecoveryStrategy.RECONNECT,
        ErrorRecoveryStrategy.RESTART_PROCESSING,
        ErrorRecoveryStrategy.CIRCUIT_BREAKER
    ]
}

client.configure_error_recovery(recovery_config)

# Custom error recovery
@client.error_recovery_handler
async def custom_recovery(error_context):
    if error_context.consecutive_errors > 5:
        # Restart connection
        await client.reconnect()
    elif error_context.error_rate > 0.1:
        # Enable circuit breaker
        client.enable_circuit_breaker(timeout=300)
```

## Performance Optimization

### Memory Management

```python
# Configure memory limits
client.configure_memory_management({
    "max_message_queue_size": 10000,
    "message_retention_seconds": 300,
    "enable_message_compression": True,
    "gc_interval_seconds": 60
})

# Monitor memory usage
memory_stats = client.get_memory_stats()
if memory_stats.usage_mb > 512:  # 512MB threshold
    logger.warning("High memory usage", usage_mb=memory_stats.usage_mb)
    await client.cleanup_old_messages()
```

### Processing Optimization

```python
# Configure processing settings
client.configure_processing({
    "worker_pool_size": 4,          # Parallel message processors
    "batch_processing": True,        # Process messages in batches
    "batch_size": 50,               # Messages per batch
    "processing_timeout": 30.0,     # Per-message timeout
    "enable_async_processing": True  # Async message handling
})

# Optimize for high throughput
client.enable_high_throughput_mode({
    "buffer_size": 1000,
    "flush_interval": 1.0,
    "compression_enabled": True,
    "validation_level": "basic"  # Reduced validation for speed
})
```

## Integration Examples

### Pipeline Integration

```python
from nwws.receiver import WeatherWire
from nwws.pipeline import Pipeline

# Create receiver and pipeline
receiver = WeatherWire(receiver_config)
pipeline = Pipeline(pipeline_config)

# Connect receiver to pipeline
async def pipeline_handler(message: WeatherWireMessage):
    # Convert to pipeline event
    event = create_pipeline_event(message)
    
    # Process through pipeline
    result = await pipeline.process(event)
    
    if not result.success:
        logger.error("Pipeline processing failed",
                    product_id=message.product_id,
                    error=result.error)

receiver.subscribe_messages(pipeline_handler)

# Start both components
await receiver.connect()
await pipeline.start()
```

### Metrics Integration

```python
from nwws.receiver import WeatherWire
from nwws.metrics import MetricsCollector

receiver = WeatherWire(config)
metrics = MetricsCollector()

# Track receiver metrics
@receiver.on_message_received
async def track_message_metrics(message: WeatherWireMessage):
    metrics.increment("messages_received_total", 
                     labels={"source": message.source})
    
    metrics.set_gauge("last_message_timestamp", 
                     message.timestamp.timestamp())

@receiver.on_connection_status_change
async def track_connection_metrics(connected: bool):
    metrics.set_gauge("connection_status", 1.0 if connected else 0.0)

# Performance timing
@receiver.message_handler
async def timed_processing(message: WeatherWireMessage):
    with metrics.timer("message_processing_duration_ms"):
        await process_message(message)
```

## Testing Support

### Mock Receiver

```python
from nwws.receiver.testing import MockWeatherWire, MockMessage

# Create mock receiver for testing
mock_receiver = MockWeatherWire()

# Inject test messages
test_message = MockMessage(
    product_id="TEST123",
    source="KTEST",
    text_content="Test weather content"
)

await mock_receiver.inject_message(test_message)

# Test message handlers
handler_called = False

async def test_handler(message):
    global handler_called
    handler_called = True
    assert message.product_id == "TEST123"

mock_receiver.subscribe_messages(test_handler)
await mock_receiver.process_pending_messages()
assert handler_called
```

### Integration Testing

```python
import pytest
from testcontainers import DockerContainer

@pytest.mark.integration
async def test_real_nwws_connection():
    # Use test NWWS-OI server (if available)
    config = WeatherWireConfig(
        username="test_user",
        password="test_pass", 
        server="test-nwws-oi.weather.gov"
    )
    
    client = WeatherWire(config)
    
    try:
        await client.connect()
        assert client.is_connected()
        
        # Wait for test message
        message_received = False
        
        async def test_handler(message):
            nonlocal message_received
            message_received = True
            
        client.subscribe_messages(test_handler)
        
        # Wait for message with timeout
        await asyncio.wait_for(
            wait_for_condition(lambda: message_received),
            timeout=30.0
        )
        
        assert message_received
        
    finally:
        await client.disconnect()
```

## Security Considerations

### Authentication

```python
from nwws.receiver.security import SecureCredentialStore

# Secure credential management
credential_store = SecureCredentialStore()
credentials = credential_store.get_credentials("nwws-oi")

config = WeatherWireConfig(
    username=credentials.username,
    password=credentials.password,
    # Never log passwords
    log_connection_details=False
)
```

### Connection Security

```python
# Enable TLS if supported
config = WeatherWireConfig(
    server="nwws-oi.weather.gov",
    port=5223,  # TLS port
    use_tls=True,
    verify_certificates=True,
    ca_cert_file="/path/to/ca-cert.pem"
)
```

## Best Practices

1. **Credential Security**: Never log passwords or store credentials in code
2. **Connection Resilience**: Always enable auto-reconnection for production
3. **Error Handling**: Implement comprehensive error handling and recovery
4. **Performance Monitoring**: Monitor connection health and message processing rates
5. **Resource Management**: Configure appropriate queue sizes and timeouts
6. **Logging**: Use structured logging with appropriate log levels
7. **Testing**: Test with mock data and integration tests
8. **Documentation**: Document custom message handlers and filters

## Troubleshooting

### Common Issues

**Connection Failures:**
```python
# Check credentials and network
if not client.is_connected():
    stats = client.get_connection_stats()
    if stats.auth_failures > 0:
        logger.error("Authentication failures detected")
    if stats.network_errors > 0:
        logger.error("Network connectivity issues")
```

**High Memory Usage:**
```python
# Monitor and cleanup
memory_stats = client.get_memory_stats()
if memory_stats.usage_mb > threshold:
    await client.cleanup_resources()
    await client.force_garbage_collection()
```

**Message Processing Delays:**
```python
# Check queue depth and processing rate
stats = client.get_processing_stats()
if stats.queue_depth > 1000:
    logger.warning("High message queue depth")
if stats.processing_rate < expected_rate:
    logger.warning("Low processing rate")
```

This receiver package provides a robust foundation for reliable ingestion of real-time weather data from the NWWS-OI service.