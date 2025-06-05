# NWWS Models Package

The models package provides data structures, configuration management, and type definitions for the NWWS2MQTT system. It contains Pydantic models for configuration validation, weather data structures, and event definitions used throughout the application.

## Overview

The models package serves as the foundation for data modeling in NWWS2MQTT, providing:
- **Configuration Models**: Validated application settings and parameters
- **Weather Data Models**: Structured representations of weather products and metadata
- **Event Models**: Pipeline event definitions and message structures
- **Type Safety**: Comprehensive type annotations and runtime validation

## Architecture

The package is organized into logical modules:

```
models/
├── __init__.py          # Package exports
├── config.py            # Application configuration models
├── events/              # Pipeline event models
│   ├── __init__.py
│   ├── base.py          # Base event classes
│   ├── pipeline.py      # Pipeline-specific events
│   └── weather.py       # Weather data events
└── weather/             # Weather data models
    ├── __init__.py
    ├── base.py          # Base weather models
    ├── products.py      # Weather product models
    └── metadata.py      # Product metadata models
```

## Core Components

### Configuration Models

The configuration system uses Pydantic for validation and type safety:

```python
from nwws.models import Config

# Load configuration from environment
config = Config()

# Access typed configuration values
print(f"NWWS Server: {config.nwws.server}")
print(f"MQTT Broker: {config.mqtt.broker}")
print(f"Log Level: {config.logging.level}")
```

**Key Configuration Sections:**
- **NWWS Settings**: Connection parameters for NWWS-OI service
- **MQTT Configuration**: Broker settings and publishing options
- **Pipeline Settings**: Filter, transformer, and output configurations
- **Logging Configuration**: Log levels, formatters, and output destinations
- **Metrics Settings**: Prometheus endpoint and collection intervals

### Weather Data Models

Structured representations of weather products and associated metadata:

```python
from nwws.models.weather import WeatherProduct, ProductMetadata

# Create weather product
product = WeatherProduct(
    id="FXUS61KBOU",
    awipsid="FXUS61",
    source="KBOU",
    wmo_id="FXUS61",
    text_content="Weather forecast text...",
    timestamp=datetime.now(),
    metadata=ProductMetadata(
        product_type="forecast",
        urgency="routine",
        certainty="likely"
    )
)

# Access structured data
print(f"Product: {product.id}")
print(f"Source: {product.source}")
print(f"Type: {product.metadata.product_type}")
```

**Weather Model Features:**
- **Type Validation**: Automatic validation of field types and constraints
- **Serialization**: JSON serialization for output handlers
- **Metadata Enrichment**: Structured metadata extraction from raw weather data
- **Geographic Data**: Location information and coordinate handling

### Event Models

Pipeline event structures for inter-component communication:

```python
from nwws.models.events import WeatherDataEvent, PipelineMetadata

# Create weather data event
event = WeatherDataEvent(
    product=weather_product,
    metadata=PipelineMetadata(
        event_id="evt_123",
        timestamp=datetime.now(),
        source_stage="receiver",
        processing_start=datetime.now()
    ),
    raw_data=original_message_data
)

# Pipeline processing
if event.should_process():
    processed_event = transformer.transform(event)
    output_handler.publish(processed_event)
```

**Event Model Features:**
- **Immutable Data**: Events are immutable to prevent accidental modification
- **Metadata Tracking**: Comprehensive metadata for debugging and monitoring
- **Type Safety**: Strong typing for all event fields and operations
- **Serialization**: Efficient serialization for inter-process communication

## Configuration Management

### Environment-Based Configuration

The configuration system loads settings from environment variables with sensible defaults:

```python
from nwws.models.config import Config

# Configuration with environment variables
config = Config()

# Override with custom values
config = Config(
    nwws_username="custom_user",
    nwws_password="custom_pass",
    mqtt_broker="custom.broker.com"
)
```

**Configuration Loading Order:**
1. Default values from model definitions
2. Environment variables (with `NWWS_` prefix)
3. Configuration file (if specified)
4. Direct parameter overrides

### Validation and Type Safety

All configuration models include comprehensive validation:

```python
from nwws.models.config import MQTTConfig
from pydantic import ValidationError

try:
    mqtt_config = MQTTConfig(
        broker="mqtt.example.com",
        port=1883,
        qos=2,  # Valid QoS level (0, 1, or 2)
        retain=True
    )
except ValidationError as e:
    print(f"Configuration error: {e}")
```

