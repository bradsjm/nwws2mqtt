# NWWS Transformers Package

The transformers package provides data transformation and enrichment capabilities for the NWWS2MQTT system. Transformers are pipeline components that modify, enrich, parse, and restructure weather data events as they flow through the processing pipeline.

## Overview

Transformers are the data processing workhorses of the pipeline system. They take incoming weather events and transform them by:
- Parsing raw weather data into structured formats
- Enriching events with additional metadata and geographic information
- Converting between different data formats and schemas
- Extracting and normalizing key information
- Adding computed fields and derived values

Unlike filters (which accept/reject events) and outputs (which publish events), transformers modify event data and return new or updated events for continued processing.

## Architecture

All transformers implement the base `Transformer` interface from the pipeline framework:

```python
from nwws.pipeline.transformers import Transformer
from nwws.pipeline.types import PipelineEvent

class MyTransformer(Transformer):
    def __init__(self, transformer_id: str = "my-transformer"):
        super().__init__(transformer_id)
    
    async def transform(self, event: PipelineEvent) -> PipelineEvent:
        # Transform event data
        transformed_data = self.process_data(event.data)
        
        # Return new event with updated data
        return event.with_updated_data(transformed_data)
    
    def process_data(self, data: dict) -> dict:
        # Custom transformation logic
        return {**data, "transformed": True}
```

## Available Transformers

### NoaaPortTransformer

Specialized transformer for parsing and enriching NOAA weather products with comprehensive metadata extraction and geographic enrichment.

**Key Features:**
- Parses NOAA text products using the pyiem library
- Extracts WMO headers and AFOS codes
- Geocoding and geographic enrichment
- County and zone information lookup
- Product classification and categorization
- Urgency and certainty determination

**Usage Example:**
```python
from nwws.transformers import NoaaPortTransformer

# Create transformer with default settings
transformer = NoaaPortTransformer("noaa-parser")

# Create with custom configuration
transformer = NoaaPortTransformer(
    transformer_id="noaa-enhanced",
    config={
        "enable_geocoding": True,
        "include_counties": True,
        "include_zones": True,
        "parse_coordinates": True,
        "extract_all_metadata": True,
        "validate_products": True
    }
)

# Transform weather event
transformed_event = await transformer.transform(weather_event)
```

**Configuration Options:**
```python
@dataclass
class NoaaPortConfig:
    enable_geocoding: bool = True        # Enable geographic enrichment
    include_counties: bool = True        # Include county information
    include_zones: bool = True           # Include forecast zone data
    parse_coordinates: bool = True       # Extract coordinate data
    extract_all_metadata: bool = True    # Extract comprehensive metadata
    validate_products: bool = True       # Validate product format
    geocoding_timeout: float = 5.0       # Geocoding operation timeout
    max_retries: int = 3                 # Retry attempts for external services
    cache_size: int = 1000               # Geographic data cache size
    ugc_data_path: str | None = None     # Path to UGC data files
```

**Transformation Process:**
1. **Text Product Parsing**: Uses pyiem to parse NOAA text products
2. **Header Extraction**: Extracts WMO headers, AWIPS IDs, and timestamps
3. **Geographic Processing**: Resolves UGC codes to geographic areas
4. **Coordinate Extraction**: Finds and validates coordinate data
5. **Metadata Enrichment**: Adds product classification and urgency levels
6. **Validation**: Ensures data integrity and completeness

**Output Structure:**
```json
{
  "id": "FXUS61KBOU20231215120000",
  "awipsid": "FXUS61",
  "source": "KBOU",
  "wmo_id": "FXUS61KBOU",
  "timestamp": "2023-12-15T12:00:00Z",
  "text_content": "Original weather text...",
  "parsed_data": {
    "product_type": "forecast",
    "urgency": "routine",
    "certainty": "likely",
    "scope": "public",
    "valid_time": "2023-12-15T18:00:00Z",
    "expire_time": "2023-12-16T06:00:00Z"
  },
  "geographic_data": {
    "coordinates": [
      {"lat": 40.0150, "lon": -105.2705},
      {"lat": 39.7392, "lon": -104.9903}
    ],
    "counties": [
      {"code": "CO-013", "name": "Boulder County"},
      {"code": "CO-059", "name": "Jefferson County"}
    ],
    "zones": [
      {"code": "COZ040", "name": "Boulder and Jefferson Counties"},
      {"code": "COZ039", "name": "Denver Metro Area"}
    ],
    "geohash": ["9xj648", "9xj61b"],
    "bounding_box": {
      "north": 40.0150,
      "south": 39.7392, 
      "east": -104.9903,
      "west": -105.2705
    }
  },
  "metadata": {
    "processing_timestamp": "2023-12-15T12:01:30Z",
    "transformer_id": "noaa-parser",
    "parser_version": "1.23.0",
    "confidence_score": 0.95
  }
}
```

