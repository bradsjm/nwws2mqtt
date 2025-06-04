// NWWS2MQTT Dashboard JavaScript
// Main dashboard controller with real-time WebSocket updates

class WeatherDashboard {
    constructor(initialData = {}) {
        this.config = {
            websocketUrl: this._getWebSocketUrl(),
            updateInterval: 5000,
            reconnectDelay: 3000,
            maxReconnectAttempts: 10,
            ...initialData
        };
        
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.isConnected = false;
        this.lastUpdateTime = null;
        this.weatherMap = null;
        this.charts = {};
        this.currentMetrics = {};
        this.officeData = {};
        
        // Bind methods to preserve context
        this.handleWebSocketMessage = this.handleWebSocketMessage.bind(this);
        this.handleWebSocketClose = this.handleWebSocketClose.bind(this);
        this.handleWebSocketError = this.handleWebSocketError.bind(this);
        this.handleWebSocketOpen = this.handleWebSocketOpen.bind(this);
    }

    async initialize() {
        try {
            console.log('Initializing NWWS2MQTT Dashboard...');
            
            // Initialize components
            await this._initializeMap();
            await this._initializeCharts();
            await this._loadInitialData();
            
            // Start WebSocket connection
            this._connectWebSocket();
            
            // Setup periodic updates fallback
            this._startFallbackUpdates();
            
            console.log('Dashboard initialization complete');
        } catch (error) {
            console.error('Dashboard initialization failed:', error);
            this._showError('Failed to initialize dashboard: ' + error.message);
        }
    }

    async _initializeMap() {
        try {
            // Initialize Leaflet map
            this.weatherMap = new WeatherOfficeMap('weather-map');
            await this.weatherMap.initialize();
            
            // Load office boundaries
            const response = await fetch('/api/geo/offices?simplification=web');
            if (!response.ok) throw new Error('Failed to load office boundaries');
            
            const geoData = await response.json();
            await this.weatherMap.loadOfficeBoundaries(geoData);
            
        } catch (error) {
            console.error('Map initialization failed:', error);
            throw error;
        }
    }

    async _initializeCharts() {
        try {
            // Initialize Chart.js charts
            this.charts.throughput = MetricsChartFactory.createThroughputTimeline('throughput-chart');
            this.charts.latency = MetricsChartFactory.createLatencyHistogram('latency-chart');
            
        } catch (error) {
            console.error('Charts initialization failed:', error);
            throw error;
        }
    }

    async _loadInitialData() {
        try {
            // Load office metadata
            const officeResponse = await fetch('/api/geo/metadata');
            if (officeResponse.ok) {
                const officeData = await officeResponse.json();
                this.officeData = officeData.offices || {};
                this._updateOfficeList();
            }
            
            // Load current metrics
            const metricsResponse = await fetch('/api/metrics/current');
            if (metricsResponse.ok) {
                const metricsData = await metricsResponse.json();
                this._updateMetricsDisplay(metricsData);
            }
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
        }
    }

    _connectWebSocket() {
        try {
            console.log('Connecting to WebSocket:', this.config.websocketUrl);
            
            this.websocket = new WebSocket(this.config.websocketUrl);
            this.websocket.onopen = this.handleWebSocketOpen;
            this.websocket.onmessage = this.handleWebSocketMessage;
            this.websocket.onclose = this.handleWebSocketClose;
            this.websocket.onerror = this.handleWebSocketError;
            
            this._updateConnectionStatus('connecting');
            
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this._updateConnectionStatus('disconnected');
            this._scheduleReconnect();
        }
    }

    handleWebSocketOpen(event) {
        console.log('WebSocket connected successfully');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this._updateConnectionStatus('connected');
        
        // Send initial ping
        this._sendWebSocketMessage({ type: 'ping' });
    }

    handleWebSocketMessage(event) {
        try {
            const message = JSON.parse(event.data);
            
            switch (message.type) {
                case 'initial_data':
                case 'metrics_update':
                    this._updateMetricsDisplay(message.data);
                    this.lastUpdateTime = message.timestamp;
                    break;
                    
                case 'pong':
                    // Connection is alive
                    break;
                    
                case 'data_response':
                    this._updateMetricsDisplay(message.data);
                    break;
                    
                case 'error':
                    console.error('WebSocket error message:', message.message);
                    this._showError('Server error: ' + message.message);
                    break;
                    
                default:
                    console.warn('Unknown WebSocket message type:', message.type);
            }
            
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    }

    handleWebSocketClose(event) {
        console.log('WebSocket connection closed:', event.code, event.reason);
        this.isConnected = false;
        this._updateConnectionStatus('disconnected');
        
        if (!event.wasClean) {
            this._scheduleReconnect();
        }
    }

    handleWebSocketError(error) {
        console.error('WebSocket error:', error);
        this._updateConnectionStatus('disconnected');
    }

    _scheduleReconnect() {
        if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this._showError('Lost connection to server. Please refresh the page.');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = this.config.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);
        
        console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
        
        setTimeout(() => {
            if (!this.isConnected) {
                this._connectWebSocket();
            }
        }, delay);
    }

