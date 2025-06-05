# NWWS Webserver Package

The webserver package provides HTTP/WebSocket services for the NWWS2MQTT system, including a real-time dashboard, metrics endpoints, API services, and administrative interfaces. It enables monitoring, control, and visualization of the weather data processing pipeline.

## Overview

The webserver package implements a FastAPI-based web application that provides:
- **Real-time Dashboard**: Live monitoring of system health and statistics
- **Metrics Endpoint**: Prometheus-compatible metrics for monitoring systems
- **REST API**: Programmatic access to system data and controls
- **WebSocket Services**: Real-time data streaming for dashboards
- **Administrative Interface**: System configuration and control capabilities
- **Health Checks**: Service health monitoring and diagnostics

## Architecture

The package consists of several key components:

```
webserver/
├── __init__.py          # Package exports
├── server.py            # Main web server implementation
├── api/                 # REST API endpoints
│   ├── __init__.py
│   ├── health.py        # Health check endpoints
│   ├── metrics.py       # Metrics API endpoints
│   ├── pipeline.py      # Pipeline control endpoints
│   └── receiver.py      # Receiver status endpoints
└── dashboard/           # Web dashboard
    ├── __init__.py
    ├── README.md        # Dashboard-specific documentation
    ├── static/          # Static assets (CSS, JS, images)
    ├── templates/       # HTML templates
    └── websocket.py     # WebSocket handlers
```

## Core Components

### WebServer

The main web server that coordinates all HTTP services:

```python
from nwws.webserver import WebServer

# Create web server with configuration
server = WebServer(
    host="0.0.0.0",
    port=8081,
    debug=False,
    enable_dashboard=True,
    enable_metrics=True,
    enable_api=True,
    cors_origins=["http://localhost:3000"],
    ssl_keyfile=None,
    ssl_certfile=None
)

# Register components
await server.register_pipeline_manager(pipeline_manager)
await server.register_receiver(weather_wire_receiver)
await server.register_metrics_collector(metrics_collector)

# Start server
await server.start()
```

**Key Features:**
- **FastAPI Framework**: Modern async web framework with automatic OpenAPI documentation
- **Component Integration**: Seamless integration with pipeline, receiver, and metrics components
- **Security**: CORS support, SSL/TLS, and authentication middleware
- **Performance**: Async request handling with connection pooling
- **Monitoring**: Built-in request/response logging and performance tracking
- **Error Handling**: Comprehensive error handling with structured responses

### REST API

Comprehensive REST API for system interaction:

```python
from fastapi import FastAPI
from nwws.webserver.api import (
    health_router,
    metrics_router,
    pipeline_router,
    receiver_router
)

# API endpoints are automatically registered
app = FastAPI(
    title="NWWS2MQTT API",
    description="REST API for NWWS2MQTT weather data processing system",
    version="1.0.0"
)

# Access API endpoints
# GET /health - System health status
# GET /health/detailed - Detailed component health
# GET /metrics - Prometheus metrics
# GET /api/v1/pipeline/status - Pipeline status
# POST /api/v1/pipeline/start - Start pipeline
# POST /api/v1/pipeline/stop - Stop pipeline
# GET /api/v1/receiver/status - Receiver connection status
# GET /api/v1/receiver/stats - Receiver statistics
```

**API Features:**
- **OpenAPI Documentation**: Automatic API documentation with Swagger UI
- **Versioning**: API versioning support for backward compatibility
- **Authentication**: Token-based authentication for administrative endpoints
- **Rate Limiting**: Request rate limiting and throttling
- **Input Validation**: Comprehensive request validation with Pydantic models
- **Error Responses**: Standardized error response format

### Dashboard

Real-time web dashboard for system monitoring:

```python
# Dashboard features
dashboard_features = {
    "real_time_stats": "Live system statistics updates",
    "connection_monitoring": "XMPP connection health visualization",
    "message_processing": "Processing throughput and error rates",
    "geographic_visualization": "Weather data geographic distribution",
    "performance_metrics": "System performance and resource usage",
    "error_tracking": "Error logs and failure analysis",
    "configuration_display": "Current system configuration view"
}

# Access dashboard
# http://localhost:8081/ - Main dashboard
# http://localhost:8081/stats - Statistics page
# http://localhost:8081/config - Configuration page
# http://localhost:8081/logs - Log viewer
```

**Dashboard Features:**
- **Real-time Updates**: WebSocket-based live data updates
- **Interactive Charts**: Dynamic charts and graphs using Chart.js
- **Responsive Design**: Mobile-friendly responsive layout
- **Dark/Light Themes**: Configurable UI themes
- **Customizable Views**: User-configurable dashboard layouts
- **Export Capabilities**: Data export in various formats

### WebSocket Services

Real-time data streaming for live updates:

```python
from nwws.webserver.dashboard.websocket import WebSocketManager

# WebSocket endpoints
websocket_endpoints = {
    "/ws/stats": "Real-time statistics stream",
    "/ws/logs": "Live log streaming",
    "/ws/events": "Pipeline event stream",
    "/ws/metrics": "Metrics data stream"
}

# Client-side WebSocket usage
const ws = new WebSocket('ws://localhost:8081/ws/stats');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    updateDashboard(data);
};

ws.onopen = function(event) {
    console.log('Connected to stats stream');
};
```

**WebSocket Features:**
- **Multiple Streams**: Separate streams for different data types
- **Message Filtering**: Client-side filtering of message types
- **Reconnection**: Automatic reconnection with exponential backoff
- **Compression**: Optional message compression for large datasets
- **Authentication**: Token-based WebSocket authentication
- **Rate Limiting**: Message rate limiting to prevent client overload

## Configuration

### Server Configuration

```python
from nwws.webserver.config import WebServerConfig

config = WebServerConfig(
    # Basic server settings
    host="0.0.0.0",                     # Server host address
    port=8081,                          # Server port
    debug=False,                        # Debug mode
    reload=False,                       # Auto-reload on code changes
    
    # Feature toggles
    enable_dashboard=True,              # Enable web dashboard
    enable_metrics=True,                # Enable metrics endpoint
    enable_api=True,                    # Enable REST API
    enable_websockets=True,             # Enable WebSocket services
    
    # Security settings
    cors_origins=["*"],                 # CORS allowed origins
    ssl_keyfile=None,                   # SSL private key file
    ssl_certfile=None,                  # SSL certificate file
    api_key_header="X-API-Key",         # API key header name
    session_secret="your-secret-key",   # Session secret
    
    # Performance settings
    max_connections=1000,               # Maximum concurrent connections
    request_timeout=30.0,               # Request timeout seconds
    websocket_timeout=300.0,            # WebSocket timeout seconds
    static_file_cache=3600,             # Static file cache seconds
    
    # Dashboard settings
    dashboard_title="NWWS2MQTT Monitor", # Dashboard title
    dashboard_theme="dark",             # Default theme (dark/light)
    refresh_interval=5.0,               # Dashboard refresh interval
    chart_history_points=100,           # Chart history data points
    
    # Logging settings
    access_log=True,                    # Enable access logging
    access_log_format="combined",       # Access log format
    log_requests=True,                  # Log all requests
    log_responses=False,                # Log response bodies
)
```

### Environment Variables

