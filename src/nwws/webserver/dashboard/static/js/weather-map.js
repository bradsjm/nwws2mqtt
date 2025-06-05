// Weather Office Map Component for NWWS2MQTT Dashboard
// Interactive Leaflet map showing US Weather Forecast Offices with activity levels
//
// Recent Activity Highlighting:
// - Office borders are highlighted with bright colors when they have recent activity
// - "Recent" is defined as activity within the last polling interval (+ 50% buffer)
// - Border colors complement existing activity level fill colors
// - Highlighted borders are thicker (minimum 3px) for better visibility

class WeatherOfficeMap {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.map = null;
        this.officeLayers = null;
        this.activityData = {};
        this.selectedOffice = null;

        // Map configuration
        this.config = {
            center: [37.7749, -95.7129], // Centered on the continental US
            zoom: 4,
            minZoom: 4,
            maxZoom: 10,
            maxBounds: [
                [16, -170.0], // Southwest bound
                [80.0, -47.0], // Northeast bound
            ],
            ...options,
        };

        // RainViewer integration
        this.rainViewer = {
            layer: null,
            enabled: false,
            opacity: 0.6,
            latestFrameTime: null,
            updateTimer: null,
            minUpdateDelay: options.rainViewerMinDelay || 30000, // 30 seconds default
        };

        // Activity level styling
        this.activityStyles = {
            idle: {
                fillColor: "#e5e7eb",
                color: "#9ca3af",
                weight: 1,
                fillOpacity: 0.1,
                opacity: 1,
            },
            low: {
                fillColor: "#10b981",
                color: "#059669",
                weight: 2,
                fillOpacity: 0.1,
                opacity: 1,
            },
            medium: {
                fillColor: "#f59e0b",
                color: "#d97706",
                weight: 2,
                fillOpacity: 0.1,
                opacity: 1,
            },
            high: {
                fillColor: "#ef4444",
                color: "#dc2626",
                weight: 3,
                fillOpacity: 0.1,
                opacity: 1,
            },
            error: {
                fillColor: "#f87171",
                color: "#b91c1c",
                weight: 3,
                fillOpacity: 0.1,
                opacity: 1,
            },
        };

        // Default style for offices
        this.defaultStyle = {
            fillColor: "#e5e7eb",
            color: "#6b7280",
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8,
        };

        // Highlighted style for selected office
        this.highlightStyle = {
            weight: 3,
            color: "#3b82f6",
            dashArray: "",
            fillOpacity: 0.8,
        };

        // Recent activity border styles - bright colors for highlighting active offices
        this.recentActivityBorderStyles = {
            low: "#ea580c", // bright orange
            medium: "#ff8c00", // bright orange
            high: "#dc2626", // bright red
            error: "#991b1b", // darker red
        };

        // Polling interval for recent activity detection (matches dashboard config)
        // Used to determine what constitutes "recent" activity
        this.pollingInterval = options.pollingInterval || 5000; // 5 seconds default

