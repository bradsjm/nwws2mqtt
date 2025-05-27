# NWWS2MQTT

A gateway service that connects to the NWWS-OI (National Weather Service Weather Wire Service - Open Interface) XMPP feed and publishes weather product data to various output destinations including MQTT.

## Features

- **Pluggable Output System**: Support for multiple output destinations
- **MQTT Support**: Publish weather data to MQTT brokers
- **Console Output**: Default fallback to console output
- **Robust Connection Management**: Automatic reconnection with exponential backoff
- **Comprehensive Statistics**: Real-time monitoring of connection, message processing, and output handler performance
- **Comprehensive Logging**: Structured logging with configurable levels
- **Graceful Shutdown**: Clean disconnection and resource cleanup

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd nwws2mqtt
```

2. Install dependencies:
```bash
uv sync
```

3. Copy the example environment file and configure:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `NWWS_USERNAME` | NWWS-OI username | - | Yes |
| `NWWS_PASSWORD` | NWWS-OI password | - | Yes |
| `NWWS_SERVER` | NWWS-OI server | nwws-oi.weather.gov | No |
| `NWWS_PORT` | NWWS-OI port | 5222 | No |
| `LOG_LEVEL` | Logging level | INFO | No |
| `LOG_FILE` | Log file path | - | No |
| `OUTPUT_HANDLERS` | Comma-separated list of output handlers | console | No |
| `STATS_INTERVAL` | Statistics logging interval in seconds | 60 | No |
| `METRICS_ENABLED` | Enable Prometheus metrics endpoint | true | No |
| `METRICS_PORT` | Port for Prometheus metrics endpoint | 8080 | No |
| `METRICS_UPDATE_INTERVAL` | Metrics update interval in seconds | 30 | No |
| `DASHBOARD_ENABLED` | Enable web dashboard | false | No |
| `DASHBOARD_PORT` | Port for web dashboard | 8081 | No |

### Output Handlers

#### Console Output
The default output handler that prints JSON data to stdout.

Configuration:
```bash
OUTPUT_HANDLERS=console
```

#### MQTT Output
Publishes weather data to an MQTT broker.

Configuration:
```bash
OUTPUT_HANDLERS=mqtt
# or combine with console
OUTPUT_HANDLERS=console,mqtt

# MQTT Settings
MQTT_BROKER=your.mqtt.broker.com
MQTT_PORT=1883
MQTT_USERNAME=mqtt_user
MQTT_PASSWORD=mqtt_password
MQTT_TOPIC_PREFIX=nwws
MQTT_QOS=1
MQTT_RETAIN=false
MQTT_CLIENT_ID=nwws-oi-client
```

MQTT topics are structured as: `{MQTT_TOPIC_PREFIX}/{product_id}`

For example: `nwws/FXUS61KBOU`

## Statistics

The application includes comprehensive statistics collection and logging that provides insights into:

### Connection Statistics
- Application uptime and connection status
- Total connections and disconnections
- Reconnection attempts and authentication failures
- Ping/pong latency monitoring

### Message Processing Statistics
- Total messages received, processed, and failed
- Processing success and error rates
- Product type distribution (e.g., FXUS61, WWUS81)
- Source distribution (e.g., KBOU, KDEN)
- AFOS code distribution
- Processing error categorization

### Output Handler Statistics
- Per-handler publishing success rates
- Connection status and error counts
- Publishing performance metrics

### Statistics Configuration

Statistics are logged at regular intervals (default: 60 seconds) and can be configured with:

```bash
STATS_INTERVAL=60  # Log statistics every 60 seconds
```

### Sample Statistics Output

```
2025-05-26 10:30:00 | INFO | === NWWS2MQTT Statistics === app_uptime=2.5h connection_status=CONNECTED connection_uptime=2.5h total_connections=1 reconnect_attempts=0 outstanding_pings=0

2025-05-26 10:30:00 | INFO | Message Processing Stats total_received=1250 total_processed=1247 total_failed=3 success_rate=99.8% error_rate=0.2% messages_per_minute=8.3 processing_per_minute=8.3

2025-05-26 10:30:00 | INFO | Output Handler: mqtt type=mqtt status=CONNECTED published=1247 failed=0 success_rate=100.0% connection_errors=0

2025-05-26 10:30:00 | INFO | Top Product Types products={'FXUS61': 45, 'WWUS81': 32, 'FXUS62': 28}

