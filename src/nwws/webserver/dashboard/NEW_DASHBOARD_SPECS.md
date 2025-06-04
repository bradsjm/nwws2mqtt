# Development Brief: NWWS2MQTT Weather Operations Dashboard

## **Project Overview**
Build a real-time web dashboard for monitoring the NWWS2MQTT weather message processing system. The dashboard will visualize message flow, system performance, and geographic distribution of weather activity across US Weather Forecast Offices.

## **Technical Requirements**

### **Backend Stack**
- **Python 3.12+** with existing project dependencies
- **FastAPI** for API endpoints and dashboard serving
- **GeoPandas/Pandas** for geographic data processing (following existing `ugc_loader.py` pattern)
- **In-memory caching only** (no Redis/external cache stores)
- **Integration** with existing metrics collectors (`PipelineStatsCollector`, `WeatherWireStatsCollector`)

### **Frontend Stack**
- **Leaflet.js** (~40KB) for interactive weather office mapping
- **Chart.js** with real-time plugin for metrics visualization
- **Vanilla JavaScript** (ES6+) with module system
- **CSS Grid/Flexbox** for responsive layouts
- **WebSocket** for real-time data updates

## **Core Components to Develop**

nwws2mqtt/
├── src/nwws/
│   ├── dashboard/                 # New dashboard module
│   │   ├── __init__.py
│   │   ├── server.py             # FastAPI dashboard routes
│   │   ├── geo_provider.py       # Geographic data processing
│   │   ├── templates/            # Jinja2 HTML templates
│   │   │   ├── dashboard.html
│   │   │   └── components/
│   │   └── static/               # CSS, JS, assets
│   │       ├── css/
│   │       ├── js/
│   │       └── libs/             # Vendored libraries
│   ├── metrics/                  # Existing metrics system
│   ├── pipeline/                 # Existing pipeline
│   └── receiver/                 # Existing receiver

### **1. Geographic Data Provider (`nwws/dashboard/geo_provider.py`)**
```python
class WeatherGeoDataProvider:
    """Manages geographic data loading and web optimization."""

    def __init__(self):
        # Load CWA, states, UGC data from pyiem parquet files
        # Cache simplified geometries in memory
        # Create office metadata lookup

    def get_cwa_geojson(self, simplification_level="web") -> dict:
        # Return simplified CWA boundaries as GeoJSON

    def get_office_metadata(self) -> dict:
        # Return office locations, regions, coverage areas

    def get_activity_overlay_data(self, metrics_data) -> dict:
        # Combine geo boundaries with current metrics
```

**Key Implementation Details:**
- Follow `ugc_loader.py` pattern for data loading
- Use `shapely.simplify()` for web-optimized geometries
- Cache multiple resolution levels (overview, detailed)
- Convert geopandas to GeoJSON for web delivery

### **2. Dashboard API Server (`nwws/dashboard/api_server.py`)**
```python
class DashboardApiServer:
    """FastAPI server for dashboard endpoints."""

    def __init__(self, metrics_registry, geo_provider):
        # Initialize with existing metrics collectors
        # Setup in-memory cache with TTL
        # Configure WebSocket for real-time updates

    # Endpoints to implement:
    # GET /dashboard - Main HTML dashboard
    # GET /api/geo/offices - Office boundaries + metadata
    # GET /api/metrics/current - Current system metrics
    # GET /api/metrics/geographic - Metrics by office
    # GET /api/metrics/timeseries - Historical data for charts
    # WebSocket /ws/realtime - Live metric updates
```

**Key Implementation Details:**
- Integrate with existing `MetricRegistry`
- Use `@lru_cache` and time-based invalidation for geo data
- Implement WebSocket broadcasting for real-time updates
- Serve static assets (HTML, CSS, JS)

### **3. Frontend Dashboard Core (`static/js/dashboard.js`)**
```javascript
class WeatherDashboard {
    constructor(config) {
        // Initialize map, charts, WebSocket connection
        // Setup auto-refresh and error handling
    }

    async initialize() {
        // Load geographic data and create map
        // Initialize chart components
        // Start real-time data stream
    }

    updateOfficeActivity(data) {
        // Color-code offices by message volume
        // Update tooltips with current stats
    }

    updateMetricsCharts(data) {
        // Refresh latency histograms
        // Update throughput time series
        // Show alert indicators
    }
}
```

