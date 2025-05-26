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
python nwws_oi_ingest.py
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

## Extending Output Handlers

To add a new output handler:

1. Create a class that inherits from `OutputHandler` in `output_handlers.py`
2. Implement the required methods:
   - `publish(product_id, structured_data, subject)`
   - `start()`
   - `stop()`
   - `is_connected` property
3. Add the handler to the `OutputManager._initialize_handlers()` method
4. Update the environment configuration documentation

## 📊 Statistics Collected

### Connection Statistics
- Application uptime and connection status
- Total connections and disconnections
- Reconnection attempts and authentication failures
- Ping/pong latency monitoring
- Outstanding ping tracking

### Message Processing Statistics
- Total messages received, processed, and failed
- Processing success and error rates (calculated properties)
- Product type distribution (e.g., FXUS61, WWUS81)
- Source distribution (e.g., KBOU, KDEN, KGJT)
- AFOS code distribution
- Processing error categorization with counts

### Output Handler Statistics
- Per-handler publishing success rates
- Connection status and error counts
- Publishing performance metrics
- Handler-specific uptime tracking

## 🔧 Configuration

Statistics logging interval is configurable via environment variable:

```bash
STATS_INTERVAL=60  # Log statistics every 60 seconds (default)
```

## License

MIT License - see LICENSE file for details.