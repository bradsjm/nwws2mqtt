# NWWS Utils Package

The utils package provides utility functions, helper classes, and shared components used throughout the NWWS2MQTT system. It contains common functionality for data conversion, geographic processing, logging configuration, and other supporting operations.

## Overview

The utils package serves as a collection of reusable utilities that support the core functionality of NWWS2MQTT. These utilities are designed to be:
- **Reusable**: Common functionality used across multiple packages
- **Reliable**: Well-tested components with comprehensive error handling
- **Efficient**: Optimized for performance in high-throughput scenarios
- **Configurable**: Flexible utilities that can be adapted to different use cases

## Architecture

The package is organized into focused utility modules:

```
utils/
├── __init__.py          # Package exports
├── converters.py        # Data conversion utilities
├── geo_provider.py      # Geographic data provider
├── geohash.py          # Geohash utilities
├── logging_config.py   # Logging configuration
├── topic_builder.py    # Topic construction utilities
└── ugc_loader.py       # UGC data loading
```

## Core Components

### Data Converters

Utilities for converting between different data formats and structures:

```python
from nwws.utils import convert_text_product_to_model

# Convert raw text product to structured model
raw_text = """
FXUS61 KBOU 151200
ZFPBOU
ZONE FORECAST PRODUCT...
"""

weather_model = convert_text_product_to_model(
    text_content=raw_text,
    source="KBOU",
    timestamp=datetime.now()
)

print(f"Product ID: {weather_model.id}")
print(f"AWIPS ID: {weather_model.awipsid}")
print(f"Parsed metadata: {weather_model.metadata}")
```

**Key Features:**
- **Text Product Parsing**: Parse NOAA text products into structured models
- **Format Conversion**: Convert between different weather data formats
- **Metadata Extraction**: Extract and normalize metadata from raw data
- **Validation**: Ensure data integrity during conversion
- **Error Handling**: Graceful handling of malformed or incomplete data

**Conversion Functions:**
- `convert_text_product_to_model()`: Convert text products to weather models
- `normalize_timestamp()`: Normalize various timestamp formats
- `extract_coordinates()`: Extract coordinate data from text
- `parse_ugc_codes()`: Parse UGC (Universal Geographic Code) identifiers
- `standardize_product_id()`: Normalize product identifiers

### Geographic Data Provider

Comprehensive geographic data services for weather location processing:

```python
from nwws.utils import WeatherGeoDataProvider

# Create geo data provider
geo_provider = WeatherGeoDataProvider()

# Geocode location
location_data = await geo_provider.geocode_location("Boulder, CO")
print(f"Coordinates: {location_data.latitude}, {location_data.longitude}")

# Reverse geocode coordinates
place_info = await geo_provider.reverse_geocode(40.0150, -105.2705)
print(f"Location: {place_info.city}, {place_info.state}")

# Get county information
county_data = await geo_provider.get_county_info("CO-013")
print(f"County: {county_data.name}, State: {county_data.state}")

# Get forecast zone information
zone_data = await geo_provider.get_zone_info("COZ040")
print(f"Zone: {zone_data.name}, Type: {zone_data.zone_type}")
```

**Key Features:**
- **Geocoding Services**: Convert addresses to coordinates
- **Reverse Geocoding**: Convert coordinates to location information
- **County Lookup**: Retrieve county data by FIPS codes
- **Zone Information**: Access forecast zone and warning area data
- **Caching**: Efficient caching of geographic lookups
- **Multiple Providers**: Support for different geocoding services

**Geographic Data Types:**
```python
@dataclass
class LocationData:
    latitude: float
    longitude: float
    accuracy: float
    source: str
    timestamp: datetime

@dataclass
class CountyInfo:
    fips_code: str
    name: str
    state: str
    state_code: str
    geometry: dict | None = None

@dataclass
class ZoneInfo:
    zone_code: str
    name: str
    state: str
    zone_type: str  # forecast, warning, fire, etc.
    geometry: dict | None = None
```

### Geohash Utilities

Geohash generation and topic creation for geographic indexing:

```python
from nwws.utils import get_geohash_topics

# Generate geohash topics for coordinates
coordinates = [
    (40.0150, -105.2705),  # Boulder, CO
    (39.7392, -104.9903)   # Denver, CO
]

geohash_topics = get_geohash_topics(
    coordinates=coordinates,
    precisions=[4, 5, 6, 7],  # Different precision levels
    topic_prefix="weather/geo"
)

print("Generated topics:")
for topic in geohash_topics:
    print(f"  {topic}")

# Output:
# weather/geo/9xj6
# weather/geo/9xj64
# weather/geo/9xj648
# weather/geo/9xj648b
# weather/geo/9xj61
# weather/geo/9xj61b
# weather/geo/9xj61bp
# weather/geo/9xj61bpb
```

**Key Features:**
- **Multi-Precision Geohashes**: Generate geohashes at multiple precision levels
- **Topic Generation**: Create MQTT topics from geohash data
- **Coordinate Validation**: Validate coordinate inputs
- **Batch Processing**: Efficiently process multiple coordinate sets
- **Customizable Formats**: Flexible topic naming conventions

**Geohash Functions:**
- `encode_geohash()`: Encode coordinates to geohash string
- `decode_geohash()`: Decode geohash to coordinate bounds
- `get_geohash_neighbors()`: Get adjacent geohash cells
- `geohash_precision_distance()`: Calculate precision level distances
- `validate_coordinates()`: Validate coordinate ranges

### Logging Configuration

Centralized logging configuration with structured output:

```python
from nwws.utils import LoggingConfig

# Create logging configuration
logging_config = LoggingConfig(
    level="INFO",
    format="json",  # or "text"
    output_file="/var/log/nwws2mqtt.log",
    max_file_size="100MB",
    backup_count=5,
    enable_console=True,
    enable_file=True
)

# Apply configuration
logging_config.configure()

# Use structured logging
from loguru import logger

logger.info(
    "Weather product processed",
    product_id="FXUS61KBOU",
    source="KBOU",
    processing_time_ms=45.2,
    success=True
)
```

**Configuration Options:**
```python
@dataclass
class LoggingConfig:
    level: str = "INFO"                    # Log level
    format: str = "json"                   # Output format (json, text)
    output_file: str | None = None         # Log file path
    max_file_size: str = "100MB"          # Maximum file size
    backup_count: int = 5                  # Number of backup files
    enable_console: bool = True            # Enable console output
    enable_file: bool = False              # Enable file output
    enable_syslog: bool = False            # Enable syslog output
    syslog_address: str = "localhost:514"  # Syslog server address
    structured_logging: bool = True        # Enable structured logging
    correlation_id: bool = True            # Include correlation IDs
    performance_logging: bool = False      # Enable performance logging
    sensitive_data_filter: bool = True     # Filter sensitive data
```

**Environment Variables:**
```bash
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/nwws2mqtt.log
LOG_MAX_FILE_SIZE=100MB
LOG_BACKUP_COUNT=5
LOG_ENABLE_CONSOLE=true
LOG_ENABLE_FILE=false
LOG_STRUCTURED_LOGGING=true
```

### Topic Builder

MQTT topic construction utilities with flexible templating:

```python
from nwws.utils import build_topic

# Build topic from weather data
topic = build_topic(
    template="weather/{product_type}/{source}/{awipsid}",
    data={
        "product_type": "forecast",
        "source": "KBOU", 
        "awipsid": "FXUS61"
    }
)
print(topic)  # weather/forecast/KBOU/FXUS61

# Build topic with geographic data
geo_topic = build_topic(
    template="weather/geo/{geohash}/{product_type}",
    data={
        "geohash": "9xj648",
        "product_type": "warning"
    }
)
print(geo_topic)  # weather/geo/9xj648/warning

# Build topic with sanitization
sanitized_topic = build_topic(
    template="weather/{source}/{description}",
    data={
        "source": "KBOU",
        "description": "Heavy Snow & Wind Advisory"
    },
    sanitize=True
)
print(sanitized_topic)  # weather/KBOU/Heavy_Snow_Wind_Advisory
```

**Key Features:**
- **Template-Based Construction**: Flexible topic templates with variable substitution
- **Data Sanitization**: Automatic sanitization of topic components
- **Validation**: Ensure topics conform to MQTT standards
- **Caching**: Cache built topics for performance
- **Custom Formatters**: Pluggable formatting for specific use cases

**Topic Functions:**
- `build_topic()`: Main topic construction function
- `sanitize_topic_component()`: Sanitize individual topic parts
- `validate_topic()`: Validate MQTT topic format
- `extract_topic_variables()`: Extract variables from topic templates
- `normalize_topic_case()`: Normalize topic case conventions

### UGC Data Loader

Universal Geographic Code (UGC) data loading and management:

```python
from nwws.utils import create_ugc_provider

# Create UGC data provider
ugc_provider = await create_ugc_provider(
    data_path="/data/ugc",
    auto_update=True,
    update_interval=86400  # 24 hours
)

# Look up county by FIPS code
county = await ugc_provider.get_county("013", "CO")
print(f"County: {county.name}, State: {county.state}")

# Look up forecast zone
zone = await ugc_provider.get_zone("COZ040")
print(f"Zone: {zone.name}, Type: {zone.zone_type}")

# Get all counties in a state
colorado_counties = await ugc_provider.get_counties_by_state("CO")
print(f"Colorado has {len(colorado_counties)} counties")

# Search by name
search_results = await ugc_provider.search_locations("Boulder")
for result in search_results:
    print(f"Found: {result.name} ({result.type})")
```

**Key Features:**
- **Complete UGC Database**: Counties, zones, parishes, and boroughs
- **Fast Lookup**: Optimized data structures for quick searches
- **Automatic Updates**: Periodic updates from authoritative sources
- **Geographic Relationships**: County-to-zone mappings and boundaries
- **Search Capabilities**: Full-text search across location names

**UGC Data Types:**
```python
@dataclass
class UGCCounty:
    fips_code: str
    name: str
    state: str
    state_fips: str
    timezone: str | None = None
    geometry: dict | None = None

@dataclass
class UGCZone:
    zone_code: str
    name: str
    state: str
    zone_type: str
    counties: list[str] = field(default_factory=list)
    geometry: dict | None = None
```

## Performance Utilities

### Caching Mechanisms

Efficient caching for expensive operations:

```python
from nwws.utils.caching import TTLCache, LRUCache

# Time-based cache
geo_cache = TTLCache(maxsize=1000, ttl=3600)  # 1 hour TTL

@geo_cache.cached
async def expensive_geocode(address: str) -> dict:
    # Expensive geocoding operation
    return await external_geocoding_service(address)

# LRU cache for frequently accessed data
lookup_cache = LRUCache(maxsize=500)

@lookup_cache.cached
def lookup_county_info(fips_code: str) -> dict:
    return county_database.get(fips_code)
```

### Data Validation

Comprehensive validation utilities:

```python
from nwws.utils.validation import (
    validate_coordinates,
    validate_timestamp,
    validate_product_id,
    ValidationError
)

try:
    # Validate geographic coordinates
    lat, lon = validate_coordinates(40.0150, -105.2705)
    
    # Validate timestamp formats
    timestamp = validate_timestamp("2023-12-15T12:00:00Z")
    
    # Validate product identifiers
    product_id = validate_product_id("FXUS61KBOU20231215120000")
    
except ValidationError as e:
    logger.error("Validation failed", error=str(e))
```

### Text Processing

Weather-specific text processing utilities:

```python
from nwws.utils.text import (
    extract_wmo_header,
    parse_awips_id,
    normalize_text_content,
    extract_coordinates_from_text
)

# Extract WMO header from text
header = extract_wmo_header("FXUS61 KBOU 151200\nZONE FORECAST...")
print(f"WMO: {header.wmo_id}, Source: {header.source}")

# Parse AWIPS identifiers
awips = parse_awips_id("FXUS61")
print(f"Product family: {awips.family}, Source: {awips.source}")

# Extract coordinates from weather text
coordinates = extract_coordinates_from_text(
    "Lat/Lon: 40.0150 -105.2705 to 39.7392 -104.9903"
)
print(f"Found {len(coordinates)} coordinate pairs")
```

## Configuration Integration

### Environment-Based Configuration

All utilities support environment-based configuration:

```bash
# Geographic data settings
GEO_DATA_PATH=/data/geographic
GEO_CACHE_SIZE=1000
GEO_CACHE_TTL=3600
GEO_PROVIDER=nominatim

# UGC data settings
UGC_DATA_PATH=/data/ugc
UGC_AUTO_UPDATE=true
UGC_UPDATE_INTERVAL=86400

# Geohash settings
GEOHASH_DEFAULT_PRECISION=6
GEOHASH_TOPIC_PREFIX=weather/geo

# Topic building settings
TOPIC_SANITIZE_DEFAULT=true
TOPIC_CASE_CONVENTION=lower
```

### Configuration Classes

Structured configuration for utilities:

```python
from nwws.utils.config import UtilsConfig

config = UtilsConfig(
    geo_data_path="/data/geographic",
    ugc_data_path="/data/ugc",
    cache_size=1000,
    cache_ttl=3600,
    auto_update_data=True,
    update_interval=86400
)

# Initialize utilities with configuration
geo_provider = WeatherGeoDataProvider(config.geo_config)
ugc_provider = await create_ugc_provider(config.ugc_config)
```

## Error Handling

### Graceful Degradation

Utilities are designed to degrade gracefully when external services are unavailable:

```python
from nwws.utils.errors import GeocodingError, DataUnavailableError

async def robust_geocoding(address: str) -> dict | None:
    try:
        # Primary geocoding service
        return await primary_geocoder.geocode(address)
    except GeocodingError:
        try:
            # Fallback to secondary service
            return await fallback_geocoder.geocode(address)
        except GeocodingError:
            # Use cached data if available
            return cache.get(address)
    except DataUnavailableError:
        logger.warning("Geocoding services unavailable", address=address)
        return None
```

### Error Recovery

Automatic error recovery and retry mechanisms:

```python
from nwws.utils.retry import RetryConfig, with_retry

retry_config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    backoff_factor=2.0,
    retryable_exceptions=[ConnectionError, TimeoutError]
)

@with_retry(retry_config)
async def reliable_data_fetch(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

## Testing Support

### Mock Utilities

Test utilities for mocking external dependencies:

```python
from nwws.utils.testing import (
    MockGeoProvider,
    MockUGCProvider,
    create_test_weather_data
)

# Create mock providers for testing
mock_geo = MockGeoProvider()
mock_geo.add_location("Boulder, CO", 40.0150, -105.2705)

mock_ugc = MockUGCProvider()
mock_ugc.add_county("013", "Boulder County", "CO")

# Generate test weather data
test_data = create_test_weather_data(
    product_type="forecast",
    source="KBOU",
    coordinates=[(40.0150, -105.2705)]
)
```

### Test Data Generators

```python
from nwws.utils.testing import WeatherDataGenerator

generator = WeatherDataGenerator()

# Generate realistic test data
forecast_data = generator.generate_forecast(
    source="KBOU",
    valid_time=datetime.now() + timedelta(hours=6),
    coordinates=[(40.0150, -105.2705)]
)

warning_data = generator.generate_warning(
    source="KBOU",
    urgency="immediate",
    affected_counties=["CO-013", "CO-059"]
)
```

## Performance Considerations

### Memory Optimization

- **Lazy Loading**: Load data only when needed
- **Memory Pools**: Reuse objects to reduce garbage collection
- **Streaming**: Process large datasets as streams
- **Cache Limits**: Set appropriate cache sizes to prevent memory leaks

### CPU Optimization

- **Vectorized Operations**: Use numpy for coordinate processing
- **Compiled Regex**: Pre-compile regular expressions for text parsing
- **Index Structures**: Use appropriate data structures for fast lookups
- **Parallel Processing**: Use multiprocessing for CPU-intensive tasks

### I/O Optimization

- **Connection Pooling**: Reuse HTTP connections for external services
- **Async Operations**: Use async I/O for network requests
- **Batch Operations**: Batch multiple requests together
- **Compression**: Compress large data transfers

## Best Practices

1. **Error Handling**: Always handle errors gracefully with appropriate fallbacks
2. **Caching**: Cache expensive operations with appropriate TTL values
3. **Validation**: Validate inputs and outputs to ensure data integrity
4. **Logging**: Use structured logging with contextual information
5. **Configuration**: Make utilities configurable for different environments
6. **Testing**: Provide comprehensive test coverage with mock utilities
7. **Documentation**: Document utility functions with clear examples
8. **Performance**: Monitor and optimize for high-throughput scenarios
9. **Resource Management**: Properly manage resources and cleanup
10. **Backward Compatibility**: Maintain API compatibility when possible

## Integration Examples

### Complete Weather Processing

```python
from nwws.utils import (
    convert_text_product_to_model,
    WeatherGeoDataProvider,
    get_geohash_topics,
    build_topic
)

async def process_weather_message(raw_message: str) -> dict:
    # Convert to structured model
    weather_model = convert_text_product_to_model(raw_message)
    
    # Enrich with geographic data
    geo_provider = WeatherGeoDataProvider()
    if weather_model.coordinates:
        location = await geo_provider.reverse_geocode(
            weather_model.coordinates[0][0],
            weather_model.coordinates[0][1]
        )
        weather_model.location_info = location
    
    # Generate geohash topics
    geohash_topics = get_geohash_topics(
        weather_model.coordinates,
        precisions=[5, 6, 7]
    )
    
    # Build primary topic
    primary_topic = build_topic(
        "weather/{product_type}/{source}/{awipsid}",
        weather_model.dict()
    )
    
    return {
        "model": weather_model,
        "primary_topic": primary_topic,
        "geohash_topics": geohash_topics
    }
```

This utils package provides the foundational utilities that power the NWWS2MQTT system, ensuring reliable, efficient, and flexible operation across all components.