**Validation Features:**
- **Type Checking**: Runtime type validation for all fields
- **Range Validation**: Numeric ranges and string length constraints
- **Format Validation**: URL, email, and custom format validation
- **Cross-Field Validation**: Dependencies between configuration fields

### Nested Configuration

Complex configuration structures with nested models:

```python
from nwws.models.config import Config

config = Config()

# Access nested configuration
nwws_settings = config.nwws
pipeline_settings = config.pipeline
output_settings = config.outputs

# Modify nested settings
config.pipeline.filters.duplicate_window_seconds = 600
config.mqtt.topic_prefix = "weather"
```

## Data Validation

### Input Validation

Comprehensive validation for all data inputs:

```python
from nwws.models.weather import WeatherProduct
from pydantic import ValidationError

try:
    product = WeatherProduct(
        id="INVALID_ID_TOO_LONG_" * 10,  # Exceeds maximum length
        awipsid="FXUS61",
        source="KBOU",
        timestamp="invalid_timestamp"  # Wrong type
    )
except ValidationError as e:
    for error in e.errors():
        print(f"Field: {error['loc']}, Error: {error['msg']}")
```

**Validation Rules:**
- **Required Fields**: Ensure essential data is present
- **Data Types**: Validate field types and formats
- **Business Rules**: Domain-specific validation logic
- **Length Constraints**: String and collection size limits

### Custom Validators

Domain-specific validation logic:

```python
from pydantic import validator
from nwws.models.weather import WeatherProduct

class WeatherProduct(BaseModel):
    awipsid: str
    wmo_id: str
    
    @validator('awipsid')
    def validate_awipsid(cls, v):
        if not v.isalnum():
            raise ValueError('AWIPS ID must be alphanumeric')
        if len(v) != 6:
            raise ValueError('AWIPS ID must be 6 characters')
        return v.upper()
    
    @validator('wmo_id')
    def validate_wmo_id(cls, v):
        if not v.startswith(('F', 'W', 'A')):
            raise ValueError('Invalid WMO ID prefix')
        return v
```

## Serialization and Deserialization

### JSON Serialization

Efficient JSON serialization for outputs:

```python
from nwws.models.weather import WeatherProduct

# Create product
product = WeatherProduct(...)

# Serialize to JSON
json_data = product.json()
json_dict = product.dict()

# Deserialize from JSON
product_copy = WeatherProduct.parse_raw(json_data)
product_from_dict = WeatherProduct(**json_dict)
```

**Serialization Features:**
- **Custom Encoders**: Handle complex data types (datetime, UUID, etc.)
- **Field Aliases**: Alternative field names for external APIs
- **Exclude Fields**: Omit sensitive or internal fields
- **Include/Exclude**: Fine-grained control over serialized fields

### Database Serialization

Integration with database ORMs:

```python
from sqlalchemy import Column, String, DateTime
from nwws.models.weather import WeatherProduct

class WeatherProductORM(Base):
    __tablename__ = 'weather_products'
    
    id = Column(String, primary_key=True)
    awipsid = Column(String)
    source = Column(String)
    timestamp = Column(DateTime)
    
    @classmethod
    def from_model(cls, product: WeatherProduct):
        return cls(
            id=product.id,
            awipsid=product.awipsid,
            source=product.source,
            timestamp=product.timestamp
        )
    
    def to_model(self) -> WeatherProduct:
        return WeatherProduct(
            id=self.id,
            awipsid=self.awipsid,
            source=self.source,
            timestamp=self.timestamp
        )
```

## Performance Considerations

### Memory Efficiency

Optimized memory usage for high-throughput processing:

```python
from nwws.models.weather import WeatherProduct

# Use __slots__ for memory efficiency
class EfficientWeatherProduct(WeatherProduct):
    __slots__ = ('id', 'awipsid', 'source', 'timestamp')

# Lazy loading for large data
class LazyWeatherProduct(WeatherProduct):
    @property
    def parsed_data(self):
        if not hasattr(self, '_parsed_data'):
            self._parsed_data = self._parse_text_content()
        return self._parsed_data
```

### Validation Performance

Optimized validation for production use:

```python
from pydantic import BaseModel

# Disable validation for trusted internal data
class FastWeatherProduct(WeatherProduct):
    class Config:
        validate_assignment = False  # Skip validation on field assignment
        allow_reuse = True          # Cache validation schemas
```

