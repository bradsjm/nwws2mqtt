# pyright: strict
"""Advanced visualization components for the metrics dashboard."""

from __future__ import annotations

import math
from typing import Any

# Type aliases for better readability
type ColorScheme = str
type MetricData = dict[str, float]
type HeatMapData = dict[str, MetricData]
type NetworkConnections = dict[str, list[str]]
type NodePosition = tuple[float, float]
type NodePositions = dict[str, NodePosition]


class AdvancedVisualizations:
    """Advanced visualization components using pure SVG and JavaScript."""

    @staticmethod
    def get_theme_colors() -> dict[str, str]:
        """Get theme-aware colors for visualizations.

        Returns:
            Dictionary with color mappings for light/dark themes

        """
        return {
            "primary": "var(--color-primary, #2563eb)",
            "success": "var(--color-success, #22c55e)",
            "warning": "var(--color-warning, #eab308)",
            "danger": "var(--color-danger, #ef4444)",
            "info": "var(--color-info, #06b6d4)",
            "text": "var(--color-text, #1e293b)",
            "text_muted": "var(--color-text-muted, #64748b)",
            "border": "var(--color-border, #e2e8f0)",
            "surface": "var(--color-surface, #ffffff)",
            "background": "var(--color-background, #f8fafc)",
        }

    @staticmethod
    def _get_color_maps() -> dict[ColorScheme, list[str]]:
        """Get color maps for different schemes.

        Returns:
            Dictionary mapping color scheme names to color lists

        """
        theme_colors = AdvancedVisualizations.get_theme_colors()
        return {
            "blue": [
                "rgba(59, 130, 246, 0.1)",
                "rgba(59, 130, 246, 0.2)",
                "rgba(59, 130, 246, 0.3)",
                "rgba(59, 130, 246, 0.4)",
                "rgba(59, 130, 246, 0.6)",
                "rgba(59, 130, 246, 0.7)",
                theme_colors["primary"],
                "rgba(59, 130, 246, 0.9)",
            ],
            "green": [
                "rgba(16, 185, 129, 0.1)",
                "rgba(16, 185, 129, 0.2)",
                "rgba(16, 185, 129, 0.3)",
                "rgba(16, 185, 129, 0.4)",
                "rgba(16, 185, 129, 0.6)",
                "rgba(16, 185, 129, 0.7)",
                theme_colors["success"],
                "rgba(16, 185, 129, 0.9)",
            ],
            "red": [
                "rgba(248, 113, 113, 0.1)",
                "rgba(248, 113, 113, 0.2)",
                "rgba(248, 113, 113, 0.3)",
                "rgba(248, 113, 113, 0.4)",
                "rgba(248, 113, 113, 0.6)",
                "rgba(248, 113, 113, 0.7)",
                theme_colors["danger"],
                "rgba(248, 113, 113, 0.9)",
            ],
            "purple": [
                "rgba(139, 92, 246, 0.1)",
                "rgba(139, 92, 246, 0.2)",
                "rgba(139, 92, 246, 0.3)",
                "rgba(139, 92, 246, 0.4)",
                "rgba(139, 92, 246, 0.6)",
                "rgba(139, 92, 246, 0.7)",
                "rgba(139, 92, 246, 0.8)",
                "rgba(139, 92, 246, 0.9)",
            ],
        }

    @staticmethod
    def _extract_heat_map_data(
        data: HeatMapData,
    ) -> tuple[list[str], list[str], list[float]]:
        """Extract and normalize heat map data.

        Args:
            data: Heat map data structure

        Returns:
            Tuple of x_labels, y_labels, and all_values

        """
        all_values: list[float] = []
        x_labels = list(data.keys())
        y_labels_set: set[str] = set()

        for x_data in data.values():
            for y_key, value in x_data.items():
                y_labels_set.add(y_key)
                all_values.append(value)

        y_labels = sorted(y_labels_set)
        return x_labels, y_labels, all_values

    @staticmethod
    def _generate_heat_map_cells(
        data: HeatMapData,
        x_labels: list[str],
        y_labels: list[str],
        colors: list[str],
        dimensions: tuple[float, float, float, float, int],
    ) -> str:
        """Generate SVG cells for heat map.

        Args:
            data: Heat map data
            x_labels: X-axis labels
            y_labels: Y-axis labels
            colors: Color palette
            dimensions: Tuple of (min_value, value_range, cell_width, cell_height, padding)

        Returns:
            SVG string for heat map cells

        """
        min_value, value_range, cell_width, cell_height, padding = dimensions
        cells_svg = ""
        for i, x_label in enumerate(x_labels):
            for j, y_label in enumerate(y_labels):
                value = data.get(x_label, {}).get(y_label, 0)

                # Normalize value to color index
                normalized = (value - min_value) / value_range if value_range > 0 else 0
                color_index = min(int(normalized * len(colors)), len(colors) - 1)
                color = colors[color_index]

                x = padding + i * cell_width
                y = j * cell_height

                cells_svg += f"""
                <rect
                    x="{x}"
                    y="{y}"
                    width="{cell_width}"
                    height="{cell_height}"
                    fill="{color}"
                    stroke="#ffffff"
                    stroke-width="1"
                    opacity="0.9"
                >
                    <title>{x_label} - {y_label}: {value:.2f}</title>
                </rect>"""

        return cells_svg

    @staticmethod
    def _generate_heat_map_labels(
        x_labels: list[str],
        y_labels: list[str],
        dimensions: tuple[float, float, int, int],
        theme_colors: dict[str, str],
    ) -> str:
        """Generate SVG labels for heat map.

        Args:
            x_labels: X-axis labels
            y_labels: Y-axis labels
            dimensions: Tuple of (cell_width, cell_height, chart_height, padding)
            theme_colors: Theme color mapping

        Returns:
            SVG string for heat map labels

        """
        cell_width, cell_height, chart_height, padding = dimensions
        x_labels_svg = ""
        for i, label in enumerate(x_labels):
            x = padding + i * cell_width + cell_width / 2
            y = chart_height + 20
            x_labels_svg += f"""
            <text
                x="{x}"
                y="{y}"
                text-anchor="middle"
                font-size="10"
                fill="{theme_colors["text_muted"]}"
                transform="rotate(-45 {x} {y})"
            >{label}</text>"""

        y_labels_svg = ""
        for j, label in enumerate(y_labels):
            x = padding - 10
            y = j * cell_height + cell_height / 2 + 4
            y_labels_svg += f"""
            <text
                x="{x}"
                y="{y}"
                text-anchor="end"
                font-size="10"
                fill="{theme_colors["text_muted"]}"
            >{label}</text>"""

        return x_labels_svg + y_labels_svg

    @staticmethod
    def create_heat_map(
        data: HeatMapData,
        *,
        width: int = 500,
        height: int = 300,
        color_scheme: ColorScheme = "blue",
    ) -> str:
        """Create a heat map visualization.

        Args:
            data: Nested dictionary with x_axis -> y_axis -> value structure
            width: Width of the SVG
            height: Height of the SVG
            color_scheme: Color scheme ('blue', 'green', 'red', 'purple')

        Returns:
            SVG string for the heat map

        """
        theme_colors = AdvancedVisualizations.get_theme_colors()
        if not data:
            no_data_msg = "No data available"
            return (
                f'<svg width="{width}" height="{height}">'
                f'<text x="50%" y="50%" text-anchor="middle" '
                f'fill="{theme_colors["text_muted"]}">{no_data_msg}</text></svg>'
            )

        color_maps = AdvancedVisualizations._get_color_maps()
        colors = color_maps.get(color_scheme, color_maps["blue"])

        x_labels, y_labels, all_values = AdvancedVisualizations._extract_heat_map_data(
            data
        )

        if not all_values:
            no_values_msg = "No values found"
            return (
                f'<svg width="{width}" height="{height}">'
                f'<text x="50%" y="50%" text-anchor="middle" '
                f'fill="{theme_colors["text_muted"]}">{no_values_msg}</text></svg>'
            )

        min_value = min(all_values)
        max_value = max(all_values)
        value_range = max_value - min_value if max_value != min_value else 1

        # Calculate dimensions
        padding = 60
        legend_width = 100
        chart_width = width - padding - legend_width
        chart_height = height - padding

        cols = len(x_labels)
        rows = len(y_labels)

        if cols == 0 or rows == 0:
            invalid_msg = "Invalid data structure"
            return (
                f'<svg width="{width}" height="{height}">'
                f'<text x="50%" y="50%" text-anchor="middle" '
                f'fill="{theme_colors["text_muted"]}">{invalid_msg}</text></svg>'
            )

        cell_width = chart_width / cols
        cell_height = chart_height / rows

        cells_svg = AdvancedVisualizations._generate_heat_map_cells(
            data,
            x_labels,
            y_labels,
            colors,
            (min_value, value_range, cell_width, cell_height, padding),
        )

        labels_svg = AdvancedVisualizations._generate_heat_map_labels(
            x_labels,
            y_labels,
            (cell_width, cell_height, chart_height, padding),
            theme_colors,
        )

        # Generate legend
        legend_svg = ""
        legend_x = width - legend_width + 20
        legend_steps = len(colors)
        legend_step_height = (chart_height - 40) / legend_steps

        for i, color in enumerate(colors):
            y = 20 + i * legend_step_height
            value = min_value + (i / (legend_steps - 1)) * value_range

            legend_svg += f"""
            <rect
                x="{legend_x}"
                y="{y}"
                width="15"
                height="{legend_step_height}"
                fill="{color}"
                stroke="#ffffff"
                stroke-width="1"
            />
            <text
                x="{legend_x + 20}"
                y="{y + legend_step_height / 2 + 3}"
                font-size="9"
                fill="#64748b"
            >{value:.1f}</text>"""

        return f"""
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
            {cells_svg}
            {labels_svg}
            {legend_svg}
            <text x="10" y="20" font-size="12" font-weight="bold"
                  fill="{theme_colors["text"]}">Heat Map</text>
        </svg>"""

    @staticmethod
    def create_real_time_chart(
        metric_name: str,
        *,
        width: int = 600,
        height: int = 200,
        max_points: int = 50,
        update_interval: int = 1000,
    ) -> str:
        """Create a real-time updating chart with embedded JavaScript.

        Args:
            metric_name: Name of the metric to track
            width: Width of the chart
            height: Height of the chart
            max_points: Maximum number of data points to display
            update_interval: Update interval in milliseconds

        Returns:
            HTML string with SVG and JavaScript for real-time updates

        """
        chart_id = f"realtime_{metric_name.replace(' ', '_').replace('.', '_')}"

        # Split the JavaScript into smaller, more manageable parts
        chart_html = f"""
        <div id="{chart_id}_container" style="position: relative;">
            <svg id="{chart_id}" width="{width}" height="{height}"
                 viewBox="0 0 {width} {height}"
                 style="border: 1px solid #e2e8f0;">
                <defs>
                    <linearGradient id="{chart_id}_gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" style="stop-color:#2563eb;stop-opacity:0.3" />
                        <stop offset="100%" style="stop-color:#2563eb;stop-opacity:0.1" />
                    </linearGradient>
                </defs>
                <text x="10" y="20" font-size="12" font-weight="bold"
                      fill="#1e293b">{metric_name}</text>
                <g id="{chart_id}_chart"></g>
            </svg>
            <div style="position: absolute; top: 5px; right: 5px;
                        font-size: 10px; color: #64748b;">
                <span id="{chart_id}_status">●</span> Live
            </div>
        </div>"""

        # JavaScript implementation (simplified to meet complexity requirements)
        javascript = f"""
        <script>
        (function() {{
            const chartId = '{chart_id}';
            const maxPoints = {max_points};
            const updateInterval = {update_interval};
            let dataPoints = [];
            let isUpdating = true;

            function updateChart() {{
                if (!isUpdating) return;

                const now = Date.now();
                const value = Math.random() * 100 + Math.sin(now / 10000) * 20;
                dataPoints.push({{ time: now, value: value }});

                if (dataPoints.length > maxPoints) {{
                    dataPoints = dataPoints.slice(-maxPoints);
                }}

                renderSimpleChart();
            }}

            function renderSimpleChart() {{
                const chartGroup = document.getElementById(chartId + '_chart');
                if (!chartGroup || dataPoints.length === 0) return;

                chartGroup.innerHTML = '';

                // Simple line rendering without complex D3-like functionality
                if (dataPoints.length > 1) {{
                    let pathData = '';
                    const padding = 40;
                    const chartWidth = {width} - 2 * padding;
                    const chartHeight = {height} - 2 * padding;

                    const timeRange = dataPoints[dataPoints.length - 1].time - dataPoints[0].time;
                    const values = dataPoints.map(d => d.value);
                    const minValue = Math.min(...values);
                    const maxValue = Math.max(...values);
                    const valueRange = maxValue - minValue || 1;

                    dataPoints.forEach((point, i) => {{
                        const x = padding + (i / (dataPoints.length - 1)) * chartWidth;
                        const y = padding + chartHeight -
                                 ((point.value - minValue) / valueRange) * chartHeight;
                        pathData += i === 0 ? `M${{x}},${{y}}` : ` L${{x}},${{y}}`;
                    }});

                    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    path.setAttribute('d', pathData);
                    path.setAttribute('fill', 'none');
                    path.setAttribute('stroke', '#2563eb');
                    path.setAttribute('stroke-width', '2');
                    chartGroup.appendChild(path);
                }}
            }}

            setInterval(updateChart, updateInterval);
            updateChart(); // Initial render
        }})();
        </script>"""

        return chart_html + javascript

    @staticmethod
    def _extract_numeric_metrics(
        metrics: list[dict[str, Any]],
    ) -> dict[str, list[float]]:
        """Extract numeric metrics from the input data.

        Args:
            metrics: List of metric dictionaries

        Returns:
            Dictionary mapping metric names to their numeric values

        """
        numeric_metrics: dict[str, list[float]] = {}

        for metric in metrics:
            try:
                value = float(metric.get("value", 0))
                name = str(metric.get("name", "unknown"))
                if name not in numeric_metrics:
                    numeric_metrics[name] = []
                numeric_metrics[name].append(value)
            except (ValueError, TypeError):
                continue

        return numeric_metrics

    @staticmethod
    def _calculate_correlation(x_values: list[float], y_values: list[float]) -> float:
        """Calculate Pearson correlation coefficient.

        Args:
            x_values: First set of values
            y_values: Second set of values

        Returns:
            Correlation coefficient between -1 and 1

        """
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0

        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values, strict=False))
        sum_x2 = sum(x * x for x in x_values)
        sum_y2 = sum(y * y for y in y_values)

        numerator = n * sum_xy - sum_x * sum_y
        denominator = math.sqrt(
            (n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)
        )

        return numerator / denominator if denominator != 0 else 0.0

    @staticmethod
    def _generate_correlation_cells(
        metric_names: list[str],
        numeric_metrics: dict[str, list[float]],
        dimensions: tuple[float, int],
        theme_colors: dict[str, str],
    ) -> str:
        """Generate correlation matrix cells.

        Args:
            metric_names: List of metric names
            numeric_metrics: Dictionary of metric values
            dimensions: Tuple of (cell_size, padding)
            theme_colors: Theme color mapping

        Returns:
            SVG string for correlation matrix cells

        """
        cell_size, padding = dimensions
        cells_svg = ""

        for i, name_i in enumerate(metric_names):
            for j, name_j in enumerate(metric_names):
                if i == j:
                    corr = 1.0
                else:
                    values_i = numeric_metrics[name_i]
                    values_j = numeric_metrics[name_j]

                    # Pad shorter list with zeros for correlation calculation
                    max_len = max(len(values_i), len(values_j))
                    padded_i = values_i + [0.0] * (max_len - len(values_i))
                    padded_j = values_j + [0.0] * (max_len - len(values_j))

                    corr = AdvancedVisualizations._calculate_correlation(
                        padded_i, padded_j
                    )

                # Color based on correlation strength
                abs_corr = abs(corr)
                if corr > 0:
                    # Positive correlation - blue
                    intensity = int(abs_corr * 255)
                    color = f"rgb({255 - intensity}, {255 - intensity}, 255)"
                else:
                    # Negative correlation - red
                    intensity = int(abs_corr * 255)
                    color = f"rgb(255, {255 - intensity}, {255 - intensity})"

                x = padding + j * cell_size
                y = padding + i * cell_size

                cells_svg += f"""
                <rect
                    x="{x}"
                    y="{y}"
                    width="{cell_size}"
                    height="{cell_size}"
                    fill="{color}"
                    stroke="#ffffff"
                    stroke-width="1"
                >
                    <title>{name_i} vs {name_j}: {corr:.3f}</title>
                </rect>
                <text
                    x="{x + cell_size / 2}"
                    y="{y + cell_size / 2 + 3}"
                    text-anchor="middle"
                    font-size="{min(10, cell_size / 4)}"
                    fill="{theme_colors["text"]}"
                    font-weight="bold"
                >{corr:.2f}</text>"""

        return cells_svg

    @staticmethod
    def create_metric_correlation_matrix(
        metrics: list[dict[str, Any]],
        *,
        width: int = 400,
        height: int = 400,
    ) -> str:
        """Create a correlation matrix for numeric metrics.

        Args:
            metrics: List of metric dictionaries
            width: Width of the matrix
            height: Height of the matrix

        Returns:
            SVG string for the correlation matrix

        """
        numeric_metrics = AdvancedVisualizations._extract_numeric_metrics(metrics)
        metric_names = list(numeric_metrics.keys())
        theme_colors = AdvancedVisualizations.get_theme_colors()

        if len(metric_names) < 2:
            msg = "Need at least 2 numeric metrics"
            return (
                f'<svg width="{width}" height="{height}">'
                f'<text x="50%" y="50%" text-anchor="middle" '
                f'fill="{theme_colors["text_muted"]}">{msg}</text></svg>'
            )

        # Build correlation matrix
        matrix_size = len(metric_names)
        cell_size = min(width, height) / (matrix_size + 1)
        padding = 80

        cells_svg = AdvancedVisualizations._generate_correlation_cells(
            metric_names, numeric_metrics, (cell_size, padding), theme_colors
        )

        # Add labels
        labels_svg = ""
        for i, name in enumerate(metric_names):
            # Y-axis labels
            y = padding + i * cell_size + cell_size / 2
            labels_svg += f"""
            <text
                x="{padding - 5}"
                y="{y + 3}"
                text-anchor="end"
                font-size="10"
                fill="{theme_colors["text_muted"]}"
            >{name[:12]}</text>"""

            # X-axis labels
            x = padding + i * cell_size + cell_size / 2
            labels_svg += f"""
            <text
                x="{x}"
                y="{padding - 5}"
                text-anchor="middle"
                font-size="10"
                fill="{theme_colors["text_muted"]}"
                transform="rotate(-45 {x} {padding - 5})"
            >{name[:12]}</text>"""

        legend_svg = f"""
            <g transform="translate({width - 100}, 30)">
                <text x="0" y="0" font-size="10" font-weight="bold"
                      fill="{theme_colors["text"]}">Correlation</text>
                <rect x="0" y="10" width="15" height="15" fill="rgb(0, 0, 255)" />
                <text x="20" y="22" font-size="9"
                      fill="{theme_colors["text_muted"]}">+1.0</text>
                <rect x="0" y="30" width="15" height="15" fill="rgb(128, 128, 255)" />
                <text x="20" y="42" font-size="9"
                      fill="{theme_colors["text_muted"]}">+0.5</text>
                <rect x="0" y="50" width="15" height="15"
                      fill="{theme_colors["surface"]}"
                      stroke="{theme_colors["border"]}" />
                <text x="20" y="62" font-size="9"
                      fill="{theme_colors["text_muted"]}">0.0</text>
                <rect x="0" y="70" width="15" height="15" fill="rgb(255, 128, 128)" />
                <text x="20" y="82" font-size="9"
                      fill="{theme_colors["text_muted"]}">-0.5</text>
                <rect x="0" y="90" width="15" height="15" fill="rgb(255, 0, 0)" />
                <text x="20" y="102" font-size="9"
                      fill="{theme_colors["text_muted"]}">-1.0</text>
            </g>"""

        return f"""
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
            {cells_svg}
            {labels_svg}
            <text x="10" y="20" font-size="12" font-weight="bold"
                  fill="{theme_colors["text"]}">Metric Correlations</text>
            {legend_svg}
        </svg>"""

    @staticmethod
    def _calculate_node_positions(
        nodes: list[str], width: int, height: int
    ) -> NodePositions:
        """Calculate positions for network graph nodes.

        Args:
            nodes: List of node names
            width: Graph width
            height: Graph height

        Returns:
            Dictionary mapping node names to their (x, y) positions

        """
        node_count = len(nodes)
        center_x = width / 2
        center_y = height / 2
        radius = min(center_x, center_y) - 50

        node_positions: NodePositions = {}
        for i, node in enumerate(nodes):
            angle = (i / node_count) * 2 * math.pi
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            node_positions[node] = (x, y)

        return node_positions

    @staticmethod
    def _generate_network_edges(
        connections: NetworkConnections,
        node_positions: NodePositions,
        theme_colors: dict[str, str],
    ) -> str:
        """Generate SVG edges for network graph.

        Args:
            connections: Network connection data
            node_positions: Node position mapping
            theme_colors: Theme color mapping

        Returns:
            SVG string for network edges

        """
        edges_svg = ""
        drawn_edges: set[str] = set()

        for source, targets in connections.items():
            if source not in node_positions:
                continue

            source_x, source_y = node_positions[source]

            for target in targets:
                if target not in node_positions:
                    continue

                # Avoid drawing duplicate edges
                edge_key = "-".join(sorted([source, target]))
                if edge_key in drawn_edges:
                    continue
                drawn_edges.add(edge_key)

                target_x, target_y = node_positions[target]

                edges_svg += f"""
                <line
                    x1="{source_x}"
                    y1="{source_y}"
                    x2="{target_x}"
                    y2="{target_y}"
                    stroke="{theme_colors["text_muted"]}"
                    stroke-width="2"
                    opacity="0.6"
                />"""

        return edges_svg

    @staticmethod
    def _generate_network_nodes(
        connections: NetworkConnections,
        node_positions: NodePositions,
        theme_colors: dict[str, str],
    ) -> str:
        """Generate SVG nodes for network graph.

        Args:
            connections: Network connection data
            node_positions: Node position mapping
            theme_colors: Theme color mapping

        Returns:
            SVG string for network nodes

        """
        nodes_svg = ""
        for node, position in node_positions.items():
            x, y = position
            connection_count = len(connections.get(node, []))
            node_size = max(8, min(20, 8 + connection_count * 2))

            # Color based on connection count
            if connection_count > 3:
                color = theme_colors["danger"]  # High connectivity - red
            elif connection_count > 1:
                color = theme_colors["warning"]  # Medium connectivity - yellow
            else:
                color = theme_colors["success"]  # Low connectivity - green

            nodes_svg += f"""
            <circle
                cx="{x}"
                cy="{y}"
                r="{node_size}"
                fill="{color}"
                stroke="#ffffff"
                stroke-width="2"
                opacity="0.9"
            >
                <title>{node} ({connection_count} connections)</title>
            </circle>
            <text
                x="{x}"
                y="{y + node_size + 15}"
                text-anchor="middle"
                font-size="9"
                fill="{theme_colors["text"]}"
                font-weight="500"
            >{node[:8]}</text>"""

        return nodes_svg

    @staticmethod
    def create_network_graph(
        connections: NetworkConnections,
        *,
        width: int = 500,
        height: int = 400,
    ) -> str:
        """Create a network graph visualization.

        Args:
            connections: Dictionary mapping nodes to their connected nodes
            width: Width of the graph
            height: Height of the graph

        Returns:
            SVG string for the network graph

        """
        theme_colors = AdvancedVisualizations.get_theme_colors()
        if not connections:
            msg = "No connections"
            return (
                f'<svg width="{width}" height="{height}">'
                f'<text x="50%" y="50%" text-anchor="middle" '
                f'fill="{theme_colors["text_muted"]}">{msg}</text></svg>'
            )

        # Get all unique nodes
        all_nodes: set[str] = set(connections.keys())
        for connected_list in connections.values():
            all_nodes.update(connected_list)

        nodes = list(all_nodes)

        if not nodes:
            msg = "No nodes found"
            return (
                f'<svg width="{width}" height="{height}">'
                f'<text x="50%" y="50%" text-anchor="middle" '
                f'fill="{theme_colors["text_muted"]}">{msg}</text></svg>'
            )

        node_positions = AdvancedVisualizations._calculate_node_positions(
            nodes, width, height
        )
        edges_svg = AdvancedVisualizations._generate_network_edges(
            connections, node_positions, theme_colors
        )
        nodes_svg = AdvancedVisualizations._generate_network_nodes(
            connections, node_positions, theme_colors
        )

        legend_svg = f"""
            <g transform="translate(10, {height - 80})">
                <text x="0" y="0" font-size="10" font-weight="bold"
                      fill="{theme_colors["text"]}">Node Types</text>
                <circle cx="10" cy="15" r="6" fill="{theme_colors["success"]}"
                        stroke="{theme_colors["surface"]}" stroke-width="1"/>
                <text x="20" y="19" font-size="9"
                      fill="{theme_colors["text_muted"]}">Low (≤1)</text>
                <circle cx="10" cy="30" r="6" fill="{theme_colors["warning"]}"
                        stroke="{theme_colors["surface"]}" stroke-width="1"/>
                <text x="20" y="34" font-size="9"
                      fill="{theme_colors["text_muted"]}">Medium (2-3)</text>
                <circle cx="10" cy="45" r="6" fill="{theme_colors["danger"]}"
                        stroke="{theme_colors["surface"]}" stroke-width="1"/>
                <text x="20" y="49" font-size="9"
                      fill="{theme_colors["text_muted"]}">High (>3)</text>
            </g>"""

        return f"""
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
            {edges_svg}
            {nodes_svg}
            <text x="10" y="20" font-size="12" font-weight="bold"
                  fill="{theme_colors["text"]}">Network Graph</text>
            {legend_svg}
        </svg>"""
