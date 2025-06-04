// Metrics Chart Factory for NWWS2MQTT Dashboard
// Chart.js based visualizations for real-time metrics

// biome-ignore lint/complexity/noStaticOnlyClass: <explanation>
class MetricsChartFactory {
    static defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: "top",
                labels: {
                    usePointStyle: true,
                    padding: 20,
                    font: {
                        size: 11,
                    },
                },
            },
            tooltip: {
                backgroundColor: "rgba(255, 255, 255, 0.95)",
                titleColor: "#1f2937",
                bodyColor: "#4b5563",
                borderColor: "#e5e7eb",
                borderWidth: 1,
                cornerRadius: 8,
                displayColors: true,
            },
        },
        layout: {
            padding: {
                top: 10,
                bottom: 10,
            },
        },
    };

    static createThroughputTimeline(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) {
            console.error(`Canvas element with id '${canvasId}' not found`);
            return null;
        }

        const config = {
            type: "line",
            data: {
                labels: [],
                datasets: [
                    {
                        label: "Messages/Minute",
                        data: [],
                        borderColor: "#3b82f6",
                        backgroundColor: "rgba(59, 130, 246, 0.1)",
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 3,
                        pointBackgroundColor: "#3b82f6",
                        pointBorderColor: "#ffffff",
                        pointBorderWidth: 2,
                    },
                    {
                        label: "Warnings",
                        data: [],
                        borderColor: "#f59e0b",
                        backgroundColor: "rgba(245, 158, 11, 0.1)",
                        borderWidth: 2,
                        fill: false,
                        tension: 0.3,
                        pointRadius: 2,
                        pointBackgroundColor: "#f59e0b",
                    },
                    {
                        label: "Errors",
                        data: [],
                        borderColor: "#ef4444",
                        backgroundColor: "rgba(239, 68, 68, 0.1)",
                        borderWidth: 2,
                        fill: false,
                        tension: 0.3,
                        pointRadius: 2,
                        pointBackgroundColor: "#ef4444",
                    },
                ],
            },
            options: {
                ...this.defaultOptions,
                scales: {
                    x: {
                        type: "time",
                        time: {
                            unit: "minute",
                            displayFormats: {
                                minute: "HH:mm",
                            },
                        },
                        title: {
                            display: true,
                            text: "Time",
                            font: {
                                size: 11,
                                weight: 500,
                            },
                        },
                        grid: {
                            color: "#f3f4f6",
                        },
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "Messages per Minute",
                            font: {
                                size: 11,
                                weight: 500,
                            },
                        },
                        grid: {
                            color: "#f3f4f6",
                        },
                    },
                },
                interaction: {
                    intersect: false,
                    mode: "index",
                },
                animation: {
                    duration: 500,
                    easing: "easeInOutQuart",
                },
            },
        };

        const chart = new Chart(ctx, config);

        // Add data update method
        chart.updateData = function (data) {
            const now = new Date(data.timestamp || Date.now());
            const timeLabel = now.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            });

            // Add new data point
            this.data.labels.push(now);
            this.data.datasets[0].data.push(data.messagesPerMinute || 0);
            this.data.datasets[1].data.push(data.warningsPerMinute || 0);
            this.data.datasets[2].data.push(data.errorsPerMinute || 0);

            // Keep only last 30 data points (30 minutes)
            if (this.data.labels.length > 30) {
                this.data.labels.shift();
                this.data.datasets.forEach((dataset) => dataset.data.shift());
            }

            this.update("none");
        };

        return chart;
    }

    static createLatencyHistogram(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) {
            console.error(`Canvas element with id '${canvasId}' not found`);
            return null;
        }

        const config = {
            type: "bar",
            data: {
                labels: [
                    "0-10ms",
                    "10-50ms",
                    "50-100ms",
                    "100-500ms",
                    "500ms-1s",
                    "1s+",
                ],
                datasets: [
                    {
                        label: "Message Count",
                        data: [0, 0, 0, 0, 0, 0],
                        backgroundColor: [
                            "#10b981",
                            "#22c55e",
                            "#eab308",
                            "#f59e0b",
                            "#ef4444",
                            "#dc2626",
                        ],
                        borderColor: [
                            "#059669",
                            "#16a34a",
                            "#ca8a04",
                            "#d97706",
                            "#dc2626",
                            "#b91c1c",
                        ],
                        borderWidth: 1,
                        borderRadius: 4,
                    },
                ],
            },
            options: {
                ...this.defaultOptions,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: "Processing Latency",
                            font: {
                                size: 11,
                                weight: 500,
                            },
                        },
                        grid: {
                            display: false,
                        },
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "Number of Messages",
                            font: {
                                size: 11,
                                weight: 500,
                            },
                        },
                        grid: {
                            color: "#f3f4f6",
                        },
                    },
                },
                plugins: {
                    ...this.defaultOptions.plugins,
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: {
                            label: function (context) {
                                const label = context.dataset.label || "";
                                const value = context.parsed.y;
                                const total = context.dataset.data.reduce(
                                    (a, b) => a + b,
                                    0,
                                );
                                const percentage =
                                    total > 0
                                        ? ((value / total) * 100).toFixed(1)
                                        : "0";
                                return `${label}: ${value} (${percentage}%)`;
                            },
                        },
                    },
                },
            },
        };

        const chart = new Chart(ctx, config);

        // Add data update method
        chart.updateData = function (data) {
            if (data.buckets && Array.isArray(data.buckets)) {
                this.data.datasets[0].data = data.buckets;
            } else {
                // Simulate histogram data from percentile data
                const avg = data.average || 0;
                const p95 = data.p95 || 0;
                const p99 = data.p99 || 0;

                // Rough distribution based on latency percentiles
                const distribution = this._calculateDistribution(avg, p95, p99);
                this.data.datasets[0].data = distribution;
            }

            this.update("none");
        };

        // Helper method to calculate distribution
        chart._calculateDistribution = function (avg, p95, p99) {
            // Simple heuristic to distribute messages across latency buckets
            const total = 100; // Assume 100 messages for percentage calculation
            let distribution = [0, 0, 0, 0, 0, 0];

            if (avg < 10) {
                distribution = [60, 25, 10, 4, 1, 0];
            } else if (avg < 50) {
                distribution = [30, 40, 20, 7, 2, 1];
            } else if (avg < 100) {
                distribution = [10, 30, 35, 20, 4, 1];
            } else if (avg < 500) {
                distribution = [5, 15, 25, 40, 12, 3];
            } else {
                distribution = [2, 8, 15, 30, 30, 15];
            }

            return distribution.map((pct) => Math.round((pct / 100) * total));
        };

        return chart;
    }

    static createProductBreakdown(canvasId, data = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) {
            console.error(`Canvas element with id '${canvasId}' not found`);
            return null;
        }

        const config = {
            type: "doughnut",
            data: {
                labels: [
                    "Warnings",
                    "Watches",
                    "Advisories",
                    "Forecasts",
                    "Other",
                ],
                datasets: [
                    {
                        data: [0, 0, 0, 0, 0],
                        backgroundColor: [
                            "#ef4444", // Red for warnings
                            "#f59e0b", // Orange for watches
                            "#eab308", // Yellow for advisories
                            "#3b82f6", // Blue for forecasts
                            "#6b7280", // Gray for other
                        ],
                        borderColor: "#ffffff",
                        borderWidth: 2,
                        hoverBorderWidth: 3,
                    },
                ],
            },
            options: {
                ...this.defaultOptions,
                plugins: {
                    ...this.defaultOptions.plugins,
                    legend: {
                        position: "bottom",
                        labels: {
                            padding: 15,
                            usePointStyle: true,
                            font: {
                                size: 11,
                            },
                        },
                    },
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: {
                            label: function (context) {
                                const label = context.label || "";
                                const value = context.parsed;
                                const total = context.dataset.data.reduce(
                                    (a, b) => a + b,
                                    0,
                                );
                                const percentage =
                                    total > 0
                                        ? ((value / total) * 100).toFixed(1)
                                        : "0";
                                return `${label}: ${value} (${percentage}%)`;
                            },
                        },
                    },
                },
                cutout: "60%",
                animation: {
                    animateRotate: true,
                    animateScale: false,
                },
            },
        };

        const chart = new Chart(ctx, config);

        // Add data update method
        chart.updateData = function (data) {
            if (data.messagesByType) {
                const types = this.data.labels;
                const newData = types.map((type) => {
                    const key = type.toLowerCase();
                    return data.messagesByType[key] || 0;
                });
                this.data.datasets[0].data = newData;
            }

            this.update("none");
        };

        return chart;
    }

    static createSystemHealthGauge(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) {
            console.error(`Canvas element with id '${canvasId}' not found`);
            return null;
        }

        const config = {
            type: "doughnut",
            data: {
                labels: ["Healthy", "Warning", "Critical"],
                datasets: [
                    {
                        data: [100, 0, 0], // Start with healthy state
                        backgroundColor: [
                            "#10b981", // Green for healthy
                            "#f59e0b", // Orange for warning
                            "#ef4444", // Red for critical
                        ],
                        borderWidth: 0,
                        cutout: "75%",
                    },
                ],
            },
            options: {
                ...this.defaultOptions,
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        enabled: false,
                    },
                },
                rotation: -90,
                circumference: 180,
                animation: {
                    animateRotate: true,
                    duration: 1000,
                },
            },
        };

        const chart = new Chart(ctx, config);

        // Add custom center text
        const originalDraw = chart.draw;
        chart.draw = function () {
            originalDraw.apply(this, arguments);

            const ctx = this.ctx;
            const centerX = (this.chartArea.left + this.chartArea.right) / 2;
            const centerY =
                (this.chartArea.top + this.chartArea.bottom) / 2 + 20;

            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.font = "bold 16px sans-serif";
            ctx.fillStyle = "#1f2937";

            const healthScore = this.data.datasets[0].data[0];
            let status = "HEALTHY";
            if (healthScore < 70) status = "CRITICAL";
            else if (healthScore < 90) status = "WARNING";

            ctx.fillText(status, centerX, centerY);
            ctx.font = "12px sans-serif";
            ctx.fillText(`${healthScore}%`, centerX, centerY + 20);
        };

        // Add health update method
        chart.updateHealth = function (errorRate, latency) {
            let healthScore = 100;

            // Reduce health based on error rate
            healthScore -= Math.min(errorRate * 2, 50);

            // Reduce health based on latency
            if (latency > 1000) healthScore -= 30;
            else if (latency > 500) healthScore -= 15;
            else if (latency > 200) healthScore -= 5;

            healthScore = Math.max(0, Math.round(healthScore));

            // Update data
            if (healthScore >= 90) {
                this.data.datasets[0].data = [healthScore, 0, 0];
            } else if (healthScore >= 70) {
                this.data.datasets[0].data = [0, healthScore, 0];
            } else {
                this.data.datasets[0].data = [0, 0, healthScore];
            }

            this.update("none");
        };

        return chart;
    }

    static createOfficeActivityMap(canvasId, officeData = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) {
            console.error(`Canvas element with id '${canvasId}' not found`);
            return null;
        }

        // Prepare data for horizontal bar chart
        const offices = Object.keys(officeData).slice(0, 10); // Top 10 most active
        const messageCounts = offices.map(
            (office) => officeData[office].messages_processed_total || 0,
        );

        const config = {
            type: "bar",
            data: {
                labels: offices,
                datasets: [
                    {
                        label: "Messages Processed",
                        data: messageCounts,
                        backgroundColor: "#3b82f6",
                        borderColor: "#2563eb",
                        borderWidth: 1,
                        borderRadius: 4,
                    },
                ],
            },
            options: {
                ...this.defaultOptions,
                indexAxis: "y",
                scales: {
                    x: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "Messages Processed",
                            font: {
                                size: 11,
                                weight: 500,
                            },
                        },
                        grid: {
                            color: "#f3f4f6",
                        },
                    },
                    y: {
                        title: {
                            display: true,
                            text: "Weather Offices",
                            font: {
                                size: 11,
                                weight: 500,
                            },
                        },
                        grid: {
                            display: false,
                        },
                    },
                },
                plugins: {
                    ...this.defaultOptions.plugins,
                    legend: {
                        display: false,
                    },
                },
            },
        };

        const chart = new Chart(ctx, config);

        // Add data update method
        chart.updateOfficeData = function (newOfficeData) {
            // Sort offices by activity and take top 10
            const sortedOffices = Object.entries(newOfficeData)
                .sort(
                    ([, a], [, b]) =>
                        (b.messages_processed_total || 0) -
                        (a.messages_processed_total || 0),
                )
                .slice(0, 10);

            this.data.labels = sortedOffices.map(([office]) => office);
            this.data.datasets[0].data = sortedOffices.map(
                ([, data]) => data.messages_processed_total || 0,
            );

            this.update("none");
        };

        return chart;
    }

    static createErrorTimeline(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) {
            console.error(`Canvas element with id '${canvasId}' not found`);
            return null;
        }

        const config = {
            type: "line",
            data: {
                labels: [],
                datasets: [
                    {
                        label: "Error Rate (%)",
                        data: [],
                        borderColor: "#ef4444",
                        backgroundColor: "rgba(239, 68, 68, 0.1)",
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 3,
                        pointBackgroundColor: "#ef4444",
                        pointBorderColor: "#ffffff",
                        pointBorderWidth: 2,
                    },
                ],
            },
            options: {
                ...this.defaultOptions,
                scales: {
                    x: {
                        type: "time",
                        time: {
                            unit: "minute",
                            displayFormats: {
                                minute: "HH:mm",
                            },
                        },
                        title: {
                            display: true,
                            text: "Time",
                            font: {
                                size: 11,
                                weight: 500,
                            },
                        },
                        grid: {
                            color: "#f3f4f6",
                        },
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: "Error Rate (%)",
                            font: {
                                size: 11,
                                weight: 500,
                            },
                        },
                        grid: {
                            color: "#f3f4f6",
                        },
                    },
                },
                plugins: {
                    ...this.defaultOptions.plugins,
                    legend: {
                        display: false,
                    },
                },
            },
        };

        const chart = new Chart(ctx, config);

        // Add data update method
        chart.updateData = function (data) {
            const now = new Date(data.timestamp || Date.now());

            this.data.labels.push(now);
            this.data.datasets[0].data.push(data.errorRate || 0);

            // Keep only last 30 data points
            if (this.data.labels.length > 30) {
                this.data.labels.shift();
                this.data.datasets[0].data.shift();
            }

            this.update("none");
        };

        return chart;
    }
}

// Utility functions for chart data processing
const ChartUtils = {
    formatBytes(bytes) {
        if (bytes === 0) return "0 B";
        const k = 1024;
        const sizes = ["B", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
    },

    formatDuration(milliseconds) {
        if (milliseconds < 1000) return `${milliseconds.toFixed(0)}ms`;
        if (milliseconds < 60000) return `${(milliseconds / 1000).toFixed(1)}s`;
        return `${(milliseconds / 60000).toFixed(1)}m`;
    },

    generateTimeLabels(count, intervalMinutes = 1) {
        const labels = [];
        const now = new Date();
        for (let i = count - 1; i >= 0; i--) {
            const time = new Date(now.getTime() - i * intervalMinutes * 60000);
            labels.push(time);
        }
        return labels;
    },

    interpolateColor(color1, color2, factor) {
        const result = color1.slice();
        for (let i = 0; i < 3; i++) {
            result[i] = Math.round(
                result[i] + factor * (color2[i] - color1[i]),
            );
        }
        return result;
    },

    getActivityColor(level) {
        const colors = {
            idle: "#e5e7eb",
            low: "#10b981",
            medium: "#f59e0b",
            high: "#ef4444",
        };
        return colors[level] || colors.idle;
    },
};