```bash
# Server configuration
WEBSERVER_HOST=0.0.0.0
WEBSERVER_PORT=8081
WEBSERVER_DEBUG=false
WEBSERVER_RELOAD=false

# Feature toggles
WEBSERVER_ENABLE_DASHBOARD=true
WEBSERVER_ENABLE_METRICS=true
WEBSERVER_ENABLE_API=true
WEBSERVER_ENABLE_WEBSOCKETS=true

# Security settings
WEBSERVER_CORS_ORIGINS=["http://localhost:3000"]
WEBSERVER_SSL_KEYFILE=/path/to/ssl/key.pem
WEBSERVER_SSL_CERTFILE=/path/to/ssl/cert.pem
WEBSERVER_API_KEY_HEADER=X-API-Key
WEBSERVER_SESSION_SECRET=your-secret-key

# Performance settings
WEBSERVER_MAX_CONNECTIONS=1000
WEBSERVER_REQUEST_TIMEOUT=30.0
WEBSERVER_WEBSOCKET_TIMEOUT=300.0

# Dashboard settings
WEBSERVER_DASHBOARD_TITLE="NWWS2MQTT Monitor"
WEBSERVER_DASHBOARD_THEME=dark
WEBSERVER_REFRESH_INTERVAL=5.0
```

## API Endpoints

### Health Endpoints

```python
# GET /health
{
    "status": "healthy",
    "timestamp": "2023-12-15T12:00:00Z",
    "uptime_seconds": 3600,
    "version": "1.0.0"
}

# GET /health/detailed
{
    "status": "healthy",
    "timestamp": "2023-12-15T12:00:00Z",
    "components": {
        "webserver": {"status": "healthy", "details": "Server running"},
        "pipeline": {"status": "healthy", "details": "Processing normally"},
        "receiver": {"status": "healthy", "details": "Connected to NWWS-OI"},
        "database": {"status": "healthy", "details": "Connection pool healthy"},
        "metrics": {"status": "healthy", "details": "Collecting metrics"}
    },
    "system": {
        "cpu_percent": 25.4,
        "memory_percent": 45.2,
        "disk_usage_percent": 78.1,
        "load_average": [1.2, 1.1, 1.0]
    }
}
```

### Pipeline Control Endpoints

```python
# GET /api/v1/pipeline/status
{
    "pipeline_id": "main-pipeline",
    "status": "running",
    "uptime_seconds": 1800,
    "events_processed": 1250,
    "events_per_minute": 8.3,
    "success_rate": 0.998,
    "error_rate": 0.002,
    "active_filters": ["duplicate-filter", "test-msg-filter"],
    "active_transformers": ["noaa-parser", "xml-parser"],
    "active_outputs": ["mqtt-primary", "console-debug"]
}

# POST /api/v1/pipeline/start
{
    "message": "Pipeline started successfully",
    "pipeline_id": "main-pipeline",
    "timestamp": "2023-12-15T12:01:00Z"
}

# POST /api/v1/pipeline/stop
{
    "message": "Pipeline stopped successfully", 
    "pipeline_id": "main-pipeline",
    "timestamp": "2023-12-15T12:01:30Z",
    "events_processed_total": 1275
}

# GET /api/v1/pipeline/config
{
    "pipeline_id": "main-pipeline",
    "configuration": {
        "filters": [...],
        "transformers": [...],
        "outputs": [...]
    },
    "last_modified": "2023-12-15T10:00:00Z"
}
```

### Receiver Status Endpoints

```python
# GET /api/v1/receiver/status
{
    "receiver_id": "nwws-oi-client",
    "connection_status": "connected",
    "server": "nwws-oi.weather.gov",
    "connection_uptime_seconds": 3600,
    "last_message_timestamp": "2023-12-15T11:59:30Z",
    "messages_received_total": 1250,
    "messages_per_minute": 8.3,
    "reconnection_count": 0,
    "authentication_failures": 0
}

# GET /api/v1/receiver/stats
{
    "receiver_id": "nwws-oi-client",
    "statistics": {
        "messages_received": 1250,
        "messages_processed": 1247,
        "messages_failed": 3,
        "success_rate": 0.998,
        "processing_rate_per_minute": 8.3,
        "top_product_types": {
            "FXUS61": 45,
            "WWUS81": 32,
            "FXUS62": 28
        },
        "top_sources": {
            "KBOU": 23,
            "KDEN": 18,
            "KGJT": 15
        }
    },
    "performance": {
        "avg_latency_ms": 45.2,
        "memory_usage_mb": 128.5,
        "cpu_percent": 15.2
    }
}
```