### **4. Map Visualization Component (`static/js/weather-map.js`)**
```javascript
class WeatherOfficeMap {
    constructor(containerId) {
        // Initialize Leaflet map
        // Load US basemap layer
        // Setup CWA boundary overlay
    }

    loadOfficeBoundaries(geojsonData) {
        // Render CWA polygons
        // Setup click handlers for drill-down
        // Add hover tooltips
    }

    updateActivityLevels(activityData) {
        // Color offices by message volume
        // Use heat map style (blue → yellow → red)
        // Update popup content with current stats
    }
}
```

### **5. Metrics Chart Factory (`static/js/charts.js`)**
```javascript
class MetricsChartFactory {
    static createLatencyHistogram(canvasId, data) {
        // Chart.js bar chart with percentile lines
        // Responsive design with threshold markers
    }

    static createThroughputTimeline(canvasId) {
        // Real-time line chart with streaming data
        // Multi-series for different message types
    }

    static createProductBreakdown(canvasId, data) {
        // Donut chart for message type distribution
        // Color-coded by severity (warnings vs. routine)
    }
}
```

## **Data Integration Points**

### **Existing Metrics to Visualize**
From `PipelineStatsCollector` and `WeatherWireStatsCollector`:
- **Message throughput**: `messages_processed_total` by office
- **Processing latency**: `message_processing_duration_seconds` histogram
- **Queue status**: Current queue sizes and backpressure events
- **Error rates**: Connection failures, processing errors
- **Office activity**: Messages per WFO with geographic context

### **Geographic Data Sources**
From pyiem parquet files (via `importlib.resources`):
- **CWA boundaries** (`cwa.parquet`): Weather Forecast Office coverage areas
- **Office metadata**: Names, regions, coordinates
- **UGC zones** (`ugcs_*.parquet`): Counties/zones for detailed breakdown

## **Key Features to Implement**

### **Real-Time Geographic Heat Map**
- US map showing WFO activity levels via color intensity
- Click office boundaries for detailed metrics
- Hover tooltips with current stats
- Automatic updates via WebSocket

### **System Health Overview**
- Large status indicators (connection health, queue status)
- Key metrics with trend indicators (↗️↘️→)
- Alert panel for threshold violations
- Throughput sparklines

### **Detailed Analytics**
- Processing latency histogram with P95/P99 markers
- Multi-series timeline charts (by message type)
- Searchable/sortable metrics table
- Export functionality (CSV/JSON)

### **Responsive Design Requirements**
- **Desktop/NOC displays**: Full feature set, large visualizations
- **Tablet**: Condensed layout, touch-friendly interactions
- **Mobile**: Essential metrics only, collapsible sections

## **Performance Requirements**

### **Backend Performance**
- **API Response Time**: <100ms for metrics endpoints
- **Geographic Data**: <500ms initial load, aggressive caching
- **WebSocket Updates**: 1-5 second intervals, efficient diffing
- **Memory Usage**: <500MB additional overhead

### **Frontend Performance**
- **Initial Load**: <2 seconds to interactive dashboard
- **Chart Updates**: 60fps animations, smooth real-time updates
- **Map Rendering**: <1 second for office boundary overlay
- **Memory Efficiency**: Cleanup old chart data, prevent leaks

## **Error Handling & Resilience**

### **Backend Fault Tolerance**
- Graceful degradation when parquet files unavailable
- Fallback modes for missing metric collectors
- WebSocket reconnection logic
- Health check endpoints

### **Frontend Error Recovery**
- Display "stale data" indicators when WebSocket disconnects
- Automatic retry logic with exponential backoff
- Clear error messages with suggested actions
- Offline mode with cached data

## **Testing Strategy**

### **Backend Testing**
- Unit tests for geographic data processing
- Integration tests with mock metrics collectors
- API endpoint testing with FastAPI test client
- WebSocket connection testing

### **Frontend Testing**
- Chart rendering with mock data
- Map interaction testing
- WebSocket message handling
- Responsive design validation

## **Deliverables**

1. **Geographic data provider** with optimized web delivery
2. **FastAPI dashboard server** with WebSocket support
3. **Interactive web dashboard** with real-time updates
4. **Comprehensive documentation** and deployment guide
5. **Test suite** covering core functionality

## **Success Criteria**
- Dashboard loads within 2 seconds on target hardware
- Real-time updates with <5 second latency
- Intuitive UX for weather operations staff
- Mobile-responsive design
- Zero external service dependencies (except CDN libraries)
- Seamless integration with existing metrics system
