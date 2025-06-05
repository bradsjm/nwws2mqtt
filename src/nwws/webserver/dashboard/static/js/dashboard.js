// NWWS2MQTT Dashboard JavaScript

class WeatherDashboard {
    constructor(initialData = {}) {
        this.config = {
            updateInterval: 5000,
            maxRetries: 3,
            retryDelay: 2000,
            ...initialData,
        };

        this.pollingInterval = null;
        this.isPolling = false;
        this.consecutiveFailures = 0;
        this.lastUpdateTime = null;
        this.weatherMap = null;
        this.charts = {};
        this.currentMetrics = {};
        this.officeData = {};
        this.sparklineManager = null;
        this.previousMetrics = {};
        this.hasSparklines = false;

        // Bind methods to preserve context
        this.pollMetrics = this.pollMetrics.bind(this);
    }

    async initialize() {
        try {
            console.log("Initializing NWWS2MQTT Dashboard...");

            // Initialize sparklines first
            await this._initializeSparklines();

            // Initialize components
            await this._initializeMap();
            await this._loadInitialData();

            // Setup RainViewer controls
            this.setupRainViewerControls();

            // Start polling for metrics
            this._startPolling();

            console.log("Dashboard initialization complete");
        } catch (error) {
            console.error("Dashboard initialization failed:", error);
            this._showError(`Failed to initialize dashboard: ${error.message}`);
        }
    }

    async _initializeMap() {
        try {
            // Initialize Leaflet map
            this.weatherMap = new WeatherOfficeMap("weather-map", {
                pollingInterval: this.config.updateInterval,
            });
            await this.weatherMap.initialize();

            // Load office boundaries
            console.log(
                "Fetching office boundaries from /dashboard/api/geo/boundaries...",
            );
            const response = await fetch(
                "/dashboard/api/geo/boundaries?simplification=web",
            );

            console.log(
                "Boundaries response status:",
                response.status,
                response.statusText,
            );

            if (!response.ok) {
                const errorText = await response.text();
                console.error(
                    "Boundaries API error:",
                    response.status,
                    errorText,
                );
                throw new Error(
                    `Failed to load office boundaries: ${response.status} ${errorText}`,
                );
            }

            const geoData = await response.json();
            await this.weatherMap.loadOfficeBoundaries(geoData);
        } catch (error) {
            console.error("Map initialization failed:", error);
            throw error;
        }
    }

    async _initializeSparklines() {
        try {
            console.log("Initializing sparklines...");

            // Check if SparklineManager is available
            if (typeof SparklineManager !== "undefined") {
                this.sparklineManager = new SparklineManager({
                    maxDataPoints: 30,
                });

                this.hasSparklines =
                    await this.sparklineManager.initializeSparklines();

                if (this.hasSparklines) {
                    console.log("Sparklines initialized successfully");
                } else {
                    console.warn(
                        "Sparklines failed to initialize, using fallback mode",
                    );
                }
            } else {
                console.warn(
                    "SparklineManager not available, skipping sparkline initialization",
                );
                this.hasSparklines = false;
            }
        } catch (error) {
            console.error("Sparklines initialization failed:", error);
            this.hasSparklines = false;
        }
    }

    async _loadInitialData() {
        try {
            // Load office metadata
            console.log(
                "Fetching office metadata from /dashboard/api/geo/metadata...",
            );
            const officeResponse = await fetch("/dashboard/api/geo/metadata");

            if (officeResponse.ok) {
                const officeData = await officeResponse.json();
                this.officeData = officeData.offices || {};
                this._updateOfficeList();
            } else {
                const errorText = await officeResponse.text();
                console.error(
                    "Office metadata API error:",
                    officeResponse.status,
                    errorText,
                );
            }

            // Load current metrics
            const metricsEndpoint =
                this.config.api_endpoints?.metrics || "/dashboard/api/metrics";
            const metricsResponse = await fetch(metricsEndpoint);

            if (metricsResponse.ok) {
                const metricsData = await metricsResponse.json();
                this._updateMetricsDisplay(metricsData);
            } else {
                const errorText = await metricsResponse.text();
                console.error(
                    "Metrics API error:",
                    metricsResponse.status,
                    errorText,
                );
            }
        } catch (error) {
            console.error("Failed to load initial data:", error);
        }
    }