    _sendWebSocketMessage(message) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(message));
        }
    }

    _updateMetricsDisplay(data) {
        if (!data) return;
        
        this.currentMetrics = data;
        
        // Update metric cards
        this._updateMetricCards(data);
        
        // Update charts
        this._updateCharts(data);
        
        // Update map activity
        this._updateMapActivity(data);
        
        // Update footer timestamp
        this._updateLastUpdateTime();
    }

    _updateMetricCards(data) {
        const throughput = data.throughput || {};
        const latency = data.latency || {};
        const errors = data.errors || {};
        const geographic = data.by_office || {};
        
        // Messages per minute
        const messagesPerMin = throughput.messages_per_minute || 0;
        this._updateMetricCard('messages-per-minute', this._formatNumber(messagesPerMin));
        
        // Active offices
        const activeOffices = Object.keys(geographic).filter(
            office => geographic[office].messages_processed_total > 0
        ).length;
        this._updateMetricCard('active-offices', activeOffices);
        
        // Average latency
        const avgLatency = latency.avg_ms || 0;
        this._updateMetricCard('avg-latency', this._formatNumber(avgLatency, 1));
        
        // Error rate
        const errorRate = errors.rate_percent || 0;
        this._updateMetricCard('error-rate', this._formatNumber(errorRate, 2));
        
        // Update system health indicator
        this._updateSystemHealth(errorRate);
    }

    _updateMetricCard(elementId, value, trend = null) {
        const valueElement = document.getElementById(elementId);
        if (valueElement) {
            valueElement.textContent = value;
        }
        
        if (trend !== null) {
            const trendElement = document.getElementById(elementId.replace('-', '-trend-'));
            if (trendElement) {
                trendElement.textContent = trend;
                trendElement.className = `metric-trend ${this._getTrendClass(trend)}`;
            }
        }
    }

    _updateCharts(data) {
        if (this.charts.throughput) {
            const throughputData = this._prepareThroughputData(data);
            this.charts.throughput.updateData(throughputData);
        }
        
        if (this.charts.latency) {
            const latencyData = this._prepareLatencyData(data);
            this.charts.latency.updateData(latencyData);
        }
    }

    _updateMapActivity(data) {
        if (this.weatherMap && data.by_office) {
            this.weatherMap.updateActivityLevels(data.by_office);
        }
    }

    _updateOfficeList() {
        const officeListElement = document.getElementById('office-list');
        if (!officeListElement || !this.officeData) return;
        
        const offices = Object.values(this.officeData).sort((a, b) => 
            a.name.localeCompare(b.name)
        );
        
        officeListElement.innerHTML = offices.map(office => `
            <div class="office-item" data-office-id="${office.id}">
                <div>
                    <div class="office-name">${office.name}</div>
                    <div class="office-details">${office.region} • ${office.id}</div>
                </div>
                <div class="office-status" id="status-${office.id}"></div>
            </div>
        `).join('');
        
        // Add click handlers
        officeListElement.querySelectorAll('.office-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const officeId = e.currentTarget.dataset.officeId;
                this._focusOnOffice(officeId);
            });
        });
    }

    _updateConnectionStatus(status) {
        const indicator = document.getElementById('ws-indicator');
        const statusText = document.getElementById('ws-status');
        const connectionStatusDot = document.getElementById('connection-status');
        const connectionText = document.getElementById('connection-text');
        
        const statusConfig = {
            connected: {
                class: 'connected',
                text: 'Connected',
                color: 'var(--success-color)'
            },
            connecting: {
                class: 'connecting', 
                text: 'Connecting...',
                color: 'var(--warning-color)'
            },
            disconnected: {
                class: 'disconnected',
                text: 'Disconnected',
                color: 'var(--error-color)'
            }
        };
        
        const config = statusConfig[status] || statusConfig.disconnected;
        
        if (indicator) {
            indicator.className = `connection-indicator ${config.class}`;
        }
        
        if (statusText) {
            statusText.textContent = config.text;
        }
        
        if (connectionStatusDot) {
            connectionStatusDot.className = `status-dot ${config.class}`;
        }
        
        if (connectionText) {
            connectionText.textContent = config.text;
        }
    }

    _updateSystemHealth(errorRate) {
        const healthDot = document.getElementById('system-health-status');
        const healthText = document.getElementById('system-health-text');
        
        let healthStatus = 'healthy';
        let healthClass = '';
        
        if (errorRate > 10) {
            healthStatus = 'Critical';
            healthClass = 'error';
        } else if (errorRate > 5) {
            healthStatus = 'Degraded';
            healthClass = 'warning';
        } else {
            healthStatus = 'Healthy';
            healthClass = '';
        }
        
        if (healthDot) {
            healthDot.className = `status-dot ${healthClass}`;
        }
        
        if (healthText) {
            healthText.textContent = healthStatus;
        }
    }

    _updateLastUpdateTime() {
        const lastUpdateElement = document.getElementById('last-update');
        if (lastUpdateElement) {
            const now = new Date();
            lastUpdateElement.textContent = `Last updated: ${now.toLocaleTimeString()}`;
        }
    }

    _focusOnOffice(officeId) {
        if (this.weatherMap) {
            this.weatherMap.focusOnOffice(officeId);
        }
        
        // Update office status in sidebar
        this._highlightOffice(officeId);
    }

    _highlightOffice(officeId) {
        // Remove previous highlights
        document.querySelectorAll('.office-item').forEach(item => {
            item.classList.remove('highlighted');
        });
        
        // Highlight selected office
        const officeElement = document.querySelector(`[data-office-id="${officeId}"]`);
        if (officeElement) {
            officeElement.classList.add('highlighted');
            officeElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    _prepareThroughputData(data) {
        const throughput = data.throughput || {};
        const timestamp = data.timestamp || Date.now() / 1000;
        
        return {
            timestamp: timestamp * 1000, // Convert to milliseconds
            messagesPerMinute: throughput.messages_per_minute || 0,
            totalMessages: throughput.total_messages || 0,
            messagesByType: throughput.messages_by_type || {}
        };
    }

    _prepareLatencyData(data) {
        const latency = data.latency || {};
        
        return {
            average: latency.avg_ms || 0,
            p95: latency.p95_ms || 0,
            p99: latency.p99_ms || 0,
            buckets: latency.histogram_buckets || []
        };
    }

    _startFallbackUpdates() {
        // Fallback update mechanism if WebSocket fails
        setInterval(async () => {
            if (!this.isConnected) {
                try {
                    const response = await fetch('/api/metrics/current');
                    if (response.ok) {
                        const data = await response.json();
                        this._updateMetricsDisplay(data);
                    }
                } catch (error) {
                    console.warn('Fallback update failed:', error);
                }
            }
        }, this.config.updateInterval * 2); // Less frequent than WebSocket updates
    }

    _getWebSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return `${protocol}//${host}/ws/realtime`;
    }

    _formatNumber(value, decimals = 0) {
        if (typeof value !== 'number' || isNaN(value)) {
            return '--';
        }
        
        if (value >= 1000000) {
            return (value / 1000000).toFixed(1) + 'M';
        } else if (value >= 1000) {
            return (value / 1000).toFixed(1) + 'K';
        } else {
            return value.toFixed(decimals);
        }
    }

    _getTrendClass(trendValue) {
        if (trendValue > 0) return 'trend-up';
        if (trendValue < 0) return 'trend-down';
        return 'trend-stable';
    }

    _showError(message) {
        console.error('Dashboard error:', message);
        
        // Show error in UI
        const errorTemplate = document.getElementById('error-template');
        if (errorTemplate) {
            const errorElement = errorTemplate.cloneNode(true);
            errorElement.id = 'error-' + Date.now();
            errorElement.style.display = 'block';
            
            const errorText = errorElement.querySelector('#error-text');
            if (errorText) {
                errorText.textContent = message;
            }
            
            document.body.appendChild(errorElement);
            
            // Auto-remove after 10 seconds
            setTimeout(() => {
                errorElement.remove();
            }, 10000);
        }
    }

    // Public API methods
    requestDataUpdate() {
        this._sendWebSocketMessage({ type: 'request_data' });
    }

    refreshMap() {
        if (this.weatherMap) {
            this.weatherMap.refresh();
        }
    }

    getOfficeMetrics(officeId) {
        return this.currentMetrics?.by_office?.[officeId] || null;
    }

    destroy() {
        if (this.websocket) {
            this.websocket.close();
        }
        
        if (this.weatherMap) {
            this.weatherMap.destroy();
        }
        
        Object.values(this.charts).forEach(chart => {
            if (chart && chart.destroy) {
                chart.destroy();
            }
        });
    }
}

// Utility functions
function formatTimestamp(timestamp) {
    return new Date(timestamp * 1000).toLocaleString();
}

function calculateTimeDifference(timestamp) {
    const now = Date.now() / 1000;
    const diff = now - timestamp;
    
    if (diff < 60) {
        return `${Math.floor(diff)}s ago`;
    } else if (diff < 3600) {
        return `${Math.floor(diff / 60)}m ago`;
    } else {
        return `${Math.floor(diff / 3600)}h ago`;
    }
}