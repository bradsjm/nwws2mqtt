// Weather Office Map Component for NWWS2MQTT Dashboard
// Interactive Leaflet map showing US Weather Forecast Offices with activity levels

class WeatherOfficeMap {
    constructor(containerId) {
        this.containerId = containerId;
        this.map = null;
        this.officeLayers = null;
        this.activityData = {};
        this.selectedOffice = null;

        // Map configuration
        this.config = {
            center: [39.8283, -98.5795], // Geographic center of US
            zoom: 4,
            minZoom: 3,
            maxZoom: 10,
            maxBounds: [
                [15.0, -180.0], // Southwest bound
                [72.0, -60.0], // Northeast bound
            ],
        };

        // RainViewer integration
        this.rainViewer = {
            layer: null,
            enabled: false,
            opacity: 0.6,
        };

        // Activity level styling
        this.activityStyles = {
            idle: {
                fillColor: "#e5e7eb",
                color: "#9ca3af",
                weight: 1,
                fillOpacity: 0.6,
            },
            low: {
                fillColor: "#10b981",
                color: "#059669",
                weight: 2,
                fillOpacity: 0.7,
            },
            medium: {
                fillColor: "#f59e0b",
                color: "#d97706",
                weight: 2,
                fillOpacity: 0.7,
            },
            high: {
                fillColor: "#ef4444",
                color: "#dc2626",
                weight: 2,
                fillOpacity: 0.8,
            },
        };

        // Default style for offices
        this.defaultStyle = {
            fillColor: "#e5e7eb",
            color: "#6b7280",
            weight: 1,
            opacity: 1,
            fillOpacity: 0.6,
        };

        // Highlighted style for selected office
        this.highlightStyle = {
            weight: 3,
            color: "#3b82f6",
            dashArray: "",
            fillOpacity: 0.8,
        };
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

            // Initialize RainViewer
            this.initializeRainViewer();

            console.log("Weather office map initialized successfully");
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

        // Add custom legend
        this._addActivityLegend();
    }

    _addActivityLegend() {
        const legend = L.control({ position: "bottomright" });

        legend.onAdd = () => {
            const div = L.DomUtil.create("div", "activity-legend");
            div.innerHTML = `
                <div class="legend-title">Office Activity</div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #ef4444"></div>
                    <span>High (100+ msg/min)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #f59e0b"></div>
                    <span>Medium (20-100 msg/min)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #10b981"></div>
                    <span>Low (1-20 msg/min)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #e5e7eb"></div>
                    <span>Idle (0 msg/min)</span>
                </div>
            `;

            // Add CSS styles
            div.style.cssText = `
                background: white;
                border-radius: 8px;
                padding: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                font-size: 12px;
                line-height: 1.4;
                max-width: 200px;
            `;

            const legendTitle = div.querySelector(".legend-title");
            if (legendTitle) {
                legendTitle.style.cssText = `
                    font-weight: 600;
                    margin-bottom: 8px;
                    color: #374151;
                `;
            }

            for (const item of div.querySelectorAll(".legend-item")) {
                item.style.cssText = `
                    display: flex;
                    align-items: center;
                    margin-bottom: 4px;
                `;
            }

            for (const color of div.querySelectorAll(".legend-color")) {
                color.style.cssText = `
                    width: 12px;
                    height: 12px;
                    border-radius: 2px;
                    margin-right: 8px;
                    border: 1px solid #d1d5db;
                `;
            }

            return div;
        };

        legend.addTo(this.map);
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

            console.log(
                `Loaded ${geoData.features.length} weather office boundaries`,
            );
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
        const activity = this.activityData[officeId] || {};
        const activityLevel = this._getActivityLevel(activity);

        return `
            <div class="office-popup">
                <h3>${properties.name || officeId}</h3>
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
                        <span class="popup-label">Messages:</span>
                        <span class="popup-value">${activity.messages_processed_total ?? 0}</span>
                    </div>
                    <div class="popup-row">
                        <span class="popup-label">Avg Latency:</span>
                        <span class="popup-value">${(activity.avg_processing_latency_ms ?? 0).toFixed(1)}ms</span>
                    </div>
                    <div class="popup-row">
                        <span class="popup-label">Errors:</span>
                        <span class="popup-value">${activity.errors_total ?? 0}</span>
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
            const activity = this.activityData[officeId] || {};
            const activityLevel = this._getActivityLevel(activity);
            const style =
                this.activityStyles[activityLevel] || this.defaultStyle;

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
        const activity = this.activityData[officeId] || {};
        const activityLevel = this._getActivityLevel(activity);
        const style = this.activityStyles[activityLevel] || this.defaultStyle;

        layer.setStyle(style);
    }

    updateActivityLevels(activityData) {
        this.activityData = activityData || {};

        if (!this.officeLayers) return;

        // Update each office layer with new activity data
        this.officeLayers.eachLayer((layer) => {
            const officeId = layer.officeId;
            const activity = this.activityData[officeId] || {};
            const activityLevel = this._getActivityLevel(activity);

            // Skip selected office
            if (layer === this.selectedOffice) return;

            // Update style based on activity level
            const style =
                this.activityStyles[activityLevel] || this.defaultStyle;
            layer.setStyle(style);

            // Update popup content if it's open
            if (layer.getPopup()?.isOpen()) {
                const newContent = this._createOfficePopup(
                    layer.feature.properties,
                    officeId,
                );
                layer.setPopupContent(newContent);
            }
        });
    }

    _getActivityLevel(activity) {
        const messageCount = activity.messages_processed_total || 0;
        const messagesPerMinute = activity.messages_per_minute || 0;

        // Use messages per minute if available, otherwise estimate from total
        const rate = messagesPerMinute > 0 ? messagesPerMinute : messageCount;

        if (rate >= 100) return "high";
        if (rate >= 20) return "medium";
        if (rate > 0) return "low";
        return "idle";
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
        // Dispatch custom event for office selection
        const event = new CustomEvent("officeSelected", {
            detail: { officeId },
        });
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

        this.rainViewer = {
            layer: null,
            enabled: false,
            opacity: 0.6,
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
            const activity = this.activityData[officeId] || {};
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
                    fillOpacity: 0.2,
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
                this._createRainViewerLayer(latestFrame.time);
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
        color: #1f2937;
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
