/**
 * SparklineManager - Manages ApexCharts sparklines for dashboard metric cards
 * Provides robust error handling and graceful fallbacks
 */
class SparklineManager {
    constructor(options = {}) {
        this.sparklines = {};
        this.dataHistory = {};
        this.maxDataPoints = options.maxDataPoints || 30;
        this.isInitialized = false;
        this.hasApexCharts = this._checkApexChartsSupport();

        // Metric configurations
        this.metricConfigs = [
            {
                id: "messages-sparkline",
                color: "#667eea",
                type: "messages",
                label: "Messages",
            },
            {
                id: "offices-sparkline",
                color: "#10b981",
                type: "offices",
                label: "Offices",
            },
            {
                id: "latency-sparkline",
                color: "#f59e0b",
                type: "latency",
                label: "Latency",
            },
            {
                id: "error-sparkline",
                color: "#ef4444",
                type: "errors",
                label: "Errors",
            },
        ];

        console.log(
            `SparklineManager: ApexCharts support: ${this.hasApexCharts}`,
        );
    }

    /**
     * Check if ApexCharts is available and browser supports required features
     */
    _checkApexChartsSupport() {
        try {
            return (
                typeof ApexCharts !== "undefined" &&
                typeof window.requestAnimationFrame !== "undefined" &&
                typeof document.querySelector !== "undefined"
            );
        } catch (error) {
            console.warn("ApexCharts support check failed:", error);
            return false;
        }
    }

    /**
     * Initialize all sparklines with error handling
     */
    async initializeSparklines() {
        if (!this.hasApexCharts) {
            console.warn(
                "SparklineManager: ApexCharts not available, skipping sparkline initialization",
            );
            this._enableFallbackMode();
            return false;
        }

        try {
            console.log("SparklineManager: Initializing sparklines...");

            const initPromises = this.metricConfigs.map((config) =>
                this._initializeSparkline(config),
            );

            const results = await Promise.allSettled(initPromises);

            // Check for any failures
            const failures = results.filter(
                (result) => result.status === "rejected",
            );
            if (failures.length > 0) {
                console.warn(
                    `SparklineManager: ${failures.length} sparklines failed to initialize`,
                );
                failures.forEach((failure, index) => {
                    console.error(
                        `Failed to initialize ${this.metricConfigs[index].id}:`,
                        failure.reason,
                    );
                });
            }

            const successes = results.filter(
                (result) => result.status === "fulfilled",
            ).length;
            console.log(
                `SparklineManager: Successfully initialized ${successes}/${this.metricConfigs.length} sparklines`,
            );

            this.isInitialized = successes > 0;

            if (!this.isInitialized) {
                this._enableFallbackMode();
            }

            return this.isInitialized;
        } catch (error) {
            console.error(
                "SparklineManager: Failed to initialize sparklines:",
                error,
            );
            this._enableFallbackMode();
            return false;
        }
    }

    /**
     * Initialize a single sparkline with error handling
     */
    async _initializeSparkline(config) {
        const { id, color, type, label } = config;

        return new Promise((resolve, reject) => {
            try {
                const element = document.querySelector(`#${id}`);
                if (!element) {
                    reject(new Error(`Element #${id} not found`));
                    return;
                }

                const options = this._createSparklineOptions(color, label);

                const chart = new ApexCharts(element, options);

                chart
                    .render()
                    .then(() => {
                        this.sparklines[type] = chart;
                        this.dataHistory[type] = [];
                        console.log(
                            `SparklineManager: Successfully initialized ${id}`,
                        );
                        resolve(chart);
                    })
                    .catch((error) => {
                        console.error(
                            `Failed to render sparkline ${id}:`,
                            error,
                        );
                        reject(error);
                    });
            } catch (error) {
                console.error(`Error creating sparkline ${id}:`, error);
                reject(error);
            }
        });
    }