        // Debug flag for enhanced recent activity logging
        this.debugRecentActivity = options.debugRecentActivity || false;
    }

    async initialize() {
        try {
            // Initialize Leaflet map
            this.map = L.map(this.containerId, {
                center: this.config.center,
                zoom: this.config.zoom,
                minZoom: this.config.minZoom,
                maxZoom: this.config.maxZoom,
                maxBounds: this.config.maxBounds,
                zoomControl: true,
                attributionControl: true,
            });

            // Add base map layer
            this._addBaseLayers();

            // Add map controls
            this._addMapControls();

            // Add custom legend
            this._addActivityLegend();

            // Initialize RainViewer
            this.initializeRainViewer();
        } catch (error) {
            console.error("Failed to initialize weather map:", error);
            throw error;
        }
    }

    _addBaseLayers() {
        // OpenStreetMap base layer
        const osmLayer = L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                attribution: "© OpenStreetMap contributors",
                maxZoom: 18,
            },
        );

        // CartoDB Positron (light theme)
        const cartodbLayer = L.tileLayer(
            "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
            {
                attribution: "© OpenStreetMap contributors © CARTO",
                maxZoom: 19,
            },
        );

        // ESRI World Imagery
        const esriLayer = L.tileLayer(
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            {
                attribution:
                    "© Esri, DigitalGlobe, GeoEye, Earthstar Geographics, CNES/Airbus DS, USDA, USGS, AeroGRID, IGN, and the GIS User Community",
                maxZoom: 18,
            },
        );

        // Add default layer
        cartodbLayer.addTo(this.map);

        // Layer control
        const baseLayers = {
            "Light Theme": cartodbLayer,
            OpenStreetMap: osmLayer,
            Satellite: esriLayer,
        };

        L.control.layers(baseLayers).addTo(this.map);
    }

    _addMapControls() {
        // Custom zoom control
        L.control
            .zoom({
                position: "topright",
            })
            .addTo(this.map);

        // Scale control
        L.control
            .scale({
                position: "bottomleft",
                imperial: true,
                metric: true,
            })
            .addTo(this.map);
    }

    _addActivityLegend() {
        const legend = L.control({ position: "bottomright" });

        legend.onAdd = () => {
            const div = L.DomUtil.create("div", "activity-legend");
            div.innerHTML = `
                <div class="legend-title">Office Activity</div>
                <div class="legend-item">
                    <div class="legend-color legend-color-high"></div>
                    <span>High (100+ msgs)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color legend-color-medium"></div>
                    <span>Medium (20-100 msg)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color legend-color-low"></div>
                    <span>Low (1-20 msg)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color legend-color-idle"></div>
                    <span>Idle (last hour)</span>
                </div>
            `;

            // Add CSS styles with higher specificity
            div.style.cssText = `
                background: white !important;
                border-radius: 8px !important;
                padding: 12px !important;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1) !important;
                font-size: 12px !important;
                line-height: 1.4 !important;
                max-width: 200px !important;
                border: 1px solid #e5e7eb !important;
            `;

            const legendTitle = div.querySelector(".legend-title");
            if (legendTitle) {
                legendTitle.style.cssText = `
                    font-weight: 600 !important;
                    margin-bottom: 8px !important;
                    color: #374151 !important;
                `;
            }

            for (const item of div.querySelectorAll(".legend-item")) {
                item.style.cssText = `
                    display: flex !important;
                    align-items: center !important;
                    margin-bottom: 4px !important;
                `;
            }

            // Set individual colors with !important to override CSS
            const colors = div.querySelectorAll(".legend-color");
            if (colors[0]) {
                // High
                colors[0].style.cssText = `
                    width: 16px !important;
                    height: 16px !important;
                    border-radius: 3px !important;
                    margin-right: 8px !important;
                    border: 1px solid #d1d5db !important;
                    background-color: #ef4444 !important;
                    flex-shrink: 0 !important;
                `;
            }
            if (colors[1]) {
                // Medium
                colors[1].style.cssText = `
                    width: 16px !important;
                    height: 16px !important;
                    border-radius: 3px !important;
                    margin-right: 8px !important;
                    border: 1px solid #d1d5db !important;
                    background-color: #f59e0b !important;
                    flex-shrink: 0 !important;
                `;
            }
            if (colors[2]) {
                // Low
                colors[2].style.cssText = `
                    width: 16px !important;
                    height: 16px !important;
                    border-radius: 3px !important;
                    margin-right: 8px !important;
                    border: 1px solid #d1d5db !important;
                    background-color: #10b981 !important;
                    flex-shrink: 0 !important;
                `;
            }
            if (colors[3]) {
                // Idle
                colors[3].style.cssText = `
                    width: 16px !important;
                    height: 16px !important;
                    border-radius: 3px !important;
                    margin-right: 8px !important;
                    border: 1px solid #d1d5db !important;
                    background-color: #e5e7eb !important;
                    flex-shrink: 0 !important;
                `;
            }

            return div;
        };

        legend.addTo(this.map);

        // Add Leaflet-specific CSS overrides to prevent conflicts
        const style = document.createElement("style");
        style.textContent = `
            .leaflet-control.activity-legend {
                background: white !important;
                border: 1px solid #e5e7eb !important;
                border-radius: 8px !important;
                padding: 12px !important;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1) !important;
                font-size: 12px !important;
                line-height: 1.4 !important;
                max-width: 200px !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            }

            .leaflet-control.activity-legend .legend-title {
                font-weight: 600 !important;
                margin-bottom: 8px !important;
                color: #374151 !important;
            }

            .leaflet-control.activity-legend .legend-item {
                display: flex !important;
                align-items: center !important;
                margin-bottom: 4px !important;
            }

            .leaflet-control.activity-legend .legend-color {
                width: 16px !important;
                height: 16px !important;
                border-radius: 3px !important;
                margin-right: 8px !important;
                border: 1px solid #d1d5db !important;
                flex-shrink: 0 !important;
                display: block !important;
            }

            .leaflet-control.activity-legend .legend-color-high {
                background-color: #ef4444 !important;
            }

            .leaflet-control.activity-legend .legend-color-medium {
                background-color: #f59e0b !important;
            }

            .leaflet-control.activity-legend .legend-color-low {
                background-color: #10b981 !important;
            }

            .leaflet-control.activity-legend .legend-color-idle {
                background-color: #e5e7eb !important;
            }
        `;
        document.head.appendChild(style);
    }

    async loadOfficeBoundaries(geoData) {
        try {
            if (!geoData || !geoData.features) {
                throw new Error("Invalid GeoJSON data provided");
            }

            // Remove existing layers
            if (this.officeLayers) {
                this.map.removeLayer(this.officeLayers);
            }

            // Create new GeoJSON layer
            this.officeLayers = L.geoJSON(geoData, {
                style: this.defaultStyle,
                onEachFeature: (feature, layer) => {
                    this._bindOfficeFeature(feature, layer);
                },
            });

            // Add layer to map
            this.officeLayers.addTo(this.map);

            // Fit map to boundaries
            if (geoData.features.length > 0) {
                this.map.fitBounds(this.officeLayers.getBounds(), {
                    padding: [20, 20],
                });
            }
        } catch (error) {
            console.error("Failed to load office boundaries:", error);
            throw error;
        }
    }

    _bindOfficeFeature(feature, layer) {
        const properties = feature.properties;
        const officeId = properties.cwa || feature.id;

        // Create popup content
        const popupContent = this._createOfficePopup(properties, officeId);
        layer.bindPopup(popupContent);

        // Add event handlers
        layer.on({
            mouseover: (e) => this._highlightFeature(e),
            mouseout: (e) => this._resetHighlight(e),
            click: (e) => this._selectOffice(e, officeId),
        });

        // Store reference for activity updates
        layer.officeId = officeId;
    }

    _createOfficePopup(properties, officeId) {
        const activity = this._getActivityData(officeId);
        const activityLevel = this._getActivityLevel(activity);
        const messages =
            activity.messages_processed_total ?? activity.messages_total ?? 0;
        const latency =
            activity.avg_processing_latency_ms ??
            activity.average_latency_ms ??
            0;
        const errors = activity.errors_total ?? activity.error_count ?? 0;

        // Check for recent activity and format last activity time
        const hasRecentActivity = this._hasRecentActivity(activity);
        const lastActivityText = activity.last_activity
            ? new Date(activity.last_activity * 1000).toLocaleTimeString()
            : "Never";
        const recentActivityIndicator = hasRecentActivity
            ? '<span style="color: #22c55e; font-weight: bold;">● ACTIVE</span>'
            : "";

        return `
            <div class="office-popup">
                <h3>${properties.name || officeId} ${recentActivityIndicator}</h3>
                <div class="popup-content">
                    <div class="popup-row">
                        <span class="popup-label">Office ID:</span>
                        <span class="popup-value">${officeId}</span>
                    </div>
                    <div class="popup-row">
                        <span class="popup-label">Region:</span>
                        <span class="popup-value">${properties.region || "Unknown"}</span>
                    </div>
                    <div class="popup-row">
                        <span class="popup-label">Activity Level:</span>
                        <span class="popup-value activity-${activityLevel}">${activityLevel.toUpperCase()}</span>
                    </div>
                    <div class="popup-row">
                        <span class="popup-label">Last Activity:</span>
                        <span class="popup-value">${lastActivityText}</span>
                    </div>
                    <div class="popup-row">
                        <span class="popup-label">Messages:</span>
                        <span class="popup-value">${messages}</span>
                    </div>
                    <div class="popup-row">
                        <span class="popup-label">Avg Latency:</span>
                        <span class="popup-value">${latency.toFixed(1)}ms</span>
                    </div>
                    <div class="popup-row">
                        <span class="popup-label">Errors:</span>
                        <span class="popup-value">${errors}</span>
                    </div>
                </div>
            </div>
        `;
    }

    _highlightFeature(e) {
        const layer = e.target;

        if (layer !== this.selectedOffice) {
            layer.setStyle({
                weight: 2,
                color: "#3b82f6",
                dashArray: "",
                fillOpacity: 0.8,
            });

            layer.bringToFront();
        }
    }

    _resetHighlight(e) {
        const layer = e.target;

        if (layer !== this.selectedOffice) {
            const officeId = layer.officeId;
            const activity = this._getActivityData(officeId);
            const activityLevel = this._getActivityLevel(activity);
            const baseStyle =
                this.activityStyles[activityLevel] || this.defaultStyle;

            // Check if office has recent activity and apply border highlighting
            const hasRecentActivity = this._hasRecentActivity(activity);
            const style = { ...baseStyle };

            if (hasRecentActivity) {
                style.color =
                    this.recentActivityBorderStyles[activityLevel] ||
                    this.recentActivityBorderStyles.idle;
                style.weight = Math.max(baseStyle.weight, 5);
                style.opacity = 1;
            }

            layer.setStyle(style);
        }
    }

    _selectOffice(e, officeId) {
        // Reset previous selection
        if (this.selectedOffice) {
            this._resetOfficeStyle(this.selectedOffice);
        }

        // Set new selection
        this.selectedOffice = e.target;
        this.selectedOffice.setStyle(this.highlightStyle);
        this.selectedOffice.bringToFront();

        // Trigger office selection event
        this._dispatchOfficeSelected(officeId);
    }

    _resetOfficeStyle(layer) {
        const officeId = layer.officeId;
        const activity = this._getActivityData(officeId);
        const activityLevel = this._getActivityLevel(activity);
        const baseStyle =
            this.activityStyles[activityLevel] || this.defaultStyle;

        // Check if office has recent activity and apply border highlighting
        const hasRecentActivity = this._hasRecentActivity(activity);
        const style = { ...baseStyle };

        if (hasRecentActivity) {
            style.color =
                this.recentActivityBorderStyles[activityLevel] ||
                this.recentActivityBorderStyles.idle;
            style.weight = Math.max(baseStyle.weight, 3);
            style.opacity = 1;
        }

        layer.setStyle(style);
    }

    updateActivityLevels(activityData) {
        try {
            this.activityData = activityData || {};

            // Validate activity data structure
            const validationIssues = this.validateActivityData(
                this.activityData,
            );
            if (validationIssues.length > 0) {
                console.warn(
                    "Activity data validation failed, but continuing with update",
                );
            }

            if (!this.officeLayers) {
                console.warn("No office layers available for activity update");
                return;
            }

            // Track existing office IDs to detect new ones
            const existingOffices = new Set();
            let hasNewOffices = false;
            let updatedCount = 0;

            // Update each existing office layer with new activity data
            this.officeLayers.eachLayer((layer) => {
                try {
                    const officeId = layer.officeId;
                    if (!officeId) {
                        console.warn("Layer missing officeId, skipping");
                        return;
                    }

                    existingOffices.add(officeId);

                    const activity = this._getActivityData(officeId);
                    const activityLevel = this._getActivityLevel(activity);

                    // Get base style based on activity level
                    const baseStyle =
                        this.activityStyles[activityLevel] || this.defaultStyle;

                    // Check if office has recent activity and apply border highlighting
                    const hasRecentActivity = this._hasRecentActivity(activity);
                    const style = { ...baseStyle };

                    if (hasRecentActivity) {
                        style.color =
                            this.recentActivityBorderStyles[activityLevel] ||
                            this.recentActivityBorderStyles.idle;
                        style.weight = Math.max(baseStyle.weight, 3); // Ensure minimum thickness for visibility
                        style.opacity = 1; // Ensure full opacity for recent activity borders
                    }

                    layer.setStyle(style);

                    // Update popup layer content
                    const newContent = this._createOfficePopup(
                        layer.feature.properties,
                        officeId,
                    );
                    layer.setPopupContent(newContent);

                    // Force redraw to ensure colors are applied
                    if (layer.redraw) {
                        layer.redraw();
                    }

                    updatedCount++;
                } catch (layerError) {
                    console.error(
                        `Error updating layer for office ${layer.officeId}:`,
                        layerError,
                    );
                }
            });

            console.log(`Updated ${updatedCount} office layers`);

            // Check for new offices in activity data that aren't on the map yet
            for (const officeId in this.activityData) {
                if (!existingOffices.has(officeId)) {
                    console.log(
                        `New office detected with activity: ${officeId}`,
                    );
                    hasNewOffices = true;
                }
            }

            // If new offices are detected, trigger a reload event
            // This allows the parent component to reload office boundaries
            if (hasNewOffices) {
                console.log("Triggering new offices detected event");
                this._dispatchNewOfficesDetected();
            }
        } catch (error) {
            console.error("Error in updateActivityLevels:", error);
            // Continue execution to prevent breaking the map
        }
    }

    _getActivityData(officeId) {
        // Try direct lookup first
        if (this.activityData[officeId]) {
            return this.activityData[officeId];
        }
        console.log("No activity data found for office: ", officeId);

        return {};
    }

    /**
     * Debug method to log activity data for troubleshooting
     */
    debugActivityData() {
        console.group("Weather Office Map - Activity Data Debug");
        console.log(
            "Total offices with activity data:",
            Object.keys(this.activityData).length,
        );
        console.log("Polling interval:", this.pollingInterval);
        console.log("Current time (unix):", Math.floor(Date.now() / 1000));
        console.log("Debug recent activity enabled:", this.debugRecentActivity);

        const recentOffices = [];
        const activeOffices = [];

        for (const [officeId, activity] of Object.entries(this.activityData)) {
            console.group(`Office: ${officeId}`);
            console.log("Activity level:", activity.activity_level);
            console.log("Last activity (unix):", activity.last_activity);
            console.log(
                "Last activity (readable):",
                activity.last_activity
                    ? new Date(activity.last_activity * 1000).toISOString()
                    : "Never",
            );
            console.log(
                "Messages total:",
                activity.messages_processed_total ??
                    activity.messages_total ??
                    0,
            );

            const hasRecentActivity = this._hasRecentActivity(activity);
            console.log("Has recent activity:", hasRecentActivity);

            if (hasRecentActivity) {
                recentOffices.push(officeId);
            }

            if (activity.activity_level && activity.activity_level !== "idle") {
                activeOffices.push(officeId);
            }

            console.groupEnd();
        }

        console.log("Offices with recent activity:", recentOffices);
        console.log("Offices with non-idle activity level:", activeOffices);
        console.groupEnd();
    }

    /**
     * Validate activity data structure and log any inconsistencies
     */
    validateActivityData(activityData) {
        const issues = [];

        if (!activityData || typeof activityData !== "object") {
            issues.push("Activity data is not a valid object");
            return issues;
        }

        for (const [officeId, activity] of Object.entries(activityData)) {
            if (!activity || typeof activity !== "object") {
                issues.push(
                    `Office ${officeId}: activity data is not an object`,
                );
                continue;
            }

            // Check for expected fields
            if (
                activity.last_activity !== undefined &&
                typeof activity.last_activity !== "number"
            ) {
                issues.push(
                    `Office ${officeId}: last_activity should be a number (unix timestamp)`,
                );
            }

            if (
                activity.activity_level !== undefined &&
                typeof activity.activity_level !== "string"
            ) {
                issues.push(
                    `Office ${officeId}: activity_level should be a string`,
                );
            }

            // Check for suspicious timestamps (future dates or very old dates)
            if (activity.last_activity) {
                const now = Date.now() / 1000;
                const dayInSeconds = 24 * 60 * 60;

                if (activity.last_activity > now + 60) {
                    issues.push(
                        `Office ${officeId}: last_activity is in the future`,
                    );
                }

                if (activity.last_activity < now - 30 * dayInSeconds) {
                    issues.push(
                        `Office ${officeId}: last_activity is more than 30 days old`,
                    );
                }
            }
        }

        if (issues.length > 0) {
            console.warn("Activity data validation issues:", issues);
        }

        return issues;
    }

    _getActivityLevel(activity) {
        // Use API-provided activity level if available
        if (activity.activity_level) {
            return activity.activity_level;
        }

        return "idle";
    }

    _hasRecentActivity(activity) {
        // Check if office has had activity within the polling interval
        // This is used to highlight borders of actively sending offices
        if (!activity || !activity.last_activity) {
            return false;
        }

        try {
            const now = Date.now() / 1000; // Convert to seconds
            const lastActivity = Number(activity.last_activity);

            // Validate timestamp is reasonable
            if (Number.isNaN(lastActivity) || lastActivity <= 0) {
                console.warn(
                    "Invalid last_activity timestamp:",
                    activity.last_activity,
                );
                return false;
            }

            const timeSinceLastActivity = now - lastActivity;

            // Consider activity "recent" if it's within the polling interval
            // Add a small buffer (1.5x) to account for timing variations and network delays
            const recentActivityThreshold = (this.pollingInterval / 1000) * 1.5;

            const isRecent = timeSinceLastActivity <= recentActivityThreshold;

            // Only log for debugging when activity is recent or when debugging is explicitly enabled
            if (isRecent || this.debugRecentActivity) {
                console.log("Recent activity check:", {
                    last_activity: lastActivity,
                    last_activity_date: new Date(
                        lastActivity * 1000,
                    ).toISOString(),
                    now: now,
                    now_date: new Date(now * 1000).toISOString(),
                    timeSinceLastActivity: timeSinceLastActivity,
                    recentActivityThreshold: recentActivityThreshold,
                    pollingInterval: this.pollingInterval,
                    isRecent: isRecent,
                });
            }

            return isRecent;
        } catch (error) {
            console.error("Error checking recent activity:", error);
            return false;
        }
    }

    focusOnOffice(officeId) {
        if (!this.officeLayers) return;

        let targetLayer = null;

        // Find the office layer
        this.officeLayers.eachLayer((layer) => {
            if (layer.officeId === officeId) {
                targetLayer = layer;
                return;
            }
        });

        if (targetLayer) {
            // Zoom to office bounds
            const bounds = targetLayer.getBounds();
            this.map.fitBounds(bounds, {
                padding: [50, 50],
                maxZoom: 7,
            });

            // Select the office
            this._selectOffice({ target: targetLayer }, officeId);

            // Open popup
            targetLayer.openPopup();
        }
    }

    _dispatchOfficeSelected(officeId) {
        const event = new CustomEvent("officeSelected", {
            detail: { officeId },
        });
        document.dispatchEvent(event);
    }

    _dispatchNewOfficesDetected() {
        const event = new CustomEvent("newOfficesDetected", {
            detail: {
                activityData: this.activityData,
                timestamp: Date.now(),
            },
        });
        console.log("Dispatching newOfficesDetected event");
        document.dispatchEvent(event);
    }

    refresh() {
        if (this.map) {
            // Refresh map tiles
            this.map.eachLayer((layer) => {
                if (layer.redraw) {
                    layer.redraw();
                }
            });

            // Invalidate size to handle container changes
            setTimeout(() => {
                this.map.invalidateSize();
            }, 100);
        }
    }

    resize() {
        if (this.map) {
            this.map.invalidateSize();
        }
    }

    destroy() {
        // Clean up RainViewer
        if (this.rainViewer.layer && this.map) {
            this.map.removeLayer(this.rainViewer.layer);
        }

        // Clear the update timer
        if (this.rainViewer.updateTimer) {
            clearTimeout(this.rainViewer.updateTimer);
        }

        this.rainViewer = {
            layer: null,
            enabled: false,
            opacity: 0.6,
            latestFrameTime: null,
            updateTimer: null,
            minUpdateDelay: 30000, // Reset to default
        };

        if (this.map) {
            this.map.remove();
            this.map = null;
        }

        this.officeLayers = null;
        this.selectedOffice = null;
        this.activityData = {};
    }

    // Utility methods
    getSelectedOffice() {
        return this.selectedOffice ? this.selectedOffice.officeId : null;
    }

    clearSelection() {
        if (this.selectedOffice) {
            this._resetOfficeStyle(this.selectedOffice);
            this.selectedOffice = null;
        }
    }

    getOfficeLayer(officeId) {
        if (!this.officeLayers) return null;

        let targetLayer = null;
        this.officeLayers.eachLayer((layer) => {
            if (layer.officeId === officeId) {
                targetLayer = layer;
            }
        });

        return targetLayer;
    }

    setActivityFilter(minLevel = "idle") {
        if (!this.officeLayers) return;

        const levelOrder = ["idle", "low", "medium", "high"];
        const minIndex = levelOrder.indexOf(minLevel);

        this.officeLayers.eachLayer((layer) => {
            const officeId = layer.officeId;
            const activity = this._getActivityData(officeId);
            const activityLevel = this._getActivityLevel(activity);
            const levelIndex = levelOrder.indexOf(activityLevel);

            if (levelIndex >= minIndex) {
                layer.setStyle({
                    ...layer.options.style,
                    opacity: 1,
                    fillOpacity: 0.7,
                });
            } else {
                layer.setStyle({
                    ...layer.options.style,
                    opacity: 0.3,
                    fillOpacity: 0.1,
                });
            }
        });
    }

    resetActivityFilter() {
        this.updateActivityLevels(this.activityData);
    }

    // RainViewer Integration Methods
    async initializeRainViewer() {
        try {
            const response = await fetch(
                "https://api.rainviewer.com/public/weather-maps.json",
            );
            const data = await response.json();

            if (data?.radar?.past && data.radar.past.length > 0) {
                // Get the most recent radar frame
                const latestFrame = data.radar.past[data.radar.past.length - 1];
                this.rainViewer.latestFrameTime = latestFrame.time;
                this._createRainViewerLayer(latestFrame.time);
                this._scheduleRainViewerUpdate();
            }
        } catch (error) {
            console.warn("Failed to initialize RainViewer:", error);
        }
    }

    _createRainViewerLayer(timestamp) {
        if (!timestamp || !this.map) return;

        const tileUrl = `https://tilecache.rainviewer.com/v2/radar/${timestamp}/256/{z}/{x}/{y}/2/1_1.png`;

        if (this.rainViewer.layer) {
            this.map.removeLayer(this.rainViewer.layer);
        }

        this.rainViewer.layer = L.tileLayer(tileUrl, {
            opacity: this.rainViewer.opacity,
            attribution:
                'Weather data © <a href="https://rainviewer.com" target="_blank">RainViewer</a>',
            zIndex: 200,
        });

        if (this.rainViewer.enabled) {
            this.rainViewer.layer.addTo(this.map);
        }
    }

    toggleRainViewer() {
        this.rainViewer.enabled = !this.rainViewer.enabled;

        if (this.rainViewer.enabled && this.rainViewer.layer) {
            this.rainViewer.layer.addTo(this.map);
        } else if (
            this.rainViewer.layer &&
            this.map.hasLayer(this.rainViewer.layer)
        ) {
            this.map.removeLayer(this.rainViewer.layer);
        }

        return this.rainViewer.enabled;
    }

    _scheduleRainViewerUpdate() {
        // Clear any existing timer
        if (this.rainViewer.updateTimer) {
            clearTimeout(this.rainViewer.updateTimer);
        }

        if (!this.rainViewer.latestFrameTime) {
            return;
        }

        // Calculate time until 10 minutes after the latest frame
        const latestFrameDate = new Date(
            this.rainViewer.latestFrameTime * 1000,
        );
        const nextUpdateTime = new Date(
            latestFrameDate.getTime() + 10 * 60 * 1000,
        );
        const now = new Date();
        const timeUntilUpdate = nextUpdateTime.getTime() - now.getTime();

        // Ensure minimum delay to prevent infinite loops
        const delay = Math.max(timeUntilUpdate, this.rainViewer.minUpdateDelay);

        this.rainViewer.updateTimer = setTimeout(async () => {
            await this._updateRainViewerFrame();
        }, delay);
    }

    async _updateRainViewerFrame() {
        try {
            const response = await fetch(
                "https://api.rainviewer.com/public/weather-maps.json",
            );
            const data = await response.json();

            if (data?.radar?.past && data.radar.past.length > 0) {
                const latestFrame = data.radar.past[data.radar.past.length - 1];

                // Only update if we have a newer frame
                if (latestFrame.time > this.rainViewer.latestFrameTime) {
                    this.rainViewer.latestFrameTime = latestFrame.time;
                    this._createRainViewerLayer(latestFrame.time);
                    console.log(
                        "RainViewer frame updated:",
                        new Date(latestFrame.time * 1000),
                    );
                }

                // Schedule the next update
                this._scheduleRainViewerUpdate();
            }
        } catch (error) {
            console.warn("Failed to update RainViewer frame:", error);
            // Retry in 5 minutes on error
            if (this.rainViewer.updateTimer) {
                clearTimeout(this.rainViewer.updateTimer);
            }
            this.rainViewer.updateTimer = setTimeout(
                async () => {
                    await this._updateRainViewerFrame();
                },
                5 * 60 * 1000,
            );
        }
    }

    async refreshRainViewer() {
        // Manual refresh method for rain viewer data
        try {
            const response = await fetch(
                "https://api.rainviewer.com/public/weather-maps.json",
            );
            const data = await response.json();

            if (data?.radar?.past && data.radar.past.length > 0) {
                const latestFrame = data.radar.past[data.radar.past.length - 1];

                // Always update regardless of timestamp for manual refresh
                this.rainViewer.latestFrameTime = latestFrame.time;
                this._createRainViewerLayer(latestFrame.time);
                this._scheduleRainViewerUpdate();

                console.log(
                    "RainViewer manually refreshed:",
                    new Date(latestFrame.time * 1000),
                );

                return true;
            }
        } catch (error) {
            console.warn("Failed to refresh RainViewer:", error);
            return false;
        }
    }

    /**
     * Utility methods for debugging and manual control
     */

    // Toggle debug mode for recent activity logging
    setDebugMode(enabled = true) {
        this.debugRecentActivity = enabled;
        console.log(
            `Debug mode for recent activity: ${enabled ? "enabled" : "disabled"}`,
        );
    }

    // Get summary of current map state
    getMapSummary() {
        const summary = {
            totalOffices: this.officeLayers
                ? Object.keys(this.activityData).length
                : 0,
            officesOnMap: 0,
            officesWithRecentActivity: 0,
            officesByActivityLevel: {
                idle: 0,
                low: 0,
                medium: 0,
                high: 0,
                error: 0,
            },
            selectedOffice: this.selectedOffice?.officeId || null,
            rainViewerEnabled: this.rainViewer.enabled,
            pollingInterval: this.pollingInterval,
        };

        if (this.officeLayers) {
            this.officeLayers.eachLayer((layer) => {
                summary.officesOnMap++;
                const activity = this._getActivityData(layer.officeId);
                const level = this._getActivityLevel(activity);
                summary.officesByActivityLevel[level]++;

                if (this._hasRecentActivity(activity)) {
                    summary.officesWithRecentActivity++;
                }
            });
        }

        return summary;
    }

    // Force update of a specific office
    forceUpdateOffice(officeId) {
        if (!this.officeLayers) {
            console.warn("No office layers available");
            return false;
        }

        let found = false;
        this.officeLayers.eachLayer((layer) => {
            if (layer.officeId === officeId) {
                found = true;
                const activity = this._getActivityData(officeId);
                const activityLevel = this._getActivityLevel(activity);
                const baseStyle =
                    this.activityStyles[activityLevel] || this.defaultStyle;
                const hasRecentActivity = this._hasRecentActivity(activity);
                const style = { ...baseStyle };

                if (hasRecentActivity) {
                    style.color =
                        this.recentActivityBorderStyles[activityLevel] ||
                        this.recentActivityBorderStyles.idle;
                    style.weight = Math.max(baseStyle.weight, 3);
                    style.opacity = 1;
                }

                layer.setStyle(style);
                layer.setPopupContent(
                    this._createOfficePopup(layer.feature.properties, officeId),
                );

                console.log(`Forced update for office: ${officeId}`);
            }
        });

        if (!found) {
            console.warn(`Office ${officeId} not found on map`);
        }

        return found;
    }

    // Get detailed info about a specific office
    getOfficeInfo(officeId) {
        const activity = this._getActivityData(officeId);
        const layer = this.getOfficeLayer(officeId);

        return {
            officeId: officeId,
            onMap: !!layer,
            activity: activity,
            activityLevel: this._getActivityLevel(activity),
            hasRecentActivity: this._hasRecentActivity(activity),
            isSelected: this.selectedOffice?.officeId === officeId,
            properties: layer?.feature?.properties || null,
        };
    }

    // Manual trigger for new offices detection
    checkForNewOffices() {
        if (!this.officeLayers) {
            console.warn("No office layers available");
            return [];
        }

        const existingOffices = new Set();
        this.officeLayers.eachLayer((layer) => {
            existingOffices.add(layer.officeId);
        });

        const newOffices = [];
        for (const officeId in this.activityData) {
            if (!existingOffices.has(officeId)) {
                newOffices.push(officeId);
            }
        }

        if (newOffices.length > 0) {
            console.log("New offices detected:", newOffices);
            this._dispatchNewOfficesDetected();
        } else {
            console.log("No new offices detected");
        }

        return newOffices;
    }
}

// Add custom CSS for popup styling
const mapStyles = `
    .office-popup {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        min-width: 200px;
    }

    .office-popup h3 {
        margin: 0 0 10px 0;
        color: #1f2937;
        font-size: 14px;
        font-weight: 600;
        border-bottom: 1px solid #e5e7eb;
        padding-bottom: 5px;
    }

    .popup-content {
        font-size: 12px;
    }

    .popup-row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 4px;
        align-items: center;
    }

    .popup-label {
        color: #6b7280;
        font-weight: 500;
    }

    .popup-value {
        color: #151e32;
        font-weight: 600;
    }

    .popup-value.activity-high { color: #dc2626; }
    .popup-value.activity-medium { color: #d97706; }
    .popup-value.activity-low { color: #059669; }
    .popup-value.activity-idle { color: #6b7280; }

    .leaflet-popup-content-wrapper {
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    .leaflet-popup-tip {
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
`;

// Inject styles
if (typeof document !== "undefined") {
    const styleSheet = document.createElement("style");
    styleSheet.textContent = mapStyles;
    document.head.appendChild(styleSheet);
}