### Batch Processing

Efficient handling of multiple records:

```python
from typing import List
from nwws.models.weather import WeatherProduct

def process_batch(raw_products: List[dict]) -> List[WeatherProduct]:
    # Use parse_obj_list for batch processing
    return [WeatherProduct.parse_obj(item) for item in raw_products]

def validate_batch(products: List[WeatherProduct]) -> List[ValidationError]:
    errors = []
    for i, product in enumerate(products):
        try:
            product.validate()
        except ValidationError as e:
            errors.append((i, e))
    return errors
```

## Error Handling

### Validation Errors

Comprehensive error handling for validation failures:

```python
from pydantic import ValidationError
from nwws.models.weather import WeatherProduct

def safe_create_product(data: dict) -> WeatherProduct | None:
    try:
        return WeatherProduct(**data)
    except ValidationError as e:
        logger.error(
            "Failed to create weather product",
            validation_errors=e.errors(),
            input_data=data
        )
        return None
```

### Graceful Degradation

Handle partial data gracefully:

```python
from typing import Optional
from nwws.models.weather import WeatherProduct

class PartialWeatherProduct(BaseModel):
    id: str
    awipsid: Optional[str] = None
    source: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def to_complete_product(self) -> WeatherProduct | None:
        if self.is_complete():
            return WeatherProduct(
                id=self.id,
                awipsid=self.awipsid,
                source=self.source,
                timestamp=self.timestamp
            )
        return None
    
    def is_complete(self) -> bool:
        return all([self.id, self.awipsid, self.source, self.timestamp])
```

## Testing Support

### Model Factories

Test data generation utilities:

```python
from datetime import datetime
from nwws.models.weather import WeatherProduct

class WeatherProductFactory:
    @staticmethod
    def create(
        id: str = "FXUS61KBOU",
        awipsid: str = "FXUS61",
        source: str = "KBOU",
        timestamp: datetime | None = None
    ) -> WeatherProduct:
        return WeatherProduct(
            id=id,
            awipsid=awipsid,
            source=source,
            timestamp=timestamp or datetime.now()
        )
    
    @staticmethod
    def create_batch(count: int) -> List[WeatherProduct]:
        return [
            WeatherProductFactory.create(id=f"TEST{i:06d}")
            for i in range(count)
        ]
```

### Mock Models

Test doubles for external dependencies:

```python
from unittest.mock import Mock
from nwws.models.config import Config

def create_mock_config(**overrides) -> Mock:
    mock_config = Mock(spec=Config)
    
    # Default values
    mock_config.nwws.server = "test.server.com"
    mock_config.mqtt.broker = "test.broker.com"
    mock_config.logging.level = "DEBUG"
    
    # Apply overrides
    for key, value in overrides.items():
        setattr(mock_config, key, value)
    
    return mock_config
```

## Best Practices

1. **Immutable Models**: Use frozen models where possible to prevent accidental modification
2. **Validation First**: Always validate external data before processing
3. **Type Annotations**: Use comprehensive type hints for better IDE support
4. **Documentation**: Include docstrings and examples for all models
5. **Version Compatibility**: Design models for backward compatibility
6. **Performance**: Use appropriate validation settings for production
7. **Error Handling**: Provide meaningful error messages and recovery strategies

## Integration Examples

### Pipeline Integration

```python
from nwws.models.events import WeatherDataEvent
from nwws.pipeline import Pipeline

def process_weather_message(raw_message: dict):
    # Create event from raw data
    event = WeatherDataEvent.from_raw_message(raw_message)
    
    # Validate event
    if not event.is_valid():
        logger.warning("Invalid weather event", event_id=event.metadata.event_id)
        return
    
    # Process through pipeline
    pipeline.process(event)
```

### Output Handler Integration

```python
from nwws.models.weather import WeatherProduct
from nwws.outputs import MQTTOutput

def publish_weather_product(product: WeatherProduct, mqtt_output: MQTTOutput):
    # Serialize for output
    json_data = product.json(exclude={'raw_data'})
    
    # Publish to MQTT
    topic = f"weather/{product.source}/{product.awipsid}"
    mqtt_output.publish(topic, json_data)
```

This models package provides the foundation for type-safe, validated data handling throughout the NWWS2MQTT system.