    /**
     * Create ApexCharts options for sparkline
     */
    _createSparklineOptions(color, label) {
        return {
            series: [
                {
                    name: label,
                    data: [],
                },
            ],
            chart: {
                type: "area",
                height: 40,
                sparkline: {
                    enabled: true,
                },
                animations: {
                    enabled: true,
                    easing: "easeinout",
                    speed: 400,
                    animateGradually: {
                        enabled: false,
                    },
                },
                toolbar: {
                    show: false,
                },
                zoom: {
                    enabled: false,
                },
            },
            stroke: {
                curve: "smooth",
                width: 2,
                colors: [color],
            },
            fill: {
                type: "gradient",
                gradient: {
                    shade: "light",
                    type: "vertical",
                    shadeIntensity: 0.4,
                    gradientToColors: [color],
                    inverseColors: false,
                    opacityFrom: 0.6,
                    opacityTo: 0.1,
                    stops: [0, 100],
                },
            },
            tooltip: {
                enabled: false,
            },
            grid: {
                show: false,
            },
            xaxis: {
                type: "datetime",
                axisBorder: {
                    show: false,
                },
                axisTicks: {
                    show: false,
                },
            },
            yaxis: {
                show: false,
                min: 0,
            },
            markers: {
                size: 0,
            },
        };
    }

    /**
     * Update sparkline with new data point
     */
    updateSparkline(type, value, timestamp) {
        if (!this.isInitialized || !this.hasApexCharts) {
            return false;
        }

        try {
            const chart = this.sparklines[type];
            const history = this.dataHistory[type];

            if (!chart || !history) {
                console.warn(
                    `SparklineManager: No chart or history found for type: ${type}`,
                );
                return false;
            }

            // Add new data point
            history.push({
                x: timestamp,
                y: value,
            });

            // Keep only last N points
            if (history.length > this.maxDataPoints) {
                history.shift();
            }

            // Update chart
            chart.updateSeries(
                [
                    {
                        name: this._getLabelForType(type),
                        data: [...history], // Create copy to avoid reference issues
                    },
                ],
                false,
            ); // Don't animate for frequent updates

            return true;
        } catch (error) {
            console.error(
                `SparklineManager: Failed to update sparkline for ${type}:`,
                error,
            );
            return false;
        }
    }

    /**
     * Get label for metric type
     */
    _getLabelForType(type) {
        const config = this.metricConfigs.find((c) => c.type === type);
        return config ? config.label : type;
    }

    /**
     * Enable fallback mode - show legacy trend indicators
     */
    _enableFallbackMode() {
        console.log("SparklineManager: Enabling fallback mode");

        try {
            // Hide sparkline containers and show legacy trend indicators
            for (const config of this.metricConfigs) {
                const sparklineElement = document.querySelector(
                    `#${config.id}`,
                );
                const trendElement = document.querySelector(
                    `#${config.type}-trend`,
                );

                if (sparklineElement) {
                    sparklineElement.style.display = "none";
                }

                if (trendElement) {
                    trendElement.style.display = "block";
                }
            }
        } catch (error) {
            console.error(
                "SparklineManager: Failed to enable fallback mode:",
                error,
            );
        }
    }

    /**
     * Check if sparklines are working
     */
    isWorking() {
        return this.isInitialized && this.hasApexCharts;
    }

    /**
     * Get sparkline data for debugging
     */
    getSparklineData(type) {
        return this.dataHistory[type] || [];
    }

    /**
     * Clear all sparkline data
     */
    clearData() {
        if (!this.isInitialized) return;

        try {
            for (const type of Object.keys(this.dataHistory)) {
                this.dataHistory[type] = [];
                if (this.sparklines[type]) {
                    this.sparklines[type].updateSeries(
                        [
                            {
                                name: this._getLabelForType(type),
                                data: [],
                            },
                        ],
                        false,
                    );
                }
            }
        } catch (error) {
            console.error("SparklineManager: Failed to clear data:", error);
        }
    }

    /**
     * Destroy all sparklines and clean up
     */
    destroy() {
        try {
            console.log("SparklineManager: Destroying sparklines...");

            for (const chart of Object.values(this.sparklines)) {
                if (chart && typeof chart.destroy === "function") {
                    try {
                        chart.destroy();
                    } catch (error) {
                        console.error("Error destroying chart:", error);
                    }
                }
            }

            this.sparklines = {};
            this.dataHistory = {};
            this.isInitialized = false;

            console.log("SparklineManager: Cleanup complete");
        } catch (error) {
            console.error("SparklineManager: Error during destruction:", error);
        }
    }
}

// Export for use in other modules
if (typeof module !== "undefined" && module.exports) {
    module.exports = SparklineManager;
}