    _startPolling() {
        console.log(
            "Starting metrics polling every",
            this.config.updateInterval,
            "ms",
        );
        this.isPolling = true;
        this._updateConnectionStatus("connecting");

        // Initial poll
        this.pollMetrics();

        // Set up interval
        this.pollingInterval = setInterval(
            this.pollMetrics,
            this.config.updateInterval,
        );
    }

    _stopPolling() {
        console.log("Stopping metrics polling");
        this.isPolling = false;

        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }

        this._updateConnectionStatus("disconnected");
    }

    async pollMetrics() {
        if (!this.isPolling) {
            return;
        }

        try {
            const metricsEndpoint =
                this.config.api_endpoints?.metrics || "/dashboard/api/metrics";
            const response = await fetch(metricsEndpoint);

            if (!response.ok) {
                throw new Error(
                    `HTTP ${response.status}: ${response.statusText}`,
                );
            }

            const data = await response.json();

            // Success - reset failure counter and update status
            this.consecutiveFailures = 0;
            this._updateConnectionStatus("connected");

            // Update the display with new data
            this._updateMetricsDisplay(data);
            this.lastUpdateTime = Date.now();
        } catch (error) {
            console.error("Failed to poll metrics:", error);
            this.consecutiveFailures++;

            if (this.consecutiveFailures >= this.config.maxRetries) {
                console.error("Max polling failures reached, stopping polling");
                this._updateConnectionStatus("error");
                this._showError(`Failed to fetch metrics: ${error.message}`);
            } else {
                console.warn(
                    `Polling failure ${this.consecutiveFailures}/${this.config.maxRetries}`,
                );
                this._updateConnectionStatus("warning");
            }
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

        // Update office status indicators
        this._updateOfficeStatusIndicators(data);

        // Update footer timestamp
        this._updateLastUpdateTime();
    }

    _updateMetricCards(data) {
        const throughput = data.throughput || {};
        const latency = data.latency || {};
        const errors = data.errors || {};
        const geographic = data.by_wmo || {};
        const system = data.system || {};
        const timestamp = (data.timestamp || Date.now() / 1000) * 1000;

        // Messages per minute with trend
        const messagesPerMin = throughput.messages_per_minute || 0;
        const messagesTrend = this._calculateTrendData(
            "messages_per_minute",
            messagesPerMin,
        );
        this._updateMetricCardWithSparkline(
            "messages-per-minute",
            "messages-trend-indicator",
            "messages",
            this._formatNumber(messagesPerMin),
            messagesPerMin,
            messagesTrend,
            timestamp,
        );

        // Active offices with trend
        const activeOffices =
            system.active_offices ||
            Object.keys(geographic).filter(
                (office) => geographic[office].messages_processed_total > 0,
            ).length;
        const officesTrend = this._calculateTrendData(
            "active_offices",
            activeOffices,
        );
        this._updateMetricCardWithSparkline(
            "active-offices",
            "offices-trend-indicator",
            "offices",
            activeOffices,
            activeOffices,
            officesTrend,
            timestamp,
        );

        // Average latency with trend
        const avgLatency = latency.avg_ms || 0;
        const latencyTrend = this._calculateTrendData(
            "avg_latency",
            avgLatency,
        );
        this._updateMetricCardWithSparkline(
            "avg-latency",
            "latency-trend-indicator",
            "latency",
            this._formatNumber(avgLatency, 1),
            avgLatency,
            latencyTrend,
            timestamp,
        );

        // Error rate with trend
        const errorRate = errors.rate_percent || 0;
        const errorTrend = this._calculateTrendData("error_rate", errorRate);
        this._updateMetricCardWithSparkline(
            "error-rate",
            "error-trend-indicator",
            "errors",
            this._formatNumber(errorRate, 2),
            errorRate,
            errorTrend,
            timestamp,
        );

        // Update system health and connection status
        this._updateSystemHealth(data);
    }

    _updateMetricCardWithSparkline(
        valueElementId,
        trendElementId,
        sparklineType,
        displayValue,
        rawValue,
        trendData,
        timestamp,
    ) {
        // Update value
        const valueElement = document.getElementById(valueElementId);
        if (valueElement) {
            valueElement.textContent = displayValue;
        }

        // Update trend indicator
        const trendElement = document.getElementById(trendElementId);
        if (trendElement && trendData) {
            const arrow = trendElement.querySelector(".trend-arrow");
            const percentage = trendElement.querySelector(".trend-percentage");

            if (arrow && percentage) {
                arrow.textContent =
                    trendData.direction === "up"
                        ? "↗"
                        : trendData.direction === "down"
                          ? "↘"
                          : "→";
                percentage.textContent = trendData.percentage;

                trendElement.className = `metric-trend-indicator trend-${trendData.direction}`;
            }
        }

        // Update sparkline
        if (this.hasSparklines && this.sparklineManager) {
            this.sparklineManager.updateSparkline(
                sparklineType,
                rawValue,
                timestamp,
            );
        }

        // Fallback: Update legacy trend indicator if sparklines are not available
        if (!this.hasSparklines) {
            this._updateLegacyTrendIndicator(valueElementId, trendData);
        }
    }

    _updateLegacyTrendIndicator(elementId, trendData) {
        // Map element IDs to their corresponding legacy trend element IDs
        const trendElementMap = {
            "messages-per-minute": "messages-trend",
            "active-offices": "offices-trend",
            "avg-latency": "latency-trend",
            "error-rate": "error-trend",
        };

        const trendElementId = trendElementMap[elementId];
        if (trendElementId && trendData) {
            const trendElement = document.getElementById(trendElementId);
            if (trendElement) {
                trendElement.textContent = trendData.percentage;
                trendElement.className = `metric-trend ${this._getTrendClass(trendData.direction)}`;
            }
        }
    }

    _updateMetricCard(elementId, value, trend = null) {
        const valueElement = document.getElementById(elementId);
        if (valueElement) {
            valueElement.textContent = value;
        }

        if (trend !== null) {
            // Map element IDs to their corresponding trend element IDs
            const trendElementMap = {
                "messages-per-minute": "messages-trend",
                "active-offices": "offices-trend",
                "avg-latency": "latency-trend",
                "error-rate": "error-trend",
            };

            const trendElementId = trendElementMap[elementId];
            if (trendElementId) {
                const trendElement = document.getElementById(trendElementId);
                if (trendElement) {
                    trendElement.textContent = trend;
                    trendElement.className = `metric-trend ${this._getTrendClass(trend)}`;
                }
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
        if (this.weatherMap && data.by_wmo) {
            this.weatherMap.updateActivityLevels(data.by_wmo);
        }
    }

    _updateOfficeStatusIndicators(data) {
        if (!data.by_wmo) return;

        // Helper function to determine activity level (matches weather map logic)
        const getActivityLevel = (activity) => {
            // Use API-provided activity level if available
            if (activity?.activity_level) {
                return activity.activity_level;
            }
            return "idle";
        };

        // Get all office elements in the sidebar
        const allOfficeElements = document.querySelectorAll(
            '.office-status[id^="status-"]',
        );
        let updatedCount = 0;

        // Update offices with activity data
        for (const officeId of Object.keys(data.by_wmo)) {
            const statusElement = document.getElementById(`status-${officeId}`);
            if (statusElement) {
                const activity = data.by_wmo[officeId];
                const activityLevel = getActivityLevel(activity);

                // Remove existing activity classes
                const oldClasses = statusElement.className;
                statusElement.className = statusElement.className.replace(
                    /\bactivity-\w+\b/g,
                    "",
                );

                // Add new activity class
                statusElement.classList.add(`activity-${activityLevel}`);

                updatedCount++;

                // Debug logging for the first few updates
                if (updatedCount <= 3) {
                    console.log(
                        `Updated office ${officeId}: ${oldClasses} -> ${statusElement.className}, activity level: ${activityLevel}`,
                    );
                }
            }
        }

        // Set any offices without activity data to idle
        for (const element of allOfficeElements) {
            const officeId = element.id.replace("status-", "");
            if (!data.by_wmo[officeId]) {
                // Remove existing activity classes
                element.className = element.className.replace(
                    /\bactivity-\w+\b/g,
                    "",
                );
                // Set to idle
                element.classList.add("activity-idle");
            }
        }

        if (updatedCount > 0) {
            console.log(`Updated ${updatedCount} office status indicators`);
        }
    }

    _updateOfficeList() {
        const officeListElement = document.getElementById("office-list");
        if (!officeListElement || !this.officeData) return;

        const offices = Object.values(this.officeData).sort((a, b) =>
            a.name.localeCompare(b.name),
        );

        officeListElement.innerHTML = offices
            .map(
                (office) => `
                <div class="office-item" data-office-id="${office.id}">
                    <div>
                        <div class="office-name">${office.name}</div>
                        <div class="office-details">${office.region} • ${office.id}</div>
                    </div>
                    <div class="office-status activity-idle" id="status-${office.id}"></div>
                </div>
            `,
            )
            .join("");

        // Add click handlers
        for (const item of officeListElement.querySelectorAll(".office-item")) {
            item.addEventListener("click", (e) => {
                const officeId = e.currentTarget.dataset.officeId;
                this._focusOnOffice(officeId);
            });
        }
    }

    _updateConnectionStatus(status) {
        const indicator = document.getElementById("ws-indicator");
        const statusText = document.getElementById("ws-status");
        const connectionStatusDot =
            document.getElementById("connection-status");
        const connectionText = document.getElementById("connection-text");

        const statusConfig = {
            connected: {
                class: "connected",
                text: "Polling",
                color: "var(--success-color)",
            },
            connecting: {
                class: "connecting",
                text: "Starting...",
                color: "var(--warning-color)",
            },
            disconnected: {
                class: "disconnected",
                text: "Stopped",
                color: "var(--error-color)",
            },
            warning: {
                class: "warning",
                text: "Retrying",
                color: "var(--warning-color)",
            },
            error: {
                class: "error",
                text: "Failed",
                color: "var(--error-color)",
            },
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

    _updateSystemHealth(data) {
        const healthDot = document.getElementById("system-health-status");
        const healthText = document.getElementById("system-health-text");

        const system = data.system || {};
        const errors = data.errors || {};
        const errorRate = errors.rate_percent || 0;

        let healthStatus = "Healthy";
        let healthClass = "";

        // Determine health status based on multiple factors
        const pipelineHealthy = system.pipeline_status === "healthy";
        const connectionActive = system.connection_status === "connected";

        if (!pipelineHealthy || !connectionActive) {
            healthStatus = "Critical";
            healthClass = "error";
        } else if (errorRate > 10) {
            healthStatus = "Critical";
            healthClass = "error";
        } else if (errorRate > 5) {
            healthStatus = "Degraded";
            healthClass = "warning";
        } else {
            healthStatus = "Healthy";
            healthClass = "";
        }

        if (healthDot) {
            healthDot.className = `status-dot ${healthClass}`;
        }

        if (healthText) {
            healthText.textContent = healthStatus;
        }
    }

    _calculateTrend(metricName, currentValue) {
        // Store previous values for trend calculation
        if (!this.previousMetrics) {
            this.previousMetrics = {};
        }

        const previousValue = this.previousMetrics[metricName];
        this.previousMetrics[metricName] = currentValue;

        if (previousValue === undefined) {
            return "--";
        }

        const difference = currentValue - previousValue;
        const percentChange =
            previousValue !== 0 ? (difference / previousValue) * 100 : 0;

        if (Math.abs(percentChange) < 1) {
            return "stable";
        }
        if (percentChange > 0) {
            return `+${Math.abs(percentChange).toFixed(1)}%`;
        }
        return `-${Math.abs(percentChange).toFixed(1)}%`;
    }

    _calculateTrendData(metricName, currentValue) {
        const previousValue = this.previousMetrics[metricName];
        this.previousMetrics[metricName] = currentValue;

        if (previousValue === undefined) {
            return { direction: "stable", percentage: "--" };
        }

        const difference = currentValue - previousValue;
        const percentChange =
            previousValue !== 0 ? (difference / previousValue) * 100 : 0;

        let direction = "stable";
        if (Math.abs(percentChange) >= 1) {
            direction = percentChange > 0 ? "up" : "down";
        }

        const formattedPercentage =
            Math.abs(percentChange) >= 1
                ? `${Math.abs(percentChange).toFixed(1)}%`
                : "--";

        return {
            direction,
            percentage: formattedPercentage,
        };
    }

    _updateLastUpdateTime() {
        const lastUpdateElement = document.getElementById("last-update");
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
        for (const item of document.querySelectorAll(".office-item")) {
            item.classList.remove("highlighted");
        }

        // Highlight selected office
        const officeElement = document.querySelector(
            `[data-office-id="${officeId}"]`,
        );
        if (officeElement) {
            officeElement.classList.add("highlighted");
            officeElement.scrollIntoView({
                behavior: "smooth",
                block: "nearest",
            });
        }
    }

    _prepareThroughputData(data) {
        const throughput = data.throughput || {};
        const timestamp = data.timestamp || Date.now() / 1000;

        return {
            timestamp: timestamp * 1000, // Convert to milliseconds
            messagesPerMinute: throughput.messages_per_minute || 0,
            totalMessages: throughput.total_messages || 0,
            messagesByType: throughput.messages_by_type || {},
        };
    }

    _prepareLatencyData(data) {
        const latency = data.latency || {};

        return {
            average: latency.avg_ms || 0,
            p95: latency.p95_ms || 0,
            p99: latency.p99_ms || 0,
            buckets: latency.histogram_buckets || [],
        };
    }

    _formatNumber(value, decimals = 0) {
        if (typeof value !== "number" || Number.isNaN(value)) {
            return "--";
        }

        if (value >= 1000000) {
            return `${(value / 1000000).toFixed(1)}M`;
        }
        if (value >= 1000) {
            return `${(value / 1000).toFixed(1)}K`;
        }
        return value.toFixed(decimals);
    }

    _getTrendClass(trendValue) {
        // Handle new trend format (direction string)
        if (typeof trendValue === "string") {
            if (trendValue === "up") return "trend-up";
            if (trendValue === "down") return "trend-down";
            return "trend-stable";
        }

        // Handle legacy trend format (numeric or string with + prefix)
        if (typeof trendValue === "number") {
            if (trendValue > 0) return "trend-up";
            if (trendValue < 0) return "trend-down";
            return "trend-stable";
        }

        // Handle string trends like "+5.2%" or "-3.1%"
        if (
            typeof trendValue === "string" &&
            trendValue !== "stable" &&
            trendValue !== "--"
        ) {
            if (trendValue.startsWith("+")) return "trend-up";
            if (trendValue.startsWith("-")) return "trend-down";
        }

        return "trend-stable";
    }

    _showError(message) {
        console.error("Dashboard error:", message);

        // Show error in UI
        const errorTemplate = document.getElementById("error-template");
        if (errorTemplate) {
            const errorElement = errorTemplate.cloneNode(true);
            errorElement.id = `error-${Date.now()}`;
            errorElement.style.display = "block";

            const errorText = errorElement.querySelector("#error-text");
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
        // Trigger immediate poll
        this.pollMetrics();
    }

    refreshMap() {
        if (this.weatherMap) {
            this.weatherMap.refresh();
        }
    }

    getOfficeMetrics(officeId) {
        return this.currentMetrics?.by_wmo?.[officeId] || null;
    }

    setupRainViewerControls() {
        const rainToggle = document.getElementById("rain-toggle");

        if (rainToggle) {
            rainToggle.addEventListener("click", () => {
                const enabled = this.weatherMap.toggleRainViewer();
                rainToggle.classList.toggle("active", enabled);
            });
        }
    }

    destroy() {
        this._stopPolling();

        if (this.sparklineManager) {
            this.sparklineManager.destroy();
        }

        if (this.weatherMap) {
            this.weatherMap.destroy();
        }

        for (const chart of Object.values(this.charts)) {
            if (chart?.destroy) {
                chart.destroy();
            }
        }
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
    }
    if (diff < 3600) {
        return `${Math.floor(diff / 60)}m ago`;
    }
    return `${Math.floor(diff / 3600)}h ago`;
}
