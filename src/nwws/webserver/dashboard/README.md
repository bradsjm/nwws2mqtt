# NWWS2MQTT Dashboard

Real-time weather operations dashboard for monitoring NWWS2MQTT system metrics and geographic activity.

## Overview

The dashboard provides a web-based interface for monitoring:
- Message throughput and processing metrics
- Weather Forecast Office activity levels
- Geographic visualization of office boundaries
- System health and error rates

## Architecture

### Polling-Based Updates

The dashboard uses client-side polling instead of WebSocket connections for real-time updates:

- **Update Interval**: 5 seconds
- **Retry Logic**: 3 consecutive failures before error state
- **Endpoints**: RESTful API endpoints for metrics and geographic data

### Components

#### Backend Components

- **Router** (`router.py`): FastAPI router with dashboard endpoints
- **Geo Endpoints** (`endpoints/geo.py`): Geographic data API
- **Metrics Endpoints** (`endpoints/metrics.py`): System metrics API

#### Frontend Components

- **Dashboard Controller** (`static/js/dashboard.js`): Main application logic with polling
- **Weather Map** (`static/js/weather-map.js`): Interactive Leaflet map
- **Charts** (`static/js/charts.js`): Chart.js visualizations
- **Styles** (`static/css/dashboard.css`): Responsive CSS styling

### API Endpoints

#### Dashboard APIs

- `GET /dashboard/api/metrics` - Current system metrics
- `GET /dashboard/api/geo/boundaries` - Office boundary GeoJSON
- `GET /dashboard/api/geo/metadata` - Office metadata and regions
- `GET /dashboard/api/geo/regions` - Region summary statistics
- `GET /dashboard/api/geo/activity` - Geographic activity data

#### Main Dashboard

- `GET /dashboard/` - Dashboard HTML interface

## Configuration

### Polling Configuration

The dashboard polling behavior can be configured via the initial data object:

```javascript
const initialData = {
    updateInterval: 5000,        // 5 second polling interval
    maxRetries: 3,               // Max consecutive failures
    retryDelay: 2000,           // Delay between retries
    api_endpoints: {
        metrics: "/dashboard/api/metrics",
        geographic: "/dashboard/api/geo/activity"
    }
};
```

### Connection States

The dashboard displays different connection states:

- **Starting**: Initial polling setup
- **Polling**: Successfully fetching data
- **Retrying**: Temporary failures, attempting retry
- **Failed**: Max retries exceeded
- **Stopped**: Polling manually stopped

## Features

### Real-time Metrics

- Messages per minute
- Active office count
- Average processing latency
- Error rate percentage
- System health status

### Interactive Map

- US Weather Forecast Office boundaries
- Activity level color coding
- Office details on click/hover
- Zoom and pan controls
- Activity legend

### Responsive Design

- Mobile-friendly layout
- Adaptive grid system
- Touch-friendly controls
- Print-optimized styles

## Development

### Adding New Metrics

1. Update the metrics endpoint to include new data
2. Modify `_updateMetricsDisplay()` in dashboard.js
3. Add corresponding HTML elements and CSS styles

### Customizing Polling

The polling mechanism can be customized by modifying the `WeatherDashboard` class:

```javascript
// Change polling interval
dashboard.config.updateInterval = 10000; // 10 seconds

// Modify retry behavior
dashboard.config.maxRetries = 5;
dashboard.config.retryDelay = 3000;
```

### Error Handling

The dashboard includes comprehensive error handling:

- Network timeouts
- HTTP error responses
- JSON parsing errors
- Geographic data loading failures
- Chart initialization errors

## Browser Support

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## Dependencies

### Frontend Libraries

- **Leaflet 1.9.4**: Interactive maps
- **Chart.js 4.4.0**: Data visualization
- **Chart.js Date Adapter**: Time-based charts

### CSS Framework

- Custom CSS grid-based layout
- CSS custom properties for theming
- Responsive breakpoints
- Print media queries

## Performance

### Optimization Features

- Efficient DOM updates
- Chart animation throttling
- Map layer caching
- Polling failure backoff
- Memory cleanup on destroy

### Resource Usage

- Lightweight JavaScript (~50KB)
- Minimal CSS footprint
- Lazy loading of chart data
- Efficient map rendering

## Accessibility

- ARIA labels for interactive elements
- Keyboard navigation support
- High contrast mode support
- Screen reader compatible
- Focus management

## Security

- CSP-compatible implementation
- No inline JavaScript execution
- HTTPS-ready
- XSS protection via proper escaping
- No sensitive data in client storage