2025-05-26 10:30:00 | INFO | Top Sources sources={'KBOU': 23, 'KDEN': 18, 'KGJT': 15}
```

## Usage

1. Configure your environment variables in `.env`
2. Run the application:
```bash
python app.py
```

The application will:
1. Connect to the NWWS-OI XMPP server
2. Join the weather data conference room
3. Process incoming weather products
4. Publish structured data to configured output handlers

## Data Format

Weather products are published as JSON-serialized data containing:
- Product metadata (ID, timestamp, etc.)
- Parsed weather data
- Geographic information
- Text content

### Prometheus Metrics

The application exposes metrics in Prometheus format via a standard `/metrics` endpoint. This enables integration with monitoring systems like Prometheus, Grafana, and other observability tools.

#### Available Metrics

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|---------|
| `nwws2mqtt_application_info` | Info | Application version and start time | - |
| `nwws2mqtt_application_uptime_seconds` | Gauge | Application uptime in seconds | - |
| `nwws2mqtt_connection_status` | Gauge | XMPP connection status (1=connected, 0=disconnected) | - |
| `nwws2mqtt_connection_uptime_seconds` | Gauge | Current connection uptime in seconds | - |
| `nwws2mqtt_connection_total_connections` | Counter | Total number of connections made | - |
| `nwws2mqtt_connection_reconnect_attempts_total` | Counter | Total number of reconnection attempts | - |
| `nwws2mqtt_messages_received_total` | Counter | Total number of messages received | - |
| `nwws2mqtt_messages_processed_total` | Counter | Total number of messages successfully processed | - |
| `nwws2mqtt_messages_failed_total` | Counter | Total number of messages that failed processing | `error_type` |
| `nwws2mqtt_messages_published_total` | Counter | Total number of messages published to output handlers | - |
| `nwws2mqtt_message_processing_success_rate` | Gauge | Message processing success rate as percentage | - |
| `nwws2mqtt_wmo_codes_total` | Counter | Total count by product type | `wmo_code` |
| `nwws2mqtt_sources_total` | Counter | Total count by source | `source` |
| `nwws2mqtt_afos_codes_total` | Counter | Total count by AFOS code | `afos_code` |
| `nwws2mqtt_output_handler_status` | Gauge | Output handler connection status | `handler_name`, `handler_type` |
| `nwws2mqtt_output_handler_published_total` | Counter | Total messages published by output handler | `handler_name`, `handler_type` |
| `nwws2mqtt_output_handler_success_rate` | Gauge | Output handler success rate as percentage | `handler_name`, `handler_type` |

## 🔧 Configuration

### Statistics Configuration

```bash
STATS_INTERVAL=60  # Log statistics every 60 seconds (default)
```

### Prometheus Metrics Configuration

```bash
METRICS_ENABLED=true          # Enable Prometheus metrics endpoint (default: true)
METRICS_PORT=8080            # Port for metrics endpoint (default: 8080)
METRICS_UPDATE_INTERVAL=30   # How often to update metrics in seconds (default: 30)
```

### Accessing Metrics

Once the application is running, metrics are available at:
```
http://localhost:8080/metrics
```

You can test the endpoint with curl:
```bash
curl http://localhost:8080/metrics
```

### Web Dashboard

The application includes an optional real-time web dashboard for monitoring application health and statistics.

#### Configuration

```bash
DASHBOARD_ENABLED=true       # Enable web dashboard (default: false)
DASHBOARD_PORT=8081         # Port for web dashboard (default: 8081)
```

#### Accessing the Dashboard

Once enabled, the dashboard is available at:
```
http://localhost:8081
```

The dashboard provides:
- **Real-time Statistics**: Live connection status, message processing metrics, and error rates
- **Connection Monitoring**: XMPP connection health, uptime, and reconnection statistics  
- **Message Processing**: Processing throughput, success/error rates, and recent message activity
- **Output Handler Status**: Status and performance of all configured output handlers
- **Product Distribution**: Top product types, sources, and AFOS codes
- **Error Tracking**: Recent processing errors and failure analysis

The dashboard automatically refreshes every 5 seconds to provide up-to-date information.

### Integration with Monitoring Systems

#### Prometheus Configuration

Add this job to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'nwws2mqtt'
    static_configs:
      - targets: ['localhost:8080']
    scrape_interval: 30s
    metrics_path: /metrics
```

#### Grafana Dashboard

The metrics can be visualized in Grafana. Key queries for monitoring:

- **Connection Status**: `nwws2mqtt_connection_status`
- **Message Processing Rate**: `rate(nwws2mqtt_messages_processed_total[5m])`
- **Error Rate**: `rate(nwws2mqtt_messages_failed_total[5m])`
- **Success Rate**: `nwws2mqtt_message_processing_success_rate`
- **Top Product Types**: `topk(10, nwws2mqtt_wmo_total)`


## License

MIT License - see LICENSE file for details.