### Metrics Endpoints

```python
# GET /metrics - Prometheus format
# HELP nwws2mqtt_messages_received_total Total messages received
# TYPE nwws2mqtt_messages_received_total counter
nwws2mqtt_messages_received_total{source="KBOU"} 150
nwws2mqtt_messages_received_total{source="KDEN"} 120

# GET /api/v1/metrics/json - JSON format
{
    "timestamp": "2023-12-15T12:00:00Z",
    "metrics": {
        "messages_received_total": 1250,
        "messages_processed_total": 1247,
        "connection_status": 1,
        "processing_success_rate": 0.998
    }
}
```

## Dashboard Features

### Real-time Statistics

The dashboard provides live system monitoring with:

- **Connection Status**: Visual indicators for NWWS-OI connection health
- **Processing Metrics**: Real-time charts of message processing rates
- **Error Tracking**: Live error logs and failure analysis
- **Performance Monitoring**: CPU, memory, and network usage graphs
- **Geographic Distribution**: Map visualization of weather data sources

### Interactive Charts

```javascript
// Chart.js configuration for real-time updates
const statsChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Messages/Minute',
            data: [],
            borderColor: 'rgb(75, 192, 192)',
            tension: 0.1
        }]
    },
    options: {
        responsive: true,
        scales: {
            x: {
                type: 'time',
                time: {
                    unit: 'minute'
                }
            }
        },
        plugins: {
            legend: {
                display: true
            }
        }
    }
});

// WebSocket data handler
function updateChart(data) {
    statsChart.data.labels.push(new Date());
    statsChart.data.datasets[0].data.push(data.messages_per_minute);
    
    // Keep only last 50 data points
    if (statsChart.data.labels.length > 50) {
        statsChart.data.labels.shift();
        statsChart.data.datasets[0].data.shift();
    }
    
    statsChart.update('none');
}
```

### Configuration Display

```html
<!-- Configuration viewer -->
<div class="config-viewer">
    <h3>Current Configuration</h3>
    <div class="config-section">
        <h4>Pipeline Settings</h4>
        <pre id="pipeline-config"></pre>
    </div>
    <div class="config-section">
        <h4>Receiver Settings</h4>
        <pre id="receiver-config"></pre>
    </div>
    <div class="config-section">
        <h4>Output Handlers</h4>
        <pre id="output-config"></pre>
    </div>
</div>
```

## Security

### Authentication

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_api_key(token: str = Depends(security)) -> str:
    """Verify API key for administrative endpoints."""
    if token.credentials != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return token.credentials

# Protected endpoint
@app.post("/api/v1/pipeline/restart")
async def restart_pipeline(api_key: str = Depends(verify_api_key)):
    await pipeline_manager.restart()
    return {"message": "Pipeline restarted"}
```

### CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://dashboard.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### SSL/TLS Support

```python
import ssl
import uvicorn

# SSL context
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain('/path/to/cert.pem', '/path/to/key.pem')

# Run with SSL
uvicorn.run(
    app,
    host="0.0.0.0",
    port=8443,
    ssl_keyfile="/path/to/key.pem",
    ssl_certfile="/path/to/cert.pem"
)
```

## Performance Optimization

### Async Request Handling

```python
from fastapi import BackgroundTasks
import asyncio

@app.get("/api/v1/system/cleanup")
async def cleanup_system(background_tasks: BackgroundTasks):
    """Trigger system cleanup in background."""
    background_tasks.add_task(perform_cleanup)
    return {"message": "Cleanup started"}

async def perform_cleanup():
    """Perform resource cleanup asynchronously."""
    await asyncio.gather(
        cleanup_logs(),
        cleanup_cache(),
        cleanup_temp_files()
    )
```

### Response Caching

```python
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

@cache(expire=60)  # Cache for 60 seconds
@app.get("/api/v1/stats/summary")
async def get_stats_summary():
    """Get cached statistics summary."""
    return await generate_stats_summary()
