# NWWS2MQTT

A comprehensive, production-ready gateway service that connects to the NWWS-OI (National Weather Service Weather Wire Service - Open Interface) XMPP feed and processes weather product data through a flexible pipeline architecture. The system transforms, enriches, and publishes weather data to multiple output destinations including MQTT brokers, databases, and custom endpoints.

## Features

### Core Architecture
- **Pipeline Framework**: Flexible, configurable processing pipeline with filters, transformers, and outputs
- **Event-Driven Processing**: Immutable event processing with comprehensive metadata tracking
- **Component Registry**: Pluggable components with automatic discovery and registration
- **Configuration Management**: YAML/JSON configuration with environment variable overrides

### Data Processing
- **Weather Data Parsing**: Advanced NOAA text product parsing with pyiem integration
- **Geographic Enrichment**: Automatic geocoding, county/zone lookup, and coordinate extraction
- **XML Processing**: Schema-aware XML parsing for CAP alerts and structured data
- **Data Validation**: Comprehensive input validation and error handling
- **Format Conversion**: Convert between different weather data formats and schemas

### Output System
- **Multiple Output Handlers**: MQTT, database, console, webhook, and custom outputs
- **Batch Processing**: Efficient batch operations for high-throughput scenarios
- **Connection Management**: Automatic reconnection with exponential backoff for all outputs
- **Error Recovery**: Sophisticated error handling with retry logic and dead letter queues

### Monitoring & Observability
- **Real-time Dashboard**: Web-based monitoring interface with live statistics
- **Prometheus Metrics**: Complete metrics collection for monitoring systems
- **Statistics Collection**: Detailed performance and processing statistics
- **Health Checks**: Comprehensive health monitoring for all components
- **Structured Logging**: JSON-structured logging with contextual information

### Advanced Features
- **Duplicate Detection**: Time-window based duplicate filtering
- **Message Filtering**: Configurable message filtering (test messages, content-based)
- **Geographic Indexing**: Geohash-based geographic topic generation
- **Performance Optimization**: Caching, connection pooling, and async processing
- **Web API**: RESTful API for system control and monitoring
- **WebSocket Streaming**: Real-time data streaming for dashboards

## Package Architecture

The NWWS2MQTT system is organized into focused packages, each handling specific aspects of weather data processing:

### 📦 [**Filters**](src/nwws/filters/README.md)
Pipeline event filtering for early rejection of unwanted data:
- **DuplicateFilter**: Time-window based duplicate detection and removal
- **TestMessageFilter**: Filtering of test messages (AWIPSID='TSTMSG')
- **Custom Filter Framework**: Easy development of domain-specific filters

### 📦 [**Transformers**](src/nwws/transformers/README.md)
Data transformation and enrichment components:
- **NoaaPortTransformer**: NOAA text product parsing with geographic enrichment
- **XmlTransformer**: Schema-aware XML processing for CAP alerts and structured data
- **Geographic Processing**: Coordinate extraction, geocoding, and UGC resolution
- **Metadata Extraction**: Automated metadata extraction and normalization

### 📦 [**Outputs**](src/nwws/outputs/README.md)
Pluggable output handlers for publishing processed data:
- **MQTTOutput**: Production-ready MQTT publishing with SSL/TLS support
- **DatabaseOutput**: Persistent storage with batch operations and connection pooling
- **ConsoleOutput**: Development and debugging output with JSON formatting
- **Custom Output Framework**: Easy integration with external services and APIs

### 📦 [**Pipeline**](src/nwws/pipeline/README.md)
Core processing framework with event-driven architecture:
- **Event Processing**: Immutable event handling with comprehensive metadata
- **Component Management**: Automatic registration and lifecycle management
- **Error Handling**: Sophisticated error recovery and retry strategies
- **Statistics Collection**: Real-time performance monitoring and reporting

