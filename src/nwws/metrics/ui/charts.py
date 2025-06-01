# pyright: strict
"""Chart utilities for generating SVG-based visualizations."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence


class ChartFactory:
    """Factory for creating various chart types using SVG."""

    @staticmethod
    def get_theme_colors() -> dict[str, str]:
        """Get theme-aware colors for charts.

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
    def create_gauge_chart(  # noqa: PLR0913
        value: float,
        max_value: float = 100,
        *,
        width: int = 120,
        height: int = 120,
        color: str | None = None,
        background_color: str | None = None,
        stroke_width: int = 8,
    ) -> str:
        """Create a circular gauge chart.

        Args:
            value: Current value to display
            max_value: Maximum value for the gauge
            width: Width of the SVG
            height: Height of the SVG
            color: Color for the progress arc (None for theme default)
            background_color: Color for the background arc (None for theme default)
            stroke_width: Width of the arc stroke

        Returns:
            SVG string for the gauge chart

        """
        theme_colors = ChartFactory.get_theme_colors()
        if color is None:
            color = theme_colors["primary"]
        if background_color is None:
            background_color = theme_colors["border"]
        center_x = width // 2
        center_y = height // 2
        radius = min(center_x, center_y) - stroke_width

        # Calculate percentage
        percentage = min(value / max_value, 1.0) if max_value > 0 else 0

        # Calculate arc path
        circumference = 2 * math.pi * radius
        dash_array = circumference
        dash_offset = circumference * (1 - percentage)

        return f"""
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
            <circle
                cx="{center_x}"
                cy="{center_y}"
                r="{radius}"
                fill="none"
                stroke="{background_color}"
                stroke-width="{stroke_width}"
            />
            <circle
                cx="{center_x}"
                cy="{center_y}"
                r="{radius}"
                fill="none"
                stroke="{color}"
                stroke-width="{stroke_width}"
                stroke-linecap="round"
                stroke-dasharray="{dash_array}"
                stroke-dashoffset="{dash_offset}"
                transform="rotate(-90 {center_x} {center_y})"
            />
            <text
                x="{center_x}"
                y="{center_y - 5}"
                text-anchor="middle"
                font-size="16"
                font-weight="bold"
                fill="{theme_colors["text"]}"
            >{value:.1f}</text>
            <text
                x="{center_x}"
                y="{center_y + 15}"
                text-anchor="middle"
                font-size="12"
                fill="{theme_colors["text_muted"]}"
            >/ {max_value}</text>
        </svg>"""

    @staticmethod
    def create_line_chart(  # noqa: PLR0913
        data_points: Sequence[tuple[float, float]],
        *,
        width: int = 400,
        height: int = 200,
        color: str | None = None,
        stroke_width: int = 2,
        show_points: bool = True,
        show_area: bool = False,
        area_opacity: float = 0.2,
    ) -> str:
        """Create a line chart with optional area fill.

        Args:
            data_points: List of (x, y) coordinate tuples
            width: Width of the SVG
            height: Height of the SVG
            color: Color for the line (None for theme default)
            stroke_width: Width of the line
            show_points: Whether to show data points
            show_area: Whether to fill area under the line
            area_opacity: Opacity for the area fill

        Returns:
            SVG string for the line chart

        """
        theme_colors = ChartFactory.get_theme_colors()
        if color is None:
            color = theme_colors["primary"]

        if not data_points:
            return (
                f'<svg width="{width}" height="{height}">'
                '<text x="50%" y="50%" text-anchor="middle" '
                f'fill="{theme_colors["text_muted"]}">No data</text></svg>'
            )

        # Find data bounds
        x_values = [point[0] for point in data_points]
        y_values = [point[1] for point in data_points]

        x_min, x_max = min(x_values), max(x_values)
        y_min, y_max = min(y_values), max(y_values)

        # Add padding
        padding = 20
        chart_width = width - 2 * padding
        chart_height = height - 2 * padding

        # Scale points to chart area
        def scale_point(x: float, y: float) -> tuple[float, float]:
            if x_max == x_min:
                scaled_x = padding + chart_width / 2
            else:
                scaled_x = padding + (x - x_min) / (x_max - x_min) * chart_width

            if y_max == y_min:
                scaled_y = padding + chart_height / 2
            else:
                scaled_y = padding + (1 - (y - y_min) / (y_max - y_min)) * chart_height

            return scaled_x, scaled_y

        scaled_points = [scale_point(x, y) for x, y in data_points]

        # Create path string
        path_data = f"M {scaled_points[0][0]} {scaled_points[0][1]}"
        for x, y in scaled_points[1:]:
            path_data += f" L {x} {y}"

        # Create area path if needed
        area_path = ""
        if show_area:
            area_data = (
                path_data
                + f" L {scaled_points[-1][0]} {height - padding} L {scaled_points[0][0]} {height - padding} Z"
            )
            area_path = (
                f'<path d="{area_data}" fill="{color}" opacity="{area_opacity}" />'
            )

        # Create points if needed
        points_svg = ""
        if show_points:
            points_svg = "".join(
                [
                    f'<circle cx="{x}" cy="{y}" r="3" fill="{color}" />'
                    for x, y in scaled_points
                ]
            )

        return f"""
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
            <defs>
                <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" style="stop-color:{color};stop-opacity:1" />
                    <stop offset="100%" style="stop-color:{color};stop-opacity:0.7" />
                </linearGradient>
            </defs>
            {area_path}
            <path
                d="{path_data}"
                fill="none"
                stroke="url(#lineGradient)"
                stroke-width="{stroke_width}"
                stroke-linecap="round"
                stroke-linejoin="round"
            />
            {points_svg}
        </svg>"""

    @staticmethod
    def create_bar_chart(  # noqa: PLR0913
        data: dict[str, float],
        *,
        width: int = 400,
        height: int = 300,
        color: str | None = None,
        show_values: bool = True,
        horizontal: bool = False,
    ) -> str:
        """Create a bar chart.

        Args:
            data: Dictionary mapping labels to values
            width: Width of the SVG
            height: Height of the SVG
            color: Color for the bars (None for theme default)
            show_values: Whether to show value labels
            horizontal: Whether to create horizontal bars

        Returns:
            SVG string for the bar chart

        """
        theme_colors = ChartFactory.get_theme_colors()
        if color is None:
            color = theme_colors["primary"]

        if not data:
            return (
                f'<svg width="{width}" height="{height}">'
                '<text x="50%" y="50%" text-anchor="middle" '
                f'fill="{theme_colors["text_muted"]}">No data</text></svg>'
            )

        labels = list(data.keys())
        values = list(data.values())
        max_value = max(values) if values else 1

        padding = 40
        chart_width = width - 2 * padding
        chart_height = height - 2 * padding

        if horizontal:
            return ChartFactory._create_horizontal_bars(
                labels,
                values,
                max_value,
                width,
                height,
                chart_width,
                chart_height,
                padding,
                color,
                show_values,
            )
        return ChartFactory._create_vertical_bars(
            labels,
            values,
            max_value,
            width,
            height,
            chart_width,
            chart_height,
            padding,
            color,
            show_values,
        )

    @staticmethod
    def _create_vertical_bars(  # noqa: PLR0913
        labels: list[str],
        values: list[float],
        max_value: float,
        width: int,
        height: int,
        chart_width: int,
        chart_height: int,
        padding: int,
        color: str,
        show_values: bool,  # noqa: FBT001
    ) -> str:
        """Create vertical bars for bar chart."""
        theme_colors = ChartFactory.get_theme_colors()
        bar_width = chart_width / len(labels) * 0.8
        bar_spacing = chart_width / len(labels)

        bars_svg = ""
        labels_svg = ""
        values_svg = ""

        for i, (label, value) in enumerate(zip(labels, values, strict=True)):
            bar_height = (value / max_value) * chart_height if max_value > 0 else 0
            x = padding + i * bar_spacing + (bar_spacing - bar_width) / 2
            y = height - padding - bar_height

            # Create bar with gradient
            bars_svg += f"""
            <rect
                x="{x}"
                y="{y}"
                width="{bar_width}"
                height="{bar_height}"
                fill="{color}"
                opacity="0.8"
                rx="4"
            />"""

            # Add label
            labels_svg += f"""
            <text
                x="{x + bar_width / 2}"
                y="{height - padding + 20}"
                text-anchor="middle"
                font-size="12"
                fill="{theme_colors["text_muted"]}"
            >{label}</text>"""

            # Add value if requested
            if show_values:
                values_svg += f"""
                <text
                    x="{x + bar_width / 2}"
                    y="{y - 5}"
                    text-anchor="middle"
                    font-size="11"
                    font-weight="bold"
                    fill="{theme_colors["text"]}"
                >{value:.1f}</text>"""

        return f"""
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
            {bars_svg}
            {labels_svg}
            {values_svg}
        </svg>"""

    @staticmethod
    def _create_horizontal_bars(  # noqa: PLR0913
        labels: list[str],
        values: list[float],
        max_value: float,
        width: int,
        height: int,
        chart_width: int,
        chart_height: int,
        padding: int,
        color: str,
        show_values: bool,  # noqa: FBT001
    ) -> str:
        """Create horizontal bars for bar chart."""
        theme_colors = ChartFactory.get_theme_colors()
        bar_height = chart_height / len(labels) * 0.8
        bar_spacing = chart_height / len(labels)

        bars_svg = ""
        labels_svg = ""
        values_svg = ""

        for i, (label, value) in enumerate(zip(labels, values, strict=True)):
            bar_width = (value / max_value) * chart_width if max_value > 0 else 0
            x = padding
            y = padding + i * bar_spacing + (bar_spacing - bar_height) / 2

            # Create bar
            bars_svg += f"""
            <rect
                x="{x}"
                y="{y}"
                width="{bar_width}"
                height="{bar_height}"
                fill="{color}"
                opacity="0.8"
                rx="4"
            />"""

            # Add label
            labels_svg += f"""
            <text
                x="{padding - 10}"
                y="{y + bar_height / 2 + 4}"
                text-anchor="end"
                font-size="12"
                fill="{theme_colors["text_muted"]}"
            >{label}</text>"""

            # Add value if requested
            if show_values:
                values_svg += f"""
                <text
                    x="{x + bar_width + 5}"
                    y="{y + bar_height / 2 + 4}"
                    text-anchor="start"
                    font-size="11"
                    font-weight="bold"
                    fill="{theme_colors["text"]}"
                >{value:.1f}</text>"""

        return f"""
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
            {bars_svg}
            {labels_svg}
            {values_svg}
        </svg>"""

    @staticmethod
    def create_donut_chart(  # noqa: PLR0913
        data: dict[str, float],
        *,
        width: int = 300,
        height: int = 300,
        colors: list[str] | None = None,
        inner_radius: float = 0.6,
        show_labels: bool = True,
        show_percentages: bool = True,
    ) -> str:
        """Create a donut chart.

        Args:
            data: Dictionary mapping labels to values
            width: Width of the SVG
            height: Height of the SVG
            colors: List of colors for the segments
            inner_radius: Inner radius as fraction of outer radius
            show_labels: Whether to show segment labels
            show_percentages: Whether to show percentages

        Returns:
            SVG string for the donut chart

        """
        theme_colors = ChartFactory.get_theme_colors()
        if not data:
            return (
                f'<svg width="{width}" height="{height}">'
                '<text x="50%" y="50%" text-anchor="middle" '
                f'fill="{theme_colors["text_muted"]}">No data</text></svg>'
            )

        if colors is None:
            colors = [
                theme_colors["primary"],
                theme_colors["success"],
                theme_colors["warning"],
                theme_colors["danger"],
                theme_colors["info"],
                "#8b5cf6",
                "#f97316",
                "#ec4899",
            ]

        total = sum(data.values())
        if total == 0:
            return (
                f'<svg width="{width}" height="{height}">'
                '<text x="50%" y="50%" text-anchor="middle" '
                f'fill="{theme_colors["text_muted"]}">No data</text></svg>'
            )
        center_x = width / 2
        center_y = height / 2
        outer_radius = min(center_x, center_y) - 20
        inner_radius_px = outer_radius * inner_radius

        segments_svg = ""
        labels_svg = ""
        current_angle = -math.pi / 2  # Start from top

        for i, (label, value) in enumerate(data.items()):
            percentage = value / total
            slice_angle = percentage * 2 * math.pi
            end_angle = current_angle + slice_angle

            # Calculate arc path
            x1 = center_x + outer_radius * math.cos(current_angle)
            y1 = center_y + outer_radius * math.sin(current_angle)
            x2 = center_x + outer_radius * math.cos(end_angle)
            y2 = center_y + outer_radius * math.sin(end_angle)

            inner_x1 = center_x + inner_radius_px * math.cos(current_angle)
            inner_y1 = center_y + inner_radius_px * math.sin(current_angle)
            inner_x2 = center_x + inner_radius_px * math.cos(end_angle)
            inner_y2 = center_y + inner_radius_px * math.sin(end_angle)

            large_arc = 1 if slice_angle > math.pi else 0
            color = colors[i % len(colors)]

            # Create segment path
            path = f"""M {x1} {y1}
                     A {outer_radius} {outer_radius} 0 {large_arc} 1 {x2} {y2}
                     L {inner_x2} {inner_y2}
                     A {inner_radius_px} {inner_radius_px} 0 {large_arc} 0 {inner_x1} {inner_y1}
                     Z"""

            segments_svg += f'<path d="{path}" fill="{color}" opacity="0.9" />'

            # Add labels if requested
            if show_labels:
                label_angle = current_angle + slice_angle / 2
                label_radius = outer_radius + 15
                label_x = center_x + label_radius * math.cos(label_angle)
                label_y = center_y + label_radius * math.sin(label_angle)

                text = f"{label}"
                if show_percentages:
                    text += f" ({percentage * 100:.1f}%)"

                labels_svg += f"""
                <text
                    x="{label_x}"
                    y="{label_y}"
                    text-anchor="middle"
                    font-size="11"
                    font-weight="500"
                    fill="{theme_colors["text"]}"
                >{text}</text>"""

            current_angle = end_angle

        # Center text
        center_text = f"""
        <text
            x="{center_x}"
            y="{center_y - 5}"
            text-anchor="middle"
            font-size="18"
            font-weight="bold"
            fill="{theme_colors["text"]}"
        >{total:.0f}</text>
        <text
            x="{center_x}"
            y="{center_y + 15}"
            text-anchor="middle"
            font-size="12"
            fill="{theme_colors["text_muted"]}"
        >Total</text>"""

        return f"""
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
            {segments_svg}
            {center_text}
            {labels_svg}
        </svg>"""

    @staticmethod
    def create_sparkline(  # noqa: PLR0913
        data_points: Sequence[float],
        *,
        width: int = 100,
        height: int = 30,
        color: str | None = None,
        stroke_width: int = 2,
        show_area: bool = True,
        area_opacity: float = 0.2,
    ) -> str:
        """Create a small sparkline chart.

        Args:
            data_points: List of numeric values
            width: Width of the SVG
            height: Height of the SVG
            color: Color for the line (None for theme default)
            stroke_width: Width of the line
            show_area: Whether to fill area under the line
            area_opacity: Opacity for the area fill

        Returns:
            SVG string for the sparkline

        """
        theme_colors = ChartFactory.get_theme_colors()
        if color is None:
            color = theme_colors["primary"]

        if not data_points:
            return f'<svg width="{width}" height="{height}"></svg>'

        if len(data_points) == 1:
            y = height / 2
            return f"""
            <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
                <line x1="0" y1="{y}" x2="{width}" y2="{y}" stroke="{color}" stroke-width="{stroke_width}" />
            </svg>"""

        y_min, y_max = min(data_points), max(data_points)
        y_range = y_max - y_min if y_max != y_min else 1

        # Calculate points
        points: list[tuple[float, float]] = []
        for i, value in enumerate(data_points):
            x = (i / (len(data_points) - 1)) * width
            y = height - ((value - y_min) / y_range) * height
            points.append((x, y))

        # Create path
        path_data = f"M {points[0][0]} {points[0][1]}"
        for x, y in points[1:]:
            path_data += f" L {x} {y}"

        # Create area path if needed
        area_path = ""
        if show_area:
            area_data = (
                path_data + f" L {points[-1][0]} {height} L {points[0][0]} {height} Z"
            )
            area_path = (
                f'<path d="{area_data}" fill="{color}" opacity="{area_opacity}" />'
            )

        return f"""
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
            {area_path}
            <path
                d="{path_data}"
                fill="none"
                stroke="{color}"
                stroke-width="{stroke_width}"
                stroke-linecap="round"
                stroke-linejoin="round"
            />
        </svg>"""

    @staticmethod
    def create_status_indicator(
        status: str,
        *,
        size: int = 20,
        animate: bool = True,
    ) -> str:
        """Create a status indicator with optional animation.

        Args:
            status: Status string ('healthy', 'warning', 'error', etc.)
            size: Size of the indicator
            animate: Whether to add pulse animation

        Returns:
            SVG string for the status indicator

        """
        theme_colors = ChartFactory.get_theme_colors()
        color_map = {
            "healthy": theme_colors["success"],
            "warning": theme_colors["warning"],
            "error": theme_colors["danger"],
            "unknown": theme_colors["text_muted"],
        }

        color = color_map.get(status.lower(), theme_colors["text_muted"])
        animation = ""

        if animate:
            animation = """
            <animate attributeName="opacity"
                     values="1;0.5;1"
                     dur="2s"
                     repeatCount="indefinite"/>"""

        return f"""
        <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
            <circle
                cx="{size / 2}"
                cy="{size / 2}"
                r="{size / 3}"
                fill="{color}"
            >{animation}</circle>
        </svg>"""