```

### Static File Optimization

```python
from fastapi.staticfiles import StaticFiles

# Serve static files with caching headers
app.mount("/static", StaticFiles(
    directory="dashboard/static",
    html=True
), name="static")

# Add cache headers middleware
@app.middleware("http")
async def add_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=3600"
    return response
```

## Monitoring and Logging

### Request Logging

```python
import time
from starlette.middleware.base import BaseHTTPMiddleware

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        logger.info(
            "HTTP request processed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time_ms=round(process_time * 1000, 2)
        )
        
        return response

app.add_middleware(RequestLoggingMiddleware)
```

### Error Tracking

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(
        "Unhandled exception",
        method=request.method,
        url=str(request.url),
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now().isoformat()
        }
    )
```

## Testing

### API Testing

```python
import pytest
from fastapi.testclient import TestClient
from nwws.webserver import WebServer

@pytest.fixture
def client():
    server = WebServer(enable_dashboard=False, enable_websockets=False)
    return TestClient(server.app)

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_pipeline_control(client):
    # Test pipeline start
    response = client.post("/api/v1/pipeline/start")
    assert response.status_code == 200
    
    # Test pipeline status
    response = client.get("/api/v1/pipeline/status")
    assert response.status_code == 200
    assert response.json()["status"] == "running"
```

### WebSocket Testing

```python
import pytest
from fastapi.testclient import TestClient
import json

def test_websocket_stats(client):
    with client.websocket_connect("/ws/stats") as websocket:
        # Send subscription message
        websocket.send_json({"subscribe": "stats"})
        
        # Receive initial data
        data = websocket.receive_json()
        assert "timestamp" in data
        assert "statistics" in data
```

### Load Testing

```python
import asyncio
import aiohttp
import time

async def load_test_api():
    """Simple load test for API endpoints."""
    concurrent_requests = 100
    total_requests = 1000
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(concurrent_requests)
        
        async def make_request():
            async with semaphore:
                async with session.get("http://localhost:8081/health") as response:
                    return response.status
        
        # Execute requests
        tasks = [make_request() for _ in range(total_requests)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        # Calculate statistics
        success_count = sum(1 for status in results if status == 200)
        total_time = end_time - start_time
        rps = total_requests / total_time
        
        print(f"Total requests: {total_requests}")
        print(f"Successful requests: {success_count}")
        print(f"Success rate: {success_count/total_requests:.2%}")
        print(f"Requests per second: {rps:.2f}")
        print(f"Total time: {total_time:.2f}s")

# Run load test
asyncio.run(load_test_api())
```

## Deployment

### Docker Configuration

```dockerfile
# Dockerfile for webserver
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY src/ ./src/
COPY static/ ./static/

# Expose port
EXPOSE 8081

# Run webserver
CMD ["uvicorn", "nwws.webserver:app", "--host", "0.0.0.0", "--port", "8081"]
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name dashboard.example.com;
    
    location / {
        proxy_pass http://localhost:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /ws/ {
        proxy_pass http://localhost:8081;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
    
    location /static/ {
        alias /var/www/static/;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }
}
```

## Best Practices

1. **Security**: Always use HTTPS in production and implement proper authentication
2. **Performance**: Use caching, async operations, and connection pooling
3. **Monitoring**: Implement comprehensive logging and error tracking
4. **Testing**: Test all endpoints and WebSocket connections thoroughly
5. **Documentation**: Keep API documentation up to date with OpenAPI
6. **Error Handling**: Provide meaningful error messages and proper HTTP status codes
7. **Scalability**: Design for horizontal scaling with load balancers
8. **Resource Management**: Monitor memory usage and connection counts
9. **Configuration**: Use environment variables for deployment-specific settings
10. **Backup**: Implement proper backup strategies for configuration and data

This webserver package provides a comprehensive web interface for monitoring and controlling the NWWS2MQTT system, enabling effective operations and maintenance of the weather data processing pipeline.