### 📦 [**Receiver**](src/nwws/receiver/README.md)
XMPP client for NWWS-OI connectivity:
- **WeatherWire**: Robust XMPP client with automatic reconnection
- **Message Processing**: Real-time weather message ingestion and parsing
- **Connection Management**: Health monitoring and connection statistics
- **Performance Optimization**: Message queuing and batch processing

### 📦 [**Metrics**](src/nwws/metrics/README.md)
Comprehensive metrics collection and export:
- **Prometheus Integration**: Full Prometheus metrics export support
- **Custom Metrics**: Counters, gauges, and histograms for application monitoring
- **Performance Tracking**: Detailed timing and throughput measurements
- **Health Monitoring**: Component health and system resource tracking

### 📦 [**Models**](src/nwws/models/README.md)
Data structures and configuration management:
- **Configuration Models**: Validated settings with environment variable support
- **Weather Data Models**: Structured representations of weather products
- **Event Models**: Pipeline event definitions with type safety
- **Validation Framework**: Comprehensive input/output validation

### 📦 [**Utils**](src/nwws/utils/README.md)
Shared utilities and helper functions:
- **Geographic Services**: Geocoding, county/zone lookup, and coordinate processing
- **Data Converters**: Format conversion and data normalization utilities
- **Geohash Generation**: Geographic indexing and topic generation
- **Logging Configuration**: Centralized logging setup and structured output

### 📦 [**Webserver**](src/nwws/webserver/README.md)
Web interface and API services:
- **Real-time Dashboard**: Live monitoring with interactive charts and maps
- **REST API**: Complete system control and monitoring API
- **WebSocket Services**: Real-time data streaming for dashboards
- **Metrics Endpoint**: Prometheus-compatible metrics exposure

## Installation

### Option 1: Docker (Recommended)

**Docker is strongly recommended** due to the complex scientific computing dependencies (GDAL, HDF5, NetCDF, GEOS, PROJ, ECCODES) required by the `pyiem` weather data processing library. The Docker setup handles all these dependencies automatically.

1. Clone the repository:
```bash
git clone <repository-url>
cd nwws2mqtt
```

2. Initialize environment and start services:
```bash
./docker.sh init
./docker.sh up
```

See the [Docker documentation](docker/README.md) for detailed Docker usage.

### Option 2: Local Development

**Note**: Local development requires installing complex scientific computing dependencies. The system requires Python 3.12+ and several system libraries.

**macOS:**
```bash
brew install gdal hdf5 netcdf geos proj eccodes
```

**Ubuntu/Debian:**
```bash
apt-get install libgdal-dev libhdf5-dev libnetcdf-dev libgeos-dev libproj-dev libeccodes-dev
```

**Installation Steps:**
1. Clone the repository:
```bash
git clone <repository-url>
cd nwws2mqtt
```

2. Install Python dependencies:
```bash
uv sync
```

3. Copy the example environment file and configure:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

The system supports multiple configuration methods with a clear precedence hierarchy:

1. **Pipeline Configuration Files** (YAML/JSON) - Recommended for complex setups
2. **Environment Variables** - Great for containerized deployments
3. **Command Line Arguments** - Useful for development and testing
4. **Default Values** - Sensible defaults for quick setup

### Core Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `NWWS_USERNAME` | NWWS-OI username | - | Yes |
| `NWWS_PASSWORD` | NWWS-OI password | - | Yes |
| `NWWS_SERVER` | NWWS-OI server | nwws-oi.weather.gov | No |
| `NWWS_PORT` | NWWS-OI port | 5222 | No |
| `LOG_LEVEL` | Logging level | INFO | No |
| `LOG_FORMAT` | Log format (json/text) | json | No |
| `OUTPUT_HANDLERS` | Comma-separated list of output handlers | console | No |

### Pipeline Configuration

Create a `pipeline.yaml` file for complex configurations:

```yaml
pipeline:
  pipeline_id: "weather-processing"
  
  filters:
    - type: "DuplicateFilter"
      config:
        window_seconds: 300.0
    - type: "TestMessageFilter"
      config: {}
  
  transformers:
    - type: "NoaaPortTransformer"
      config:
        enable_geocoding: true
        include_counties: true
        include_zones: true
    - type: "XmlTransformer"
      config:
        validate_xml: true
  
  outputs:
    - type: "MQTTOutput"
      config:
        broker: "mqtt.example.com"
        port: 1883
        topic_prefix: "nwws"
        qos: 1
    - type: "DatabaseOutput"
      config:
        connection_string: "postgresql://user:pass@localhost/weather"
        batch_size: 100

receiver:
  username: "${NWWS_USERNAME}"
  password: "${NWWS_PASSWORD}"
  server: "nwws-oi.weather.gov"
  auto_reconnect: true

webserver:
  enable_dashboard: true
  enable_metrics: true
  port: 8081

metrics:
  enabled: true
  port: 8080
  update_interval: 30
```

### Output Handler Configuration

#### Console Output
```bash
# Simple console output
OUTPUT_HANDLERS=console

# Console with pretty printing
CONSOLE_PRETTY_PRINT=true
CONSOLE_COLOR_OUTPUT=true
```

#### MQTT Output
```bash
# Basic MQTT configuration
OUTPUT_HANDLERS=mqtt
MQTT_BROKER=your.mqtt.broker.com
MQTT_PORT=1883
MQTT_USERNAME=mqtt_user
MQTT_PASSWORD=mqtt_password
MQTT_TOPIC_PREFIX=nwws

# Advanced MQTT settings
MQTT_QOS=1
MQTT_RETAIN=false
MQTT_SSL_ENABLED=true
MQTT_CLIENT_ID=nwws2mqtt-instance-1
```

**MQTT Topic Structure:**
```
{topic_prefix}/{product_type}/{source}/{awipsid}
# Examples:
nwws/forecast/KBOU/FXUS61
nwws/warning/KDEN/WWUS81
nwws/geo/9xj648/warning  # Geographic topics
```

#### Database Output
```bash
OUTPUT_HANDLERS=database
DATABASE_URL=postgresql://user:pass@localhost:5432/weather
DATABASE_BATCH_SIZE=100
DATABASE_CREATE_TABLES=true
```

## Data Processing Pipeline

The system processes weather data through a sophisticated pipeline architecture:

### 1. Message Reception (Receiver Package)
- **XMPP Connection**: Robust connection to NWWS-OI with automatic reconnection
- **Message Parsing**: Real-time parsing of incoming weather messages
- **Health Monitoring**: Connection status and performance tracking

### 2. Event Filtering (Filters Package)
- **Duplicate Detection**: Time-window based duplicate message filtering
- **Test Message Filtering**: Automatic removal of test messages
- **Custom Filters**: Configurable filtering based on content, source, or metadata

### 3. Data Transformation (Transformers Package)
- **NOAA Text Parsing**: Advanced parsing of weather text products
- **Geographic Enrichment**: Automatic geocoding and geographic data enhancement
- **XML Processing**: Structured processing of CAP alerts and XML data
- **Metadata Extraction**: Comprehensive metadata extraction and normalization

### 4. Output Publishing (Outputs Package)
- **MQTT Publishing**: Real-time publishing to MQTT brokers with topic structure
- **Database Storage**: Persistent storage with batch operations
- **Multiple Destinations**: Simultaneous publishing to multiple output handlers

### Example Data Flow

```
Raw NWWS Message → Parse & Validate → Filter (Duplicates/Tests) → 
Transform (Parse/Enrich) → Publish (MQTT/DB/Console)
```

**Input:**
```
FXUS61 KBOU 151200
ZFPBOU
Zone Forecast Product for Colorado
National Weather Service Boulder CO
1200 PM MST Fri Dec 15 2023
...
```

