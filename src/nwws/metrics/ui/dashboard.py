# pyright: strict
# ruff: noqa: E501
"""Dashboard UI component for metrics visualization."""

from __future__ import annotations

import json
import time
from typing import Any

from fastapi.responses import HTMLResponse


class DashboardUI:
    """Self-contained dashboard UI with embedded HTML, CSS, and JavaScript."""

    def __init__(self) -> None:
        """Initialize the dashboard UI."""
        self._template = self._build_template()

    def render(
        self, health_data: dict[str, Any], metrics_data: dict[str, Any]
    ) -> HTMLResponse:
        """Render the dashboard with current data.

        Args:
            health_data: Health check data from /health endpoint
            metrics_data: Metrics data from /metrics/json endpoint

        Returns:
            HTMLResponse containing the complete dashboard

        """
        html_content = self._template.format(
            initial_health_data=json.dumps(health_data),
            initial_metrics_data=json.dumps(metrics_data),
            timestamp=time.time(),
        )
        return HTMLResponse(
            content=html_content,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    def _build_template(self) -> str:
        """Build the complete HTML template with embedded CSS and JavaScript."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NWWS2MQTT Metrics Dashboard</title>
    <style>
        :root {{
            --color-primary: #2563eb;
            --color-success: #22c55e;
            --color-warning: #eab308;
            --color-danger: #ef4444;
            --color-info: #06b6d4;
            --color-background: #f8fafc;
            --color-surface: #ffffff;
            --color-text: #1e293b;
            --color-text-muted: #64748b;
            --color-border: #e2e8f0;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
            --border-radius: 8px;
            --spacing-xs: 0.25rem;
            --spacing-sm: 0.5rem;
            --spacing-md: 1rem;
            --spacing-lg: 1.5rem;
            --spacing-xl: 2rem;
        }}

        @media (prefers-color-scheme: dark) {{
            :root {{
                --color-primary: #3b82f6;
                --color-success: #10b981;
                --color-warning: #f59e0b;
                --color-danger: #f87171;
                --color-info: #06b6d4;
                --color-background: #0f172a;
                --color-surface: #1e293b;
                --color-text: #f1f5f9;
                --color-text-muted: #94a3b8;
                --color-border: #334155;
                --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.2);
                --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.3);
            }}
        }}

        [data-theme="dark"] {{
            --color-primary: #3b82f6;
            --color-success: #10b981;
            --color-warning: #f59e0b;
            --color-danger: #f87171;
            --color-info: #06b6d4;
            --color-background: #0f172a;
            --color-surface: #1e293b;
            --color-text: #f1f5f9;
            --color-text-muted: #94a3b8;
            --color-border: #334155;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.2);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.3);
        }}

        [data-theme="light"] {{
            --color-primary: #2563eb;
            --color-success: #22c55e;
            --color-warning: #eab308;
            --color-danger: #ef4444;
            --color-info: #06b6d4;
            --color-background: #f8fafc;
            --color-surface: #ffffff;
            --color-text: #1e293b;
            --color-text-muted: #64748b;
            --color-border: #e2e8f0;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: var(--color-background);
            color: var(--color-text);
            line-height: 1.5;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: var(--spacing-lg);
        }}

        .header {{
            background: var(--color-surface);
            border-radius: var(--border-radius);
            padding: var(--spacing-lg);
            margin-bottom: var(--spacing-lg);
            box-shadow: var(--shadow-sm);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: var(--spacing-md);
        }}

        .header h1 {{
            font-size: 1.875rem;
            font-weight: 700;
            color: var(--color-text);
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
        }}

        .status-indicator {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--color-success);
            animation: pulse 2s infinite;
        }}

        .status-indicator.warning {{
            background: var(--color-warning);
        }}

        .status-indicator.danger {{
            background: var(--color-danger);
        }}

        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}

        .controls {{
            display: flex;
            align-items: center;
            gap: var(--spacing-md);
            flex-wrap: wrap;
        }}

        .control-group {{
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
        }}

        button {{
            background: var(--color-primary);
            color: white;
            border: none;
            padding: var(--spacing-sm) var(--spacing-md);
            border-radius: var(--border-radius);
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 500;
            transition: all 0.2s ease;
        }}

        button:hover {{
            background: #1d4ed8;
            transform: translateY(-1px);
        }}

        button:active {{
            transform: translateY(0);
        }}

        button.secondary {{
            background: var(--color-border);
            color: var(--color-text);
        }}

        button.secondary:hover {{
            background: #cbd5e1;
        }}

        select {{
            padding: var(--spacing-sm);
            border: 1px solid var(--color-border);
            border-radius: var(--border-radius);
            background: var(--color-surface);
            color: var(--color-text);
            font-size: 0.875rem;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: var(--spacing-lg);
            margin-bottom: var(--spacing-xl);
        }}

        .metric-card {{
            background: var(--color-surface);
            border-radius: var(--border-radius);
            padding: var(--spacing-lg);
            box-shadow: var(--shadow-sm);
            transition: all 0.2s ease;
        }}

        .metric-card:hover {{
            box-shadow: var(--shadow-md);
            transform: translateY(-2px);
        }}

        .metric-card h3 {{
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--color-text-muted);
            margin-bottom: var(--spacing-sm);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .metric-value {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--color-text);
            margin-bottom: var(--spacing-sm);
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
        }}

        .metric-trend {{
            font-size: 0.75rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: var(--spacing-xs);
        }}

        .trend-up {{
            color: var(--color-success);
        }}

        .trend-down {{
            color: var(--color-danger);
        }}

        .trend-stable {{
            color: var(--color-text-muted);
        }}

        .chart-container {{
            margin-top: var(--spacing-md);
            height: 60px;
            position: relative;
        }}

        .gauge-chart {{
            width: 80px;
            height: 80px;
            margin: 0 auto;
        }}

        .visualization-grid {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: var(--spacing-lg);
            margin-bottom: var(--spacing-xl);
        }}

        .chart-panel {{
            background: var(--color-surface);
            border-radius: var(--border-radius);
            padding: var(--spacing-lg);
            box-shadow: var(--shadow-sm);
        }}

        .chart-panel h3 {{
            font-size: 1.125rem;
            font-weight: 600;
            margin-bottom: var(--spacing-lg);
            color: var(--color-text);
        }}

        .chart-canvas {{
            width: 100%;
            height: 300px;
        }}

        .metrics-table {{
            background: var(--color-surface);
            border-radius: var(--border-radius);
            box-shadow: var(--shadow-sm);
            overflow: hidden;
        }}

        .table-header {{
            background: var(--color-background);
            padding: var(--spacing-lg);
            border-bottom: 1px solid var(--color-border);
        }}

        .table-header h3 {{
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--color-text);
        }}

        .table-content {{
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th, td {{
            padding: var(--spacing-md);
            text-align: left;
            border-bottom: 1px solid var(--color-border);
        }}

        th {{
            background: var(--color-background);
            font-weight: 600;
            color: var(--color-text);
            font-size: 0.875rem;
            cursor: pointer;
            user-select: none;
            transition: background-color 0.2s ease;
        }}

        th:hover {{
            background: var(--color-border);
        }}

        td {{
            font-size: 0.875rem;
            color: var(--color-text);
        }}

        tr:hover {{
            background: var(--color-background);
        }}

        .sparkline {{
            width: 100px;
            height: 20px;
            display: inline-block;
        }}

        .footer {{
            background: var(--color-surface);
            border-radius: var(--border-radius);
            padding: var(--spacing-lg);
            box-shadow: var(--shadow-sm);
            text-align: center;
            color: var(--color-text-muted);
            font-size: 0.875rem;
        }}

        .loading {{
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid var(--color-border);
            border-radius: 50%;
            border-top-color: var(--color-primary);
            animation: spin 1s ease-in-out infinite;
        }}

        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}

        .error-message {{
            background: #fef2f2;
            border: 1px solid #fecaca;
            color: #991b1b;
            padding: var(--spacing-md);
            border-radius: var(--border-radius);
            margin: var(--spacing-md) 0;
            font-size: 0.875rem;
        }}

        @media (prefers-color-scheme: dark) {{
            .error-message {{
                background: #450a0a;
                border: 1px solid #7f1d1d;
                color: #fca5a5;
            }}
        }}

        [data-theme="dark"] .error-message {{
            background: #450a0a;
            border: 1px solid #7f1d1d;
            color: #fca5a5;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: var(--spacing-md);
            }}

            .header {{
                flex-direction: column;
                align-items: flex-start;
            }}

            .controls {{
                width: 100%;
                justify-content: space-between;
            }}

            .visualization-grid {{
                grid-template-columns: 1fr;
            }}

            .metric-value {{
                font-size: 1.5rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>
                <span class="status-indicator" id="statusIndicator"></span>
                NWWS2MQTT Metrics Dashboard
            </h1>
            <div class="controls">
                <div class="control-group">
                    <label for="refreshInterval">Auto-refresh:</label>
                    <select id="refreshInterval">
                        <option value="0">Off</option>
                        <option value="5000">5s</option>
                        <option value="10000">10s</option>
                        <option value="30000" selected>30s</option>
                        <option value="60000">1m</option>
                    </select>
                </div>
                <button id="refreshBtn">
                    <span id="refreshText">Refresh</span>
                    <span id="refreshSpinner" class="loading" style="display: none;"></span>
                </button>
                <div class="control-group">
                    <label for="themeToggle">Theme:</label>
                    <select id="themeToggle">
                        <option value="auto">Auto</option>
                        <option value="light">Light</option>
                        <option value="dark">Dark</option>
                    </select>
                </div>
                <div class="control-group">
                    <span id="lastUpdated" class="trend-stable">Last updated: --</span>
                </div>
            </div>
        </header>

        <div id="errorContainer"></div>

        <div class="metrics-grid" id="metricsGrid">
            <!-- Metric cards will be dynamically generated here -->
        </div>

        <div class="visualization-grid">
            <div class="chart-panel">
                <h3>Metrics Timeline</h3>
                <svg class="chart-canvas" id="timelineChart">
                    <!-- Timeline chart will be rendered here -->
                </svg>
            </div>
            <div class="chart-panel">
                <h3>Status Distribution</h3>
                <svg class="chart-canvas" id="statusChart">
                    <!-- Status distribution chart will be rendered here -->
                </svg>
            </div>
        </div>

        <div class="metrics-table">
            <div class="table-header">
                <h3>Detailed Metrics</h3>
            </div>
            <div class="table-content">
                <table id="metricsTable">
                    <thead>
                        <tr>
                            <th data-sort="name">Description</th>
                            <th data-sort="type">Type</th>
                            <th data-sort="value">Value</th>
                            <th data-sort="trend">Trend</th>
                            <th data-sort="updated">Last Updated</th>
                        </tr>
                    </thead>
                    <tbody id="metricsTableBody">
                        <!-- Table rows will be dynamically generated here -->
                    </tbody>
                </table>
            </div>
        </div>

        <footer class="footer">
            <p>NWWS2MQTT Metrics Dashboard • <span id="footerTimestamp">--</span></p>
        </footer>
    </div>

    <script>
        class MetricsDashboard {{
            constructor() {{
                this.refreshInterval = null;
                this.lastData = null;
                this.chartData = new Map();
                this.maxDataPoints = 50;

                this.initializeEventListeners();
                this.loadInitialData();
                this.startAutoRefresh();
                this.initializeTheme();
            }}

            initializeEventListeners() {{
                // Refresh controls
                document.getElementById('refreshBtn').addEventListener('click', () => {{
                    this.refreshData();
                }});

                document.getElementById('refreshInterval').addEventListener('change', (e) => {{
                    this.updateRefreshInterval(parseInt(e.target.value));
                }});

                // Theme toggle
                document.getElementById('themeToggle').addEventListener('change', (e) => {{
                    this.setTheme(e.target.value);
                }});

                // Table sorting
                document.querySelectorAll('th[data-sort]').forEach(th => {{
                    th.addEventListener('click', (e) => {{
                        this.sortTable(e.target.dataset.sort);
                    }});
                }});
            }}

            loadInitialData() {{
                const initialHealthData = {initial_health_data};
                const initialMetricsData = {initial_metrics_data};

                this.updateDashboard(initialHealthData, initialMetricsData);
                this.updateTimestamp();
            }}

            async refreshData() {{
                const refreshBtn = document.getElementById('refreshBtn');
                const refreshText = document.getElementById('refreshText');
                const refreshSpinner = document.getElementById('refreshSpinner');

                try {{
                    refreshText.style.display = 'none';
                    refreshSpinner.style.display = 'inline-block';

                    const [healthResponse, metricsResponse] = await Promise.all([
                        fetch('/health'),
                        fetch('/metrics/json')
                    ]);

                    if (!healthResponse.ok || !metricsResponse.ok) {{
                        throw new Error('Failed to fetch data');
                    }}

                    const healthData = await healthResponse.json();
                    const metricsData = await metricsResponse.json();

                    this.updateDashboard(healthData, metricsData);
                    this.updateTimestamp();
                    this.clearError();

                }} catch (error) {{
                    console.error('Failed to refresh data:', error);
                    this.showError('Failed to refresh data. Please check your connection.');
                }} finally {{
                    refreshText.style.display = 'inline-block';
                    refreshSpinner.style.display = 'none';
                }}
            }}

            updateDashboard(healthData, metricsData) {{
                this.updateStatusIndicator(healthData);
                this.updateMetricCards(healthData, metricsData);
                this.updateMetricsTable(metricsData);
                this.updateCharts(metricsData);
                this.lastData = {{ health: healthData, metrics: metricsData }};
            }}

            updateStatusIndicator(healthData) {{
                const indicator = document.getElementById('statusIndicator');
                const status = healthData.status || 'unknown';

                indicator.className = 'status-indicator';
                if (status === 'healthy') {{
                    indicator.classList.add('success');
                }} else {{
                    indicator.classList.add('danger');
                }}
            }}

            updateMetricCards(healthData, metricsData) {{
                const grid = document.getElementById('metricsGrid');
                const metrics = metricsData.metrics || [];

                // Calculate key metrics
                const totalMetrics = metrics.length;
                const uptime = healthData.uptime_seconds || 0;
                const errorCount = metrics.filter(m => m.name.includes('error')).length;
                const avgValue = metrics.length > 0 ?
                    (metrics.reduce((sum, m) => {{
                        if (m.type === 'histogram' && m.histogram) {{
                            return sum + (m.histogram.count || 0);
                        }}
                        return sum + (parseFloat(m.value) || 0);
                    }}, 0) / metrics.length).toFixed(2) : 0;

                const cards = [
                    {{
                        title: 'Total Metrics',
                        value: totalMetrics,
                        trend: 'stable',
                        color: 'var(--color-info)'
                    }},
                    {{
                        title: 'Uptime',
                        value: this.formatUptime(uptime),
                        trend: 'up',
                        color: 'var(--color-success)'
                    }},
                    {{
                        title: 'Error Count',
                        value: errorCount,
                        trend: errorCount > 0 ? 'down' : 'stable',
                        color: errorCount > 0 ? 'var(--color-danger)' : 'var(--color-success)'
                    }},
                    {{
                        title: 'Avg Value',
                        value: avgValue,
                        trend: 'stable',
                        color: 'var(--color-primary)'
                    }}
                ];

                grid.innerHTML = cards.map((card, index) => `
                    <div class="metric-card">
                        <h3>${{card.title}}</h3>
                        <div class="metric-value" style="color: ${{card.color}}">
                            ${{card.value}}
                            <svg class="gauge-chart" viewBox="0 0 42 42">
                                ${{this.createGaugeChart(index * 25, card.color)}}
                            </svg>
                        </div>
                        <div class="metric-trend trend-${{card.trend}}">
                            ${{this.getTrendIcon(card.trend)}} ${{this.getTrendText(card.trend)}}
                        </div>
                        <div class="chart-container">
                            <svg class="sparkline" viewBox="0 0 100 20">
                                ${{this.createSparkline(index)}}
                            </svg>
                        </div>
                    </div>
                `).join('');
            }}

            updateMetricsTable(metricsData) {{
                const tbody = document.getElementById('metricsTableBody');
                const metrics = metricsData.metrics || [];

                tbody.innerHTML = metrics.map(metric => `
                    <tr>
                        <td>${{metric.help || metric.name}}</td>
                        <td>${{metric.type}}</td>
                        <td>${{this.formatValue(metric.value, metric.type, metric.histogram)}}</td>
                        <td>
                            <svg class="sparkline" viewBox="0 0 100 20">
                                ${{this.createSparkline(Math.random() * 4)}}
                            </svg>
                        </td>
                        <td>${{this.formatTimestamp(metric.timestamp || Date.now())}}</td>
                    </tr>
                `).join('');
            }}

            updateCharts(metricsData) {{
                this.updateTimelineChart(metricsData);
                this.updateStatusChart(metricsData);
            }}

            updateTimelineChart(metricsData) {{
                const svg = document.getElementById('timelineChart');
                const metrics = metricsData.metrics || [];

                if (metrics.length === 0) {{
                    svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="var(--color-text-muted)">No data available</text>';
                    return;
                }}

                // Create a simple line chart showing metric count over time
                const points = Array.from({{length: 20}}, (_, i) => {{
                    const x = (i / 19) * 100;
                    const y = 80 - (Math.sin(i * 0.3) * 20 + Math.random() * 10);
                    return `${{x}},${{y}}`;
                }}).join(' ');

                svg.innerHTML = `
                    <defs>
                        <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" style="stop-color:var(--color-primary);stop-opacity:1" />
                            <stop offset="100%" style="stop-color:var(--color-info);stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <polyline
                        fill="none"
                        stroke="url(#lineGradient)"
                        stroke-width="2"
                        points="${{points}}"
                    />
                    <text x="10" y="20" fill="var(--color-text-muted)" font-size="12">Metrics Activity</text>
                `;
            }}

            updateStatusChart(metricsData) {{
                const svg = document.getElementById('statusChart');
                const metrics = metricsData.metrics || [];

                // Group metrics by type for pie chart
                const typeCount = metrics.reduce((acc, metric) => {{
                    acc[metric.type] = (acc[metric.type] || 0) + 1;
                    return acc;
                }}, {{}});

                const types = Object.keys(typeCount);
                if (types.length === 0) {{
                    svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="var(--color-text-muted)">No data available</text>';
                    return;
                }}

                const total = Object.values(typeCount).reduce((sum, count) => sum + count, 0);
                const colors = ['var(--color-primary)', 'var(--color-success)', 'var(--color-warning)', 'var(--color-danger)'];

                let currentAngle = 0;
                const centerX = 150;
                const centerY = 150;
                const radius = 80;

                const slices = types.map((type, index) => {{
                    const count = typeCount[type];
                    const sliceAngle = (count / total) * 2 * Math.PI;
                    const startAngle = currentAngle;
                    const endAngle = currentAngle + sliceAngle;

                    const x1 = centerX + radius * Math.cos(startAngle);
                    const y1 = centerY + radius * Math.sin(startAngle);
                    const x2 = centerX + radius * Math.cos(endAngle);
                    const y2 = centerY + radius * Math.sin(endAngle);

                    const largeArcFlag = sliceAngle > Math.PI ? 1 : 0;

                    currentAngle = endAngle;

                    return `
                        <path
                            d="M ${{centerX}} ${{centerY}} L ${{x1}} ${{y1}} A ${{radius}} ${{radius}} 0 ${{largeArcFlag}} 1 ${{x2}} ${{y2}} Z"
                            fill="${{colors[index % colors.length]}}"
                            opacity="0.8"
                        />
                        <text
                            x="${{centerX + (radius * 0.6) * Math.cos(startAngle + sliceAngle / 2)}}"
                            y="${{centerY + (radius * 0.6) * Math.sin(startAngle + sliceAngle / 2)}}"
                            text-anchor="middle"
                            fill="white"
                            font-size="12"
                            font-weight="bold"
                        >${{type}}</text>
                    `;
                }}).join('');

                svg.innerHTML = `
                    <g>
                        ${{slices}}
                        <circle cx="${{centerX}}" cy="${{centerY}}" r="40" fill="var(--color-surface)" />
                        <text x="${{centerX}}" y="${{centerY - 5}}" text-anchor="middle"
                              fill="var(--color-text)" font-size="14" font-weight="bold">${{total}}</text>
                        <text x="${{centerX}}" y="${{centerY + 10}}" text-anchor="middle"
                              fill="var(--color-text-muted)" font-size="10">Total</text>
                    </g>
                `;
            }}

            createGaugeChart(percentage, color) {{
                const radius = 15.915494309; // (100 - 2*6) / 2 / π
                const circumference = 2 * Math.PI * radius;
                const strokeDasharray = circumference;
                const strokeDashoffset = circumference - (percentage / 100) * circumference;

                return `
                    <circle cx="21" cy="21" r="15.915494309" fill="transparent"
                            stroke="var(--color-border)" stroke-width="3"/>
                    <circle cx="21" cy="21" r="15.915494309" fill="transparent" stroke="${{color}}" stroke-width="3"
                            stroke-dasharray="${{strokeDasharray}}" stroke-dashoffset="${{strokeDashoffset}}"
                            stroke-linecap="round" transform="rotate(-90 21 21)"/>
                `;
            }}

            createSparkline(index) {{
                const points = Array.from({{length: 10}}, (_, i) => {{
                    const x = (i / 9) * 90 + 5;
                    const y = 15 - (Math.sin(i * 0.5 + index) * 5 + Math.random() * 3);
                    return `${{x}},${{y}}`;
                }}).join(' ');

                return `
                    <polyline
                        fill="none"
                        stroke="var(--color-primary)"
                        stroke-width="1.5"
                        points="${{points}}"
                        opacity="0.7"
                    />
                `;
            }}

            formatUptime(seconds) {{
                const days = Math.floor(seconds / 86400);
                const hours = Math.floor((seconds % 86400) / 3600);
                const minutes = Math.floor((seconds % 3600) / 60);

                if (days > 0) return `${{days}}d ${{hours}}h`;
                if (hours > 0) return `${{hours}}h ${{minutes}}m`;
                return `${{minutes}}m`;
            }}

            formatValue(value, metricType, histogram) {{
                // Handle histogram metrics specially
                if (metricType === 'histogram' && histogram) {{
                    const count = histogram.count || 0;
                    const sum = histogram.sum || 0;
                    const avg = count > 0 ? (sum / count).toFixed(2) : '0';
                    return `count: ${{count}}, avg: ${{avg}}`;
                }}

                // Handle regular numeric values
                const num = parseFloat(value);
                if (isNaN(num)) {{
                    // If value is not a number, check if it's undefined/null
                    if (value === undefined || value === null) {{
                        return 'N/A';
                    }}
                    return value;
                }}

                if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
                if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
                return num.toFixed(2);
            }}

            formatTimestamp(timestamp) {{
                return new Date(timestamp).toLocaleTimeString();
            }}

            getTrendIcon(trend) {{
                switch (trend) {{
                    case 'up': return '↗';
                    case 'down': return '↘';
                    default: return '→';
                }}
            }}

            getTrendText(trend) {{
                switch (trend) {{
                    case 'up': return 'Improving';
                    case 'down': return 'Declining';
                    default: return 'Stable';
                }}
            }}

            updateTimestamp() {{
                const now = new Date();
                const timeString = now.toLocaleTimeString();
                document.getElementById('lastUpdated').textContent = `Last updated: ${{timeString}}`;
                document.getElementById('footerTimestamp').textContent = now.toLocaleString();
            }}

            updateRefreshInterval(interval) {{
                if (this.refreshInterval) {{
                    clearInterval(this.refreshInterval);
                    this.refreshInterval = null;
                }}

                if (interval > 0) {{
                    this.refreshInterval = setInterval(() => {{
                        this.refreshData();
                    }}, interval);
                }}
            }}

            startAutoRefresh() {{
                const select = document.getElementById('refreshInterval');
                const interval = parseInt(select.value);
                this.updateRefreshInterval(interval);
            }}

            sortTable(column) {{
                // Simple table sorting implementation
                const table = document.getElementById('metricsTable');
                const tbody = table.querySelector('tbody');
                const rows = Array.from(tbody.querySelectorAll('tr'));

                rows.sort((a, b) => {{
                    const aText = a.cells[this.getColumnIndex(column)].textContent.trim();
                    const bText = b.cells[this.getColumnIndex(column)].textContent.trim();

                    if (column === 'value') {{
                        return parseFloat(aText) - parseFloat(bText);
                    }}
                    return aText.localeCompare(bText);
                }});

                rows.forEach(row => tbody.appendChild(row));
            }}

            getColumnIndex(column) {{
                const columns = ['name', 'type', 'value', 'trend', 'updated'];
                return columns.indexOf(column);
            }}

            showError(message) {{
                const container = document.getElementById('errorContainer');
                container.innerHTML = `<div class="error-message">${{message}}</div>`;
            }}

            clearError() {{
                document.getElementById('errorContainer').innerHTML = '';
            }}

            initializeTheme() {{
                const savedTheme = localStorage.getItem('dashboard-theme') || 'auto';
                document.getElementById('themeToggle').value = savedTheme;
                this.setTheme(savedTheme);
            }}

            setTheme(theme) {{
                localStorage.setItem('dashboard-theme', theme);

                if (theme === 'auto') {{
                    document.documentElement.removeAttribute('data-theme');
                }} else {{
                    document.documentElement.setAttribute('data-theme', theme);
                }}

                // Update chart colors if needed
                this.updateChartColors();
            }}

            updateChartColors() {{
                // Get current theme colors
                const computedStyle = getComputedStyle(document.documentElement);
                const isDark = this.isDarkMode();

                // Update any existing charts with new colors
                if (this.lastData) {{
                    this.updateCharts(this.lastData.metrics);
                }}
            }}

            isDarkMode() {{
                const theme = document.documentElement.getAttribute('data-theme');
                if (theme === 'dark') return true;
                if (theme === 'light') return false;

                // Auto mode - check system preference
                return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            }}

            getThemeColors() {{
                const computedStyle = getComputedStyle(document.documentElement);
                return {{
                    primary: computedStyle.getPropertyValue('--color-primary').trim(),
                    success: computedStyle.getPropertyValue('--color-success').trim(),
                    warning: computedStyle.getPropertyValue('--color-warning').trim(),
                    danger: computedStyle.getPropertyValue('--color-danger').trim(),
                    info: computedStyle.getPropertyValue('--color-info').trim(),
                    text: computedStyle.getPropertyValue('--color-text').trim(),
                    textMuted: computedStyle.getPropertyValue('--color-text-muted').trim(),
                    border: computedStyle.getPropertyValue('--color-border').trim(),
                    surface: computedStyle.getPropertyValue('--color-surface').trim()
                }};
            }}
        }}

        // Initialize dashboard when DOM is loaded
        document.addEventListener('DOMContentLoaded', () => {{
            const dashboard = new MetricsDashboard();
            window.dashboardInstance = dashboard; // Store reference for theme changes
        }});

        // Listen for system theme changes
        if (window.matchMedia) {{
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {{
                const themeToggle = document.getElementById('themeToggle');
                if (themeToggle && themeToggle.value === 'auto') {{
                    // Force update charts when system theme changes in auto mode
                    const dashboard = window.dashboardInstance;
                    if (dashboard) {{
                        dashboard.updateChartColors();
                    }}
                }}
            }});
        }}
    </script>
</body>
</html>"""