### XmlTransformer

Flexible XML parsing and transformation engine for structured weather data formats including CAP alerts, XML bulletins, and custom schemas.

**Key Features:**
- Schema-aware XML parsing and validation
- XPath-based data extraction
- Namespace handling and resolution
- Custom transformation rules
- Error handling and validation
- Performance-optimized parsing

**Usage Example:**
```python
from nwws.transformers import XmlTransformer

# Create transformer with schema validation
transformer = XmlTransformer(
    transformer_id="xml-parser",
    config={
        "schema_file": "schemas/cap.xsd",
        "validate_xml": True,
        "extract_namespaces": True,
        "transformation_rules": "rules/cap_transform.yaml"
    }
)

# Transform XML event
xml_event = PipelineEvent(data={"xml_content": "<alert>...</alert>"})
transformed_event = await transformer.transform(xml_event)
```

**Configuration Options:**
```python
@dataclass
class XmlTransformerConfig:
    schema_file: str | None = None           # XSD schema file for validation
    validate_xml: bool = True                # Enable XML validation
    extract_namespaces: bool = True          # Extract namespace information
    transformation_rules: str | None = None  # YAML transformation rules file
    xpath_expressions: dict[str, str] = None # Custom XPath extractions
    namespace_mappings: dict[str, str] = None # Namespace prefix mappings
    encoding: str = "utf-8"                  # XML encoding
    parser_options: dict = None              # lxml parser options
    max_file_size: int = 10_000_000         # Maximum XML file size (bytes)
    timeout: float = 30.0                   # Parsing timeout
```

**Transformation Rules:**
```yaml
# cap_transform.yaml - Example CAP alert transformation
extraction_rules:
  alert_id:
    xpath: "//cap:identifier"
    type: "string"
    required: true
  
  urgency:
    xpath: "//cap:urgency"
    type: "string"
    default: "unknown"
  
  coordinates:
    xpath: "//cap:polygon"
    type: "coordinates"
    processor: "parse_polygon"
  
  areas:
    xpath: "//cap:area/cap:areaDesc"
    type: "array"
    item_type: "string"

field_mappings:
  alert_id: "id"
  urgency: "metadata.urgency"
  coordinates: "geographic_data.polygon"
  areas: "geographic_data.areas"

post_processors:
  - name: "normalize_urgency"
    field: "metadata.urgency"
    function: "normalize_urgency_value"
  
  - name: "geocode_areas"
    field: "geographic_data.areas"
    function: "resolve_area_codes"
```

**Custom Processors:**
```python
from nwws.transformers.xml_transformer import XmlProcessor

class CapAlertProcessor(XmlProcessor):
    def parse_polygon(self, polygon_text: str) -> list[tuple[float, float]]:
        """Parse CAP polygon coordinates."""
        coordinates = []
        pairs = polygon_text.strip().split()
        
        for i in range(0, len(pairs), 2):
            if i + 1 < len(pairs):
                lat, lon = float(pairs[i]), float(pairs[i + 1])
                coordinates.append((lat, lon))
        
        return coordinates
    
    def normalize_urgency_value(self, urgency: str) -> str:
        """Normalize urgency values to standard format."""
        urgency_map = {
            "immediate": "immediate",
            "expected": "urgent", 
            "future": "routine",
            "past": "routine",
            "unknown": "routine"
        }
        return urgency_map.get(urgency.lower(), "routine")

# Register custom processor
XmlTransformer.register_processor("cap_alert", CapAlertProcessor)
```

## Transformer Features

### Event Immutability

Transformers work with immutable events to prevent side effects:

```python
async def transform(self, event: PipelineEvent) -> PipelineEvent:
    # Original event is never modified
    original_data = event.data
    
    # Create new data structure
    transformed_data = {
        **original_data,
        "enriched_field": "new_value",
        "metadata": {
            **original_data.get("metadata", {}),
            "transformer": self.transformer_id,
            "processed_at": datetime.now().isoformat()
        }
    }
    
    # Return new event with updated data
    return event.with_updated_data(transformed_data)
```

### Error Handling and Recovery

Robust error handling for transformation failures:

```python
from nwws.pipeline.errors import TransformationError

class RobustTransformer(Transformer):
    async def transform(self, event: PipelineEvent) -> PipelineEvent:
        try:
            # Attempt transformation
            result = await self.complex_transformation(event)
            return result
            
        except ValidationError as e:
            # Handle validation errors gracefully
            self.logger.warning(
                "Validation failed, using fallback",
                transformer_id=self.transformer_id,
                event_id=event.metadata.event_id,
                error=str(e)
            )
            return self.apply_fallback_transformation(event)
            
        except ExternalServiceError as e:
            # Handle external service failures
            if self.config.retry_on_service_error:
                return await self.retry_with_backoff(event)
            else:
                return event  # Pass through unchanged
                
        except Exception as e:
            # Log unexpected errors and re-raise
            self.logger.error(
                "Unexpected transformation error",
                transformer_id=self.transformer_id,
                event_id=event.metadata.event_id,
                error=str(e)
            )
            raise TransformationError(f"Failed to transform event: {e}") from e
```

### Performance Optimization

Efficient transformation for high-throughput scenarios:

```python
from asyncio import Semaphore
from functools import lru_cache

class OptimizedTransformer(Transformer):
    def __init__(self, transformer_id: str):
        super().__init__(transformer_id)
        self.semaphore = Semaphore(10)  # Limit concurrent operations
        self.cache_size = 1000
    
    @lru_cache(maxsize=1000)
    def cached_lookup(self, key: str) -> dict:
        """Cache expensive lookups."""
        return self.expensive_operation(key)
    
    async def transform(self, event: PipelineEvent) -> PipelineEvent:
        async with self.semaphore:  # Limit concurrency
            # Use cached operations where possible
            lookup_result = self.cached_lookup(event.data["key"])
            
            # Batch operations when possible
            if hasattr(self, '_batch_queue'):
                return await self.batch_transform(event)
            
            return await self.single_transform(event)
```

### Conditional Transformations

Apply transformations based on event conditions:

```python
class ConditionalTransformer(Transformer):
    def __init__(self, transformer_id: str):
        super().__init__(transformer_id)
        self.transformation_rules = {
            self.is_forecast: self.transform_forecast,
            self.is_warning: self.transform_warning,
            self.is_observation: self.transform_observation
        }
    
    async def transform(self, event: PipelineEvent) -> PipelineEvent:
        # Apply appropriate transformation based on conditions
        for condition, transform_func in self.transformation_rules.items():
            if condition(event):
                return await transform_func(event)
        
        # Default transformation
        return await self.default_transform(event)
    
    def is_forecast(self, event: PipelineEvent) -> bool:
        return event.data.get("product_type") == "forecast"
    
    def is_warning(self, event: PipelineEvent) -> bool:
        return event.data.get("urgency") in ["immediate", "urgent"]
```

## Configuration Integration

### Pipeline Configuration

Transformers are configured in the pipeline configuration file:

```yaml
transformers:
  - type: NoaaPortTransformer
    config:
      transformer_id: "noaa-parser"
      enable_geocoding: true
      include_counties: true
      include_zones: true
      validation_level: "strict"
  
  - type: XmlTransformer
    config:
      transformer_id: "xml-parser"
      schema_file: "schemas/cap.xsd"
      validate_xml: true
      transformation_rules: "rules/cap_transform.yaml"
  
  - type: CustomTransformer
    config:
      transformer_id: "custom-enricher"
      external_api_url: "https://api.weather.com/v1/geocode"
      timeout: 10.0
      cache_ttl: 3600
```

### Environment-Based Configuration