**Output:**
```json
{
  "id": "FXUS61KBOU20231215120000",
  "awipsid": "FXUS61",
  "source": "KBOU",
  "product_type": "forecast",
  "timestamp": "2023-12-15T12:00:00Z",
  "geographic_data": {
    "coordinates": [[40.0150, -105.2705]],
    "counties": ["CO-013", "CO-059"],
    "zones": ["COZ040", "COZ039"],
    "geohash": ["9xj648", "9xj61b"]
  },
  "metadata": {
    "urgency": "routine",
    "certainty": "likely",
    "scope": "public"
  },
  "text_content": "Zone Forecast Product..."
}
```

## Monitoring & Statistics

### Real-time Dashboard
Access the web dashboard at `http://localhost:8081` (when enabled) for:
- **Live Statistics**: Real-time processing metrics and performance charts
- **Connection Status**: XMPP connection health and uptime monitoring  
- **Geographic Visualization**: Map-based visualization of weather data sources
- **Error Tracking**: Live error logs and failure analysis
- **System Health**: Resource usage and component status

### Statistics Collection

The system provides comprehensive statistics across all components:

**Connection Statistics:**
- Application uptime and connection status
- Reconnection attempts and authentication metrics
- Network latency and ping/pong monitoring

**Processing Statistics:**
- Message throughput and processing rates
- Success/error rates and failure categorization
- Product type and source distribution
- Geographic data processing metrics

**Performance Statistics:**
- CPU and memory usage tracking
- Processing latency and queue depths
- Cache hit rates and optimization metrics

**Configuration:**
```bash
STATS_INTERVAL=60           # Statistics logging interval
DASHBOARD_ENABLED=true      # Enable web dashboard
DASHBOARD_PORT=8081        # Dashboard port
```

## Usage

### Quick Start

1. **Configure Environment:**
```bash
cp .env.example .env
# Edit .env with your NWWS-OI credentials
```

2. **Run with Docker (Recommended):**
```bash
./docker.sh init
./docker.sh up
```

3. **Or run locally:**
```bash
uv run python -m nwws
```

### Advanced Usage

**With Pipeline Configuration:**
```bash
# Create pipeline.yaml configuration file
uv run python -m nwws --config pipeline.yaml
```

**With Specific Components:**
```bash
# Enable dashboard and metrics
DASHBOARD_ENABLED=true METRICS_ENABLED=true uv run python -m nwws

# Custom output handlers
OUTPUT_HANDLERS=mqtt,database,console uv run python -m nwws
```

**Development Mode:**
```bash
# Run with debug logging and auto-reload
LOG_LEVEL=DEBUG uv run python -m nwws --reload
```

### System Operation

The application performs the following workflow:

1. **Initialize Components**: Load configuration and initialize all pipeline components
2. **Connect to NWWS-OI**: Establish XMPP connection to weather data feed
3. **Start Processing Pipeline**: Begin processing incoming weather messages
4. **Real-time Processing**: 
   - Filter duplicate and test messages
   - Parse and enrich weather data
   - Publish to configured output destinations
5. **Monitoring**: Collect statistics and provide web dashboard access
6. **Graceful Shutdown**: Clean disconnection and resource cleanup on termination

### Accessing Services

- **Dashboard**: http://localhost:8081 (if enabled)
- **Metrics**: http://localhost:8080/metrics (Prometheus format)
- **API**: http://localhost:8081/api/v1/ (REST API)
- **Health Check**: http://localhost:8081/health

## Data Processing Examples

### Input: Raw NWWS-OI Message
```xml
<message from='nwws@conference.nwws-oi.weather.gov/KBOU' 
         to='username@nwws-oi.weather.gov' 
         type='groupchat'>
  <body>
FXUS61 KBOU 151200
ZFPBOU
Zone Forecast Product for Colorado
National Weather Service Boulder CO
1200 PM MST Fri Dec 15 2023

COZ040-160600-
Boulder and Jefferson Counties Below 6000 Feet-
1200 PM MST Fri Dec 15 2023

.TODAY...Partly cloudy. High around 45.
.TONIGHT...Mostly clear. Low around 25.
  </body>
  <x xmlns='nwws:msg'>
    <timestamp>2023-12-15T19:00:00Z</timestamp>
    <awipsID>FXUS61</awipsID>
    <source>KBOU</source>
  </x>
</message>
```

