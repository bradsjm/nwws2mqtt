# Pipeline Outputs

This directory contains output implementations for the NWWS2MQTT pipeline system.

## Available Outputs

### ConsoleOutput

Prints pipeline events to the console using Rich formatting.

**Usage:**
```python
from outputs import ConsoleOutput

output = ConsoleOutput(output_id="console", pretty=True)
```

### MQTTOutput

Publishes pipeline events to an MQTT broker with configurable topics and retention.

**Features:**
- Configurable broker connection settings
- Automatic message expiry and cleanup
- Topic structure: `{prefix}/{cccc}/{awipsid}/{product_id}`
- Support for QoS levels and message retention
- Graceful connection handling and reconnection

**Usage:**

#### Direct Configuration
```python
from outputs.mqtt import MQTTOutput, MQTTOutputConfig

config = MQTTOutputConfig(
    broker="localhost",
    port=1883,
    username="mqtt_user",
    password="mqtt_pass",
    topic_prefix="nwws",
    qos=1,
    retain=True,
    message_expiry_minutes=60
)

output = MQTTOutput(output_id="mqtt", config=config)
```

#### From MqttConfig
```python
from models.mqtt_config import MqttConfig
from outputs.mqtt import MQTTOutput

mqtt_config = MqttConfig.from_env()
output = MQTTOutput.from_config("mqtt", mqtt_config)
```

#### Pipeline Integration
```python
from pipeline import PipelineBuilder, OutputConfig
from outputs.mqtt import create_mqtt_output

# Register with pipeline
builder = PipelineBuilder()
builder.output_registry.register("mqtt", create_mqtt_output)

# Use in pipeline configuration
pipeline_config = PipelineConfig(
    outputs=[
        OutputConfig(
            output_type="mqtt",
            output_id="weather_mqtt",
            config={
                "broker": "mqtt.example.com",
                "port": 1883,
                "topic_prefix": "weather",
                "qos": 1,
                "retain": True,
                "username": "weather_user",
                "password": "secure_password"
            }
        )
    ]
)
```

## Configuration

### MQTT Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `broker` | str | Required | MQTT broker hostname or IP |
| `port` | int | 1883 | MQTT broker port |
| `username` | str\|None | None | Authentication username |
| `password` | str\|None | None | Authentication password |
| `topic_prefix` | str | "nwws" | Prefix for all MQTT topics |
| `qos` | int | 1 | Quality of Service level (0, 1, or 2) |
| `retain` | bool | False | Whether to retain messages |
| `client_id` | str | "nwws-oi-pipeline-client" | MQTT client identifier |
| `message_expiry_minutes` | int | 60 | Message expiry time in minutes |

## Topic Structure

MQTT topics follow the pattern:
```
{topic_prefix}/{cccc}/{awipsid}/{product_id}
```

**Example:**
- Prefix: `nwws`
- CCCC: `KBOU` (issuing office)
- AWIPSID: `FXUS61` (product type)
- Product ID: `AFDBOU`

**Result:** `nwws/KBOU/FXUS61/AFDBOU`

## Error Handling

The MQTT output handles various error conditions:

- **Connection failures**: Automatic retry with configurable timeout
- **Broker unavailability**: Graceful degradation with warning logs
- **Message publishing failures**: Error logging with retry capability
- **Configuration errors**: Clear error messages for missing required settings

## Performance Considerations

- **Async operations**: All MQTT operations are non-blocking
- **Message batching**: Can be combined with `BatchOutput` for high-throughput scenarios
- **Connection pooling**: Single connection per output instance
- **Memory management**: Automatic cleanup of expired retained messages

## Examples

See `mqtt_example.py` for detailed usage examples including:
- Direct instantiation
- Configuration from environment
- Pipeline system integration
- Error handling patterns