```bash
# NoaaPort Transformer settings
NOAA_ENABLE_GEOCODING=true
NOAA_INCLUDE_COUNTIES=true  
NOAA_INCLUDE_ZONES=true
NOAA_UGC_DATA_PATH=/data/ugc
NOAA_GEOCODING_TIMEOUT=5.0

# XML Transformer settings
XML_SCHEMA_FILE=schemas/cap.xsd
XML_VALIDATE_XML=true
XML_TRANSFORMATION_RULES=rules/default.yaml
XML_PARSER_TIMEOUT=30.0
```

### Dynamic Configuration

Runtime configuration updates:

```python
# Update transformer configuration
new_config = {
    "enable_geocoding": False,  # Disable for performance
    "include_counties": False,
    "cache_size": 2000         # Increase cache size
}

await transformer.update_configuration(new_config)
```

## Custom Transformer Development

### Creating Custom Transformers

```python
from nwws.pipeline.transformers import Transformer
from nwws.pipeline.types import PipelineEvent
from typing import Dict, Any
import aiohttp

class WeatherApiEnricher(Transformer):
    """Enriches weather data with external API information."""
    
    def __init__(self, transformer_id: str, config: Dict[str, Any]):
        super().__init__(transformer_id)
        self.api_url = config["api_url"]
        self.api_key = config["api_key"]
        self.timeout = config.get("timeout", 10.0)
        self.session: aiohttp.ClientSession | None = None
    
    async def startup(self) -> None:
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
    
    async def shutdown(self) -> None:
        """Clean up resources."""
        if self.session:
            await self.session.close()
    
    async def transform(self, event: PipelineEvent) -> PipelineEvent:
        """Enrich event with external weather data."""
        try:
            # Extract coordinates from event
            coordinates = self.extract_coordinates(event.data)
            if not coordinates:
                return event  # Pass through if no coordinates
            
            # Fetch external data
            external_data = await self.fetch_weather_data(coordinates)
            
            # Merge with existing data
            enriched_data = {
                **event.data,
                "external_weather": external_data,
                "enrichment_metadata": {
                    "source": "weather_api",
                    "timestamp": datetime.now().isoformat(),
                    "transformer": self.transformer_id
                }
            }
            
            return event.with_updated_data(enriched_data)
            
        except Exception as e:
            self.logger.error(
                "Failed to enrich with external data",
                transformer_id=self.transformer_id,
                error=str(e)
            )
            # Return original event on error
            return event
    
    def extract_coordinates(self, data: Dict[str, Any]) -> tuple[float, float] | None:
        """Extract lat/lon coordinates from event data."""
        geo_data = data.get("geographic_data", {})
        coords = geo_data.get("coordinates", [])
        
        if coords and len(coords) > 0:
            if isinstance(coords[0], dict):
                return coords[0].get("lat"), coords[0].get("lon")
            elif isinstance(coords[0], (list, tuple)) and len(coords[0]) >= 2:
                return coords[0][0], coords[0][1]
        
        return None
    
    async def fetch_weather_data(self, coordinates: tuple[float, float]) -> Dict[str, Any]:
        """Fetch additional weather data from external API."""
        lat, lon = coordinates
        
        url = f"{self.api_url}/current"
        params = {
            "lat": lat,
            "lon": lon,
            "key": self.api_key,
            "format": "json"
        }
        
        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()
```

### Transformer Registration

```python
from nwws.pipeline.transformers import TransformerRegistry

# Register custom transformer
TransformerRegistry.register("weather_api_enricher", WeatherApiEnricher)

# Use in configuration
transformer_config = {
    "type": "weather_api_enricher",
    "config": {
        "transformer_id": "api-enricher",
        "api_url": "https://api.weather.com/v1",
        "api_key": "your_api_key",
        "timeout": 15.0
    }
}
```

## Performance Considerations

### Throughput Optimization

- **Async Operations**: Use async/await for I/O operations
- **Connection Pooling**: Maintain persistent connections to external services
- **Caching**: Cache expensive operations and lookups
- **Batch Processing**: Process multiple events together when possible

### Memory Management

- **Stream Processing**: Process events as streams to minimize memory usage
- **Resource Cleanup**: Properly dispose of resources in shutdown methods
- **Cache Limits**: Set appropriate cache sizes to prevent memory leaks
- **Object Pooling**: Reuse expensive objects when possible

### Monitoring and Metrics

```python
from nwws.metrics import MetricsCollector

class InstrumentedTransformer(Transformer):
    def __init__(self, transformer_id: str, metrics: MetricsCollector):
        super().__init__(transformer_id)
        self.metrics = metrics
    
    async def transform(self, event: PipelineEvent) -> PipelineEvent:
        # Track transformation metrics
        self.metrics.increment("transformations_total", 
                              labels={"transformer": self.transformer_id})
        
        with self.metrics.timer("transformation_duration_ms",
                               labels={"transformer": self.transformer_id}):
            try:
                result = await self.do_transform(event)
                
                # Track success
                self.metrics.increment("transformations_success_total",
                                     labels={"transformer": self.transformer_id})
                return result
                
            except Exception as e:
                # Track errors
                self.metrics.increment("transformations_error_total",
                                     labels={"transformer": self.transformer_id,
                                           "error_type": type(e).__name__})
                raise
```

## Testing

### Unit Testing

```python
import pytest
from nwws.transformers import NoaaPortTransformer
from nwws.pipeline.types import PipelineEvent, PipelineEventMetadata

@pytest.mark.asyncio
async def test_noaa_port_transformer():
    # Create transformer
    transformer = NoaaPortTransformer("test-transformer")
    
    # Create test event
    test_data = {
        "text_content": "FXUS61 KBOU 151200\nZFP FORECASTS...",
        "source": "KBOU"
    }
    
    event = PipelineEvent(
        metadata=PipelineEventMetadata(event_id="test-123"),
        data=test_data
    )
    
    # Transform event
    result = await transformer.transform(event)
    
    # Verify transformation
    assert result.data["awipsid"] == "FXUS61"
    assert result.data["source"] == "KBOU"
    assert "parsed_data" in result.data
    assert "geographic_data" in result.data

@pytest.mark.asyncio
async def test_xml_transformer():
    xml_content = """
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
        <identifier>NOAA-NWS-ALERTS-CO-1234567890</identifier>
        <urgency>Immediate</urgency>
        <info>
            <area>
                <areaDesc>Boulder County</areaDesc>
                <polygon>40.0,-105.0 39.9,-105.0 39.9,-104.9 40.0,-104.9 40.0,-105.0</polygon>
            </area>
        </info>
    </alert>
    """
    
    transformer = XmlTransformer("xml-test")
    event = PipelineEvent(
        metadata=PipelineEventMetadata(event_id="xml-test-123"),
        data={"xml_content": xml_content}
    )
    
    result = await transformer.transform(event)
    
    assert result.data["alert_id"] == "NOAA-NWS-ALERTS-CO-1234567890"
    assert result.data["urgency"] == "immediate"
    assert len(result.data["coordinates"]) == 5  # Polygon with 5 points
```

### Integration Testing

```python
@pytest.mark.integration
async def test_transformer_pipeline_integration():
    # Create full pipeline with transformers
    pipeline_config = {
        "transformers": [
            {"type": "NoaaPortTransformer", "config": {"transformer_id": "noaa"}},
            {"type": "XmlTransformer", "config": {"transformer_id": "xml"}}
        ]
    }
    
    pipeline = Pipeline(pipeline_config)
    
    # Test with real weather data
    weather_message = load_test_weather_message()
    event = create_pipeline_event(weather_message)
    
    result = await pipeline.process(event)
    
    assert result.success
    assert result.processed_event.data["transformed"] is True
```

## Best Practices

1. **Immutability**: Never modify input events; always return new events
2. **Error Handling**: Handle errors gracefully and provide fallback behavior
3. **Resource Management**: Properly initialize and clean up resources
4. **Performance**: Use caching and async operations for expensive work
5. **Validation**: Validate inputs and outputs to ensure data integrity
6. **Logging**: Use structured logging with contextual information
7. **Configuration**: Make transformers configurable for different use cases
8. **Testing**: Test transformers with various input scenarios
9. **Documentation**: Document transformation logic and data schemas
10. **Monitoring**: Implement comprehensive metrics and monitoring

This transformers package provides powerful data transformation capabilities that form the core of the NWWS2MQTT processing pipeline, enabling rich data enrichment and format conversion for weather data streams.