### Output: Processed Weather Data
```json
{
  "id": "FXUS61KBOU20231215120000",
  "awipsid": "FXUS61",
  "source": "KBOU",
  "wmo_id": "FXUS61KBOU",
  "timestamp": "2023-12-15T19:00:00Z",
  "product_type": "forecast",
  "text_content": "Zone Forecast Product for Colorado...",
  
  "parsed_data": {
    "product_name": "Zone Forecast Product for Colorado",
    "issuing_office": "National Weather Service Boulder CO",
    "issuance_time": "2023-12-15T19:00:00Z",
    "urgency": "routine",
    "certainty": "likely",
    "scope": "public"
  },
  
  "geographic_data": {
    "ugc_codes": ["COZ040"],
    "counties": [
      {
        "code": "CO-013",
        "name": "Boulder County",
        "state": "Colorado"
      },
      {
        "code": "CO-059", 
        "name": "Jefferson County",
        "state": "Colorado"
      }
    ],
    "zones": [
      {
        "code": "COZ040",
        "name": "Boulder and Jefferson Counties Below 6000 Feet",
        "type": "forecast"
      }
    ],
    "coordinates": [
      {"lat": 40.0150, "lon": -105.2705},
      {"lat": 39.7392, "lon": -104.9903}
    ],
    "geohash": ["9xj648", "9xj61b"],
    "bounding_box": {
      "north": 40.0150,
      "south": 39.7392,
      "east": -104.9903,
      "west": -105.2705
    }
  },
  
  "processing_metadata": {
    "received_timestamp": "2023-12-15T19:00:01.234Z",
    "processed_timestamp": "2023-12-15T19:00:01.456Z",
    "processing_duration_ms": 222,
    "pipeline_id": "main-pipeline",
    "transformer_versions": {
      "noaa_parser": "1.23.0",
      "geo_enricher": "2.1.0"
    }
  }
}
```

### MQTT Topic Examples
```
# Primary product topic
nwws/forecast/KBOU/FXUS61

# Geographic topics (multiple precision levels)
nwws/geo/9xj6/forecast      # Lower precision (larger area)
nwws/geo/9xj648/forecast    # Higher precision (smaller area)

# County-based topics
nwws/county/CO-013/forecast
nwws/county/CO-059/forecast

# Zone-based topics  
nwws/zone/COZ040/forecast
```

## Monitoring & Observability

### Prometheus Metrics

The application exposes comprehensive metrics in Prometheus format at `/metrics`:

```bash
# Enable metrics (default: true)
METRICS_ENABLED=true
METRICS_PORT=8080
METRICS_UPDATE_INTERVAL=30
```

**Key Metrics Categories:**
- **Application Metrics**: Uptime, version, and health status
- **Connection Metrics**: XMPP connection status and performance
- **Processing Metrics**: Message throughput, success rates, and error counts  
- **Output Metrics**: Publishing success rates per output handler
- **Performance Metrics**: Processing latency, queue depths, and resource usage
- **Geographic Metrics**: Distribution by weather office and geographic region

**Example Metrics:**
```prometheus
# Message processing
nwws2mqtt_messages_processed_total{source="KBOU"} 1250
nwws2mqtt_processing_duration_seconds_bucket{le="0.1"} 1200

# Connection health
nwws2mqtt_connection_status 1
nwws2mqtt_connection_uptime_seconds 3600

# Output handler performance
nwws2mqtt_output_published_total{handler="mqtt",type="MQTTOutput"} 1247
nwws2mqtt_output_success_rate{handler="mqtt",type="MQTTOutput"} 0.998
```