class ChartDataProcessor:
    """Utility class for processing data for charts."""

    @staticmethod
    def aggregate_by_type(metrics: list[dict[str, Any]]) -> dict[str, int]:
        """Aggregate metrics by type for pie/donut charts.

        Args:
            metrics: List of metric dictionaries

        Returns:
            Dictionary mapping metric types to counts

        """
        type_counts: dict[str, int] = {}
        for metric in metrics:
            metric_type = metric.get("type", "unknown")
            type_counts[metric_type] = type_counts.get(metric_type, 0) + 1
        return type_counts

    @staticmethod
    def extract_time_series(
        metrics: list[dict[str, Any]],
        value_key: str = "value",
        time_key: str = "timestamp",
        max_points: int = 50,
    ) -> list[tuple[float, float]]:
        """Extract time series data from metrics.

        Args:
            metrics: List of metric dictionaries
            value_key: Key for the value field
            time_key: Key for the timestamp field
            max_points: Maximum number of data points to return

        Returns:
            List of (timestamp, value) tuples

        """
        points: list[tuple[float, float]] = []
        for metric in metrics:
            timestamp = metric.get(time_key, 0)
            value = metric.get(value_key, 0)

            try:
                timestamp_float = float(timestamp)
                value_float = float(value)
                points.append((timestamp_float, value_float))
            except (ValueError, TypeError):
                continue

        # Sort by timestamp and limit points
        points.sort(key=lambda x: x[0])
        if len(points) > max_points:
            # Sample points evenly
            step = len(points) // max_points
            points = points[::step]

        return points

    @staticmethod
    def create_histogram_data(
        values: Sequence[float],
        bins: int = 10,
    ) -> dict[str, float]:
        """Create histogram data from a list of values.

        Args:
            values: List of numeric values
            bins: Number of histogram bins

        Returns:
            Dictionary mapping bin labels to counts

        """
        if not values:
            return {}

        min_val, max_val = min(values), max(values)
        if min_val == max_val:
            return {f"{min_val:.2f}": len(values)}

        bin_width = (max_val - min_val) / bins
        bin_counts: dict[str, float] = {}

        for i in range(bins):
            bin_start = min_val + i * bin_width
            bin_end = bin_start + bin_width
            bin_label = f"{bin_start:.1f}-{bin_end:.1f}"

            count = sum(1 for value in values if bin_start <= value < bin_end)
            # Include max value in the last bin
            if i == bins - 1:
                count += sum(1 for value in values if value == max_val)

            bin_counts[bin_label] = count

        return bin_counts

    @staticmethod
    def calculate_trends(
        current_metrics: list[dict[str, Any]],
        previous_metrics: list[dict[str, Any]] | None = None,
    ) -> dict[str, str]:
        """Calculate trend indicators for metrics.

        Args:
            current_metrics: Current metric values
            previous_metrics: Previous metric values for comparison

        Returns:
            Dictionary mapping metric names to trend indicators

        """
        trends: dict[str, str] = {}

        if not previous_metrics:
            # No previous data, mark all as stable
            for metric in current_metrics:
                trends[metric.get("name", "")] = "stable"
            return trends

        # Create lookup for previous values
        prev_values = {
            metric.get("name", ""): float(metric.get("value", 0))
            for metric in previous_metrics
        }

        for metric in current_metrics:
            name = metric.get("name", "")
            current_value = float(metric.get("value", 0))
            prev_value = prev_values.get(name, current_value)

            if current_value > prev_value * 1.05:  # 5% increase threshold
                trends[name] = "up"
            elif current_value < prev_value * 0.95:  # 5% decrease threshold
                trends[name] = "down"
            else:
                trends[name] = "stable"

        return trends
