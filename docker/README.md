# Docker Usage Guide for NWWS2MQTT

This guide covers how to build, deploy, and manage the NWWS2MQTT application using Docker.

## Table of Contents

- [Quick Start](#quick-start)
- [Building the Image](#building-the-image)
- [Running with Docker](#running-with-docker)
- [Docker Compose](#docker-compose)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Development](#development)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

## Quick Start

The fastest way to get started is using Docker Compose:

```bash
# Clone the repository
git clone <repository-url>
cd nwws2mqtt

# Copy environment template
cp .env.example .env

# Edit .env with your NWWS credentials
vim .env

# Start the application from the docker directory
cd docker
docker compose up -d
```

## Building the Image

### Standard Build

```bash
# Build with default Python version (3.13) from project root
docker build -f docker/Dockerfile -t nwws2mqtt .

# Build with specific Python version
docker build -f docker/Dockerfile --build-arg PYTHON_VERSION=3.13 -t nwws2mqtt:py3.13 .

# Or build from docker directory
cd docker
docker build -f Dockerfile -t nwws2mqtt ..
```

### Multi-platform Build

```bash
# Build for multiple architectures from project root
docker buildx build -f docker/Dockerfile --platform linux/amd64,linux/arm64 -t nwws2mqtt:latest .
```

### Build Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `PYTHON_VERSION` | `3.13` | Python version to use |

### Build Notes

**Scientific Computing Dependencies**: This application uses `pyiem` for weather data processing, which requires several heavy scientific computing libraries including:
- GDAL (Geospatial Data Abstraction Library)
- HDF5 and NetCDF for scientific data formats
- GEOS for geometric operations
- PROJ for cartographic projections
- ECCODES for meteorological data

The Dockerfile uses **Debian Bookworm** instead of Alpine Linux to ensure compatibility with these scientific packages. This results in a larger image (~1.4GB) but provides better reliability for the geospatial dependencies.

**Build Time**: Initial builds may take 10-15 minutes due to compilation of scientific libraries. Subsequent builds use Docker layer caching for faster rebuilds.

## Running with Docker

### Basic Run

```bash
docker run -d \
  --name nwws2mqtt \
  -p 8080:8080 \
  -e NWWS_USERNAME=your_username \
  -e NWWS_PASSWORD=your_password \
  nwws2mqtt
```

### With Environment File

```bash
docker run -d \
  --name nwws2mqtt \
  -p 8080:8080 \
  --env-file .env \
  nwws2mqtt
```

### With Persistent Logs

```bash
docker run -d \
  --name nwws2mqtt \
  -p 8080:8080 \
  -v $(pwd)/../logs:/app/logs \
  --env-file ../.env \
  nwws2mqtt
```

**Note**: The application requires valid NWWS-OI credentials to function. Without proper `NWWS_USERNAME` and `NWWS_PASSWORD`, the container will exit with a configuration error.

## Docker Compose

### Available Profiles

The `docker-compose.yml` includes several profiles for different deployment scenarios:

| Profile | Description | Services |
|---------|-------------|----------|
| `default` | Basic application with MQTT | nwws2mqtt, mosquitto |
| `mqtt` | MQTT broker only | mosquitto |
| `database` | PostgreSQL database | postgres |
| `cache` | Redis cache | redis |
| `monitoring` | Prometheus + Grafana | prometheus, grafana |
| `full` | All services | All of the above |

### Profile Usage

```bash
# Default profile (app + MQTT)
docker compose up -d

# With database
docker compose --profile database up -d

# With monitoring
docker compose --profile monitoring up -d

# Full stack
docker compose --profile full up -d

# Multiple profiles
docker compose --profile database --profile monitoring up -d
```

**Important**: Make sure to create and configure your `.env` file before starting services:
```bash
cp ../.env.example ../.env
# Edit ../.env with your NWWS credentials
```

### Common Commands

```bash
# Navigate to docker directory
cd docker

# Start services
docker compose up -d

# View logs
docker compose logs -f nwws2mqtt

# Stop services
docker compose down

# Rebuild and restart
docker compose up -d --build

# Scale services
docker compose up -d --scale nwws2mqtt=3
```

## Configuration

### Environment Variables

#### NWWS-OI Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NWWS_USERNAME` | Yes | - | NWWS-OI username |
| `NWWS_PASSWORD` | Yes | - | NWWS-OI password |
| `NWWS_SERVER` | No | `nwws-oi.weather.gov` | NWWS-OI server |
| `NWWS_PORT` | No | `5222` | NWWS-OI port |

#### Logging Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | No | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | No | - | Log file path (optional) |

#### Metrics Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `METRIC_ENABLED` | No | `true` | Enable metrics endpoint |
| `METRIC_HOST` | No | `127.0.0.1` | Metrics host (use `0.0.0.0` in containers) |
| `METRIC_PORT` | No | `8080` | Metrics port |

#### MQTT Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MQTT_BROKER` | No | - | MQTT broker hostname |
| `MQTT_PORT` | No | `1883` | MQTT broker port |
| `MQTT_USERNAME` | No | - | MQTT username |
| `MQTT_PASSWORD` | No | - | MQTT password |
| `MQTT_TOPIC_PREFIX` | No | `nwws` | MQTT topic prefix |
| `MQTT_QOS` | No | `1` | MQTT Quality of Service |
| `MQTT_RETAIN` | No | `true` | MQTT retain messages |
| `MQTT_CLIENT_ID` | No | `nwws-oi-client` | MQTT client ID |

### Example .env File

```bash
# NWWS-OI Configuration
NWWS_USERNAME=your_username_here
NWWS_PASSWORD=your_password_here
NWWS_SERVER=nwws-oi.weather.gov
NWWS_PORT=5222

# Logging
LOG_LEVEL=INFO

# Metrics
METRIC_ENABLED=true
METRIC_HOST=0.0.0.0
METRIC_PORT=8080

# MQTT
MQTT_BROKER=mosquitto
MQTT_PORT=1883
MQTT_TOPIC_PREFIX=nwws
MQTT_QOS=1
MQTT_RETAIN=true

# Optional: Database
POSTGRES_DB=nwws
POSTGRES_USER=nwws
POSTGRES_PASSWORD=nwws123

# Optional: Monitoring
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin
```

## Monitoring

### Health Checks

The application includes built-in health checks:

```bash
# Check application health
curl http://localhost:8080/health

# Check metrics endpoint
curl http://localhost:8080/metrics
```

### Prometheus Metrics

Access Prometheus at http://localhost:9090 when using the monitoring profile.

Key metrics to monitor:
- `nwws_messages_total` - Total messages processed
- `nwws_errors_total` - Total errors encountered
- `nwws_processing_duration_seconds` - Message processing time
- `nwws_pipeline_stage_duration_seconds` - Pipeline stage timing

### Grafana Dashboard

Access Grafana at http://localhost:3000 (admin/admin) when using the monitoring profile.

Import the included dashboard JSON files for pre-configured visualizations.

## Development

### Development Setup

```bash
# Build development image from project root
docker build -f docker/Dockerfile -t nwws2mqtt:dev .

# Or from docker directory
cd docker
docker build -f Dockerfile -t nwws2mqtt:dev ..

# Run with development overrides
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Mount source code for development (from project root)
docker run -it --rm \
  -v $(pwd)/src:/app/src \
  -p 8080:8080 \
  --env-file .env \
  nwws2mqtt:dev
```

### Using Convenience Scripts

From the project root, you can use the provided convenience scripts:

```bash
# Using the bash script
./docker.sh init          # Initialize .env file
./docker.sh build         # Build the image
./docker.sh up monitoring # Start with monitoring
./docker.sh logs          # Show logs
./docker.sh health        # Check health

# Using Make
make init                 # Initialize environment
make build TAG=dev        # Build with dev tag
make up PROFILE=full      # Start all services
make logs SERVICE=mqtt    # Show MQTT logs
make clean                # Clean up everything
```

### Debugging

```bash
# Run with debug logging
docker run -it --rm \
  -e LOG_LEVEL=DEBUG \
  -p 8080:8080 \
  --env-file .env \
  nwws2mqtt

# Access container shell
docker exec -it nwws2mqtt /bin/sh

# View real-time logs
docker logs -f nwws2mqtt
```

## Production Deployment

### Resource Limits

```yaml
# docker-compose.prod.yml
services:
  nwws2mqtt:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
      restart_policy:
        condition: unless-stopped
        delay: 5s
        max_attempts: 3
```

### Security Considerations

1. **Use secrets for sensitive data:**
```bash
# Create Docker secrets
echo "your_username" | docker secret create nwws_username -
echo "your_password" | docker secret create nwws_password -
```

2. **Run as non-root user (already configured in Dockerfile)**

3. **Use specific image tags:**
```bash
docker tag nwws2mqtt:latest nwws2mqtt:v1.0.0
```

4. **Network security:**
```yaml
networks:
  nwws-internal:
    driver: bridge
    internal: true
```

### Performance Tuning

```yaml
# docker-compose.yml
services:
  nwws2mqtt:
    environment:
      # Optimize for production
      - PYTHONOPTIMIZE=2
      - PYTHONDONTWRITEBYTECODE=1
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
```

## Troubleshooting

### Common Issues

#### Container Won't Start

```bash
# Check logs
docker logs nwws2mqtt

# Check configuration
docker run --rm --env-file .env nwws2mqtt python -c "from nwws.models import Config; print(Config.from_env())"
```

#### Scientific Dependencies Issues

If you encounter issues with geospatial or scientific computing libraries:

```bash
# Verify pyiem import works
docker run --rm nwws2mqtt python -c "import pyiem; print('pyiem imported successfully')"

# Check GDAL installation
docker run --rm nwws2mqtt python -c "from osgeo import gdal; print(f'GDAL version: {gdal.VersionInfo()}')"

# Test HDF5/NetCDF
docker run --rm nwws2mqtt python -c "import netCDF4; print('NetCDF4 working')"
```

#### Connection Issues

```bash
# Test NWWS connectivity
docker run --rm --env-file .env nwws2mqtt python -c "
import socket
s = socket.socket()
s.settimeout(10)
s.connect(('nwws-oi.weather.gov', 5222))
print('Connection successful')
"

# Test MQTT connectivity
docker run --rm --env-file .env nwws2mqtt python -c "
import paho.mqtt.client as mqtt
client = mqtt.Client()
client.connect('mosquitto', 1883, 60)
print('MQTT connection successful')
"
```

#### Memory Issues

```bash
# Monitor resource usage
docker stats nwws2mqtt

# Increase memory limits
docker run -m 2g nwws2mqtt
```

#### Permission Issues

```bash
# Check user permissions
docker exec nwws2mqtt id

# Fix log directory permissions
sudo chown -R 1001:1001 ./logs
```

### Debugging Commands

```bash
# Enter container for debugging
docker exec -it nwws2mqtt /bin/sh

# Check Python environment
docker exec nwws2mqtt python --version
docker exec nwws2mqtt pip list

# Test application components
docker exec nwws2mqtt python -m pytest src/tests/ -v

# Check network connectivity
docker exec nwws2mqtt netstat -tulpn
docker exec nwws2mqtt nslookup nwws-oi.weather.gov
```

### Log Analysis

```bash
# View recent logs
docker logs --tail 100 nwws2mqtt

# Filter logs by level
docker logs nwws2mqtt 2>&1 | grep ERROR

# Follow logs with timestamps
docker logs -f -t nwws2mqtt

# Export logs
docker logs nwws2mqtt > nwws2mqtt.log 2>&1
```

## Backup and Recovery

### Data Backup

```bash
# Backup volumes (from docker directory)
docker run --rm -v docker_mosquitto-data:/data -v $(pwd):/backup alpine tar czf /backup/mosquitto-backup.tar.gz -C /data .

# Backup database
docker exec postgres pg_dump -U nwws nwws > nwws-backup.sql
```

### Recovery

```bash
# Restore volumes (from docker directory)
docker run --rm -v docker_mosquitto-data:/data -v $(pwd):/backup alpine tar xzf /backup/mosquitto-backup.tar.gz -C /data

# Restore database
docker exec -i postgres psql -U nwws nwws < nwws-backup.sql
```

## Additional Resources

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [UV Package Manager](https://docs.astral.sh/uv/)
- [Prometheus Monitoring](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)