### Web Dashboard

Access the real-time monitoring dashboard:

```bash
# Enable dashboard
DASHBOARD_ENABLED=true
DASHBOARD_PORT=8081
DASHBOARD_THEME=dark

# Access at http://localhost:8081
```

**Dashboard Features:**
- **Live Statistics**: Real-time charts and metrics updates
- **Geographic Visualization**: Interactive maps showing weather data distribution
- **Connection Monitoring**: XMPP health and reconnection tracking
- **Performance Analytics**: Throughput, latency, and error analysis
- **Configuration View**: Current system configuration display
- **Log Streaming**: Live log viewing with filtering capabilities

### Health Checks

Comprehensive health monitoring endpoints:

```bash
# Basic health check
curl http://localhost:8081/health

# Detailed component health
curl http://localhost:8081/health/detailed

# API status
curl http://localhost:8081/api/v1/status
```

### Integration with Monitoring Systems

**Prometheus Configuration:**
```yaml
scrape_configs:
  - job_name: 'nwws2mqtt'
    static_configs:
      - targets: ['localhost:8080']
    scrape_interval: 30s
    metrics_path: /metrics
```

**Grafana Queries:**
```promql
# Processing rate
rate(nwws2mqtt_messages_processed_total[5m])

# Error rate  
rate(nwws2mqtt_messages_failed_total[5m]) / rate(nwws2mqtt_messages_received_total[5m])

# 99th percentile latency
histogram_quantile(0.99, rate(nwws2mqtt_processing_duration_seconds_bucket[5m]))
```

**Alerting Rules:**
```yaml
groups:
  - name: nwws2mqtt
    rules:
      - alert: HighErrorRate
        expr: rate(nwws2mqtt_messages_failed_total[5m]) / rate(nwws2mqtt_messages_received_total[5m]) > 0.05
        for: 2m
      
      - alert: ConnectionDown  
        expr: nwws2mqtt_connection_status == 0
        for: 1m
```


## Development

### Package Development

Each package includes comprehensive documentation and development guidelines:

- **[Filters Development](src/nwws/filters/README.md)**: Creating custom message filters
- **[Transformers Development](src/nwws/transformers/README.md)**: Building data transformation components  
- **[Outputs Development](src/nwws/outputs/README.md)**: Implementing custom output handlers
- **[Pipeline Development](src/nwws/pipeline/README.md)**: Pipeline framework and event processing
- **[Utils Development](src/nwws/utils/README.md)**: Shared utilities and helper functions

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest -m unit        # Unit tests only
uv run pytest -m integration # Integration tests only
uv run pytest -m slow        # Performance tests

# Run with coverage
uv run pytest --cov=src/nwws --cov-report=html
```

### Code Quality

```bash
# Format code
uv run ruff format

# Lint code  
uv run ruff check --fix

# Type checking
uv run basedpyright
```

### Contributing

1. **Fork the repository** and create a feature branch
2. **Follow the coding standards** defined in `.github/copilot-instructions.md`
3. **Add comprehensive tests** for new functionality
4. **Update documentation** including package README files
5. **Ensure all checks pass** (tests, linting, type checking)
6. **Submit a pull request** with detailed description

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   NWWS-OI       │    │   Receiver       │    │   Pipeline      │
│   XMPP Feed     │───▶│   Package        │───▶│   Framework     │
│                 │    │   (WeatherWire)  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Monitoring    │    │   Webserver      │    │   Processing    │
│   & Metrics     │◀───│   Package        │    │   Stages        │
│                 │    │   (Dashboard)    │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MQTT Broker   │    │   Output         │    │   Filters       │
│   Database      │◀───│   Handlers       │◀───│   Transformers  │
│   Custom APIs   │    │   Package        │    │   Components    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## License

MIT License - see LICENSE file for details.