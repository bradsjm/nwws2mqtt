"""Core geohash functionality for NWS geographic data processing.

This module provides functions to parse Well-Known Text (WKT) geometry strings
from NWS products and generate optimized Geohash strings for spatial indexing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygeohash as pgh
from loguru import logger
from shapely import wkt
from shapely.geometry import Point, Polygon

if TYPE_CHECKING:
    from shapely.geometry.base import BaseGeometry


@dataclass
class GeohashConfig:
    """Configuration parameters for geohash-based geographic data processing and spatial indexing.

    This configuration class controls the critical parameters for converting NWS geographic
    data (WKT geometries) into optimized geohash tiles for efficient spatial indexing and
    MQTT topic routing. The geohash tiling process balances coverage accuracy against
    computational efficiency by generating hierarchical spatial tiles at various precision
    levels.

    The configuration directly impacts the performance characteristics of the spatial
    subscription system. Lower precision levels create fewer, larger tiles that cover
    broader geographic areas but may include irrelevant regions. Higher precision levels
    create more accurate coverage but can generate excessive numbers of small tiles,
    potentially overwhelming the MQTT topic structure and subscription management.

    The hierarchical merging feature optimizes tile count by automatically combining
    adjacent tiles at lower precision levels when their children would exceed the
    maximum tile threshold, maintaining spatial coverage while reducing computational
    overhead and topic proliferation.
    """

    max_geohash_precision: int = 6
    """Maximum precision level for geohash generation (1-12, default: 6)."""

    min_geohash_precision: int = 3
    """Minimum precision level for geohash generation (1-12, default: 3)."""

    max_tiles_per_geometry: int = 100
    """Maximum number of geohash tiles to generate per geometry (default: 100)."""

    coverage_threshold: float = 0.95
    """Minimum coverage ratio required (0.0-1.0, default: 0.95)."""

    use_hierarchical_merging: bool = True
    """Whether to use hierarchical merging to optimize tile count (default: True)."""

    def __post_init__(self) -> None:
        """Validate configuration parameters after initialization."""
        if not 1 <= self.min_geohash_precision <= 12:
            msg = (
                f"min_geohash_precision must be between 1 and 12, got {self.min_geohash_precision}"
            )
            raise ValueError(msg)

        if not 1 <= self.max_geohash_precision <= 12:
            msg = (
                f"max_geohash_precision must be between 1 and 12, got {self.max_geohash_precision}"
            )
            raise ValueError(msg)

        if self.min_geohash_precision > self.max_geohash_precision:
            msg = (
                f"min_geohash_precision ({self.min_geohash_precision}) cannot be "
                f"greater than max_geohash_precision ({self.max_geohash_precision})"
            )
            raise ValueError(msg)

        if not 1 <= self.max_tiles_per_geometry <= 10000:
            msg = (
                f"max_tiles_per_geometry must be between 1 and 10000, "
                f"got {self.max_tiles_per_geometry}"
            )
            raise ValueError(msg)

        if not 0.0 <= self.coverage_threshold <= 1.0:
            msg = f"coverage_threshold must be between 0.0 and 1.0, got {self.coverage_threshold}"
            raise ValueError(msg)


def get_geohash_topics(wkt_string: str, config: GeohashConfig | None = None) -> list[str]:
    """Generate optimized geohash topic prefixes for NWS geographic data routing and spatial indexing.

    This function processes Well-Known Text (WKT) geometry strings from National Weather
    Service products and converts them into a collection of geohash strings that can be
    used as MQTT topic prefixes for geographic-based message routing. The algorithm
    automatically optimizes the geohash precision and tile count to balance spatial
    accuracy against system performance.

    The processing workflow adapts to different geometry types:
    - Point geometries generate a single geohash at the maximum configured precision
    - Polygon geometries undergo adaptive precision analysis, starting from the highest
      precision and reducing until the tile count falls within acceptable limits
    - Complex polygons utilize hierarchical merging to combine adjacent tiles and
      reduce topic proliferation while maintaining spatial coverage

    The resulting geohash strings serve as efficient spatial indexes that enable
    subscribers to receive weather alerts and updates for specific geographic regions
    without requiring complex geometric intersection calculations at message delivery time.

    Args:
        wkt_string: Well-Known Text geometry string from NWS weather products (e.g.,
            "POINT(-122.4194 37.7749)" or "POLYGON((-122.5 37.7, -122.3 37.7, ...))")
        config: Geohash generation configuration controlling precision levels, tile limits,
            and optimization strategies. If None, uses default configuration with precision
            range 3-6 and maximum 100 tiles per geometry.

    Returns:
        List of geohash strings optimized for spatial indexing and topic routing. Point
        geometries return a single-element list, while polygon geometries return multiple
        geohashes covering the area with configurable precision and tile count limits.

    Raises:
        WktParsingError: If the WKT string cannot be parsed or contains unsupported
            geometry types (only Point and Polygon are supported).
        GeohashTilingError: If geohash tile generation fails due to invalid coordinates,
            precision parameters, or geometric processing errors.

    """
    config = config or GeohashConfig()
    geometry = _parse_nws_wkt(wkt_string)
    if isinstance(geometry, Point):
        geohash_str = _determine_optimal_geohash_for_point(
            geometry.x,
            geometry.y,
            config.max_geohash_precision,
        )
        return [geohash_str]
    return _determine_optimal_geohash_coverage(geometry, config)


def _parse_nws_wkt(wkt_string: str) -> Point | Polygon:
    """Parse a Well-Known Text (WKT) geometry string from NWS products."""
    try:
        geometry = wkt.loads(wkt_string)
    except Exception as e:
        msg = f"Failed to parse WKT string '{wkt_string}': {e}"
        raise WktParsingError(msg) from e

    if not isinstance(geometry, (Point, Polygon)):
        msg = (
            f"Unsupported geometry type: {type(geometry).__name__}. "
            "Only Point and Polygon are supported."
        )
        raise WktParsingError(msg)

    return geometry


def _get_geometry_mbr(geometry: BaseGeometry) -> tuple[float, float, float, float]:
    """Get the Minimum Bounding Rectangle (MBR) of a geometry."""
    bounds = geometry.bounds
    return (bounds[0], bounds[1], bounds[2], bounds[3])


def _compute_raw_geohash_tiles_for_box(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    precision: int,
) -> list[str]:
    """Compute all geohash tiles that intersect with a bounding box."""
    tiles: set[str] = set()
    lat_step = 180.0 / (2 ** (precision * 2.5))
    lon_step = 360.0 / (2 ** (precision * 2.5))
    lat_step = max(lat_step, 0.001)
    lon_step = max(lon_step, 0.001)
    lat = min_lat
    while lat <= max_lat:
        lon = min_lon
        while lon <= max_lon:
            geohash_str = pgh.encode(lat, lon, precision=precision)
            tiles.add(geohash_str)
            lon += lon_step
        lat += lat_step
    return list(tiles)


def _hierarchically_merge_tiles(tiles: list[str]) -> list[str]:
    """Merge geohash tiles hierarchically to reduce count while maintaining coverage."""
    if len(tiles) <= 1:
        return tiles
    parent_groups: dict[str, list[str]] = {}
    for tile in tiles:
        if len(tile) > 1:
            parent = tile[:-1]
            if parent not in parent_groups:
                parent_groups[parent] = []
            parent_groups[parent].append(tile)
    merged_tiles: list[str] = []
    for parent, children in parent_groups.items():
        if len(children) >= 16:
            merged_tiles.append(parent)
        else:
            merged_tiles.extend(children)
    if len(merged_tiles) < len(tiles) * 0.8:
        return _hierarchically_merge_tiles(merged_tiles)
    return merged_tiles


def _determine_optimal_geohash_coverage(
    geometry: Polygon,
    config: GeohashConfig | None = None,
) -> list[str]:
    """Determine optimal geohash coverage for a geometry."""
    if config is None:
        config = GeohashConfig()
    try:
        min_lon, min_lat, max_lon, max_lat = _get_geometry_mbr(geometry)
        for precision in range(config.max_geohash_precision, config.min_geohash_precision - 1, -1):
            tiles = _compute_raw_geohash_tiles_for_box(
                min_lon, min_lat, max_lon, max_lat, precision
            )
            if config.use_hierarchical_merging:
                tiles = _hierarchically_merge_tiles(tiles)
            if len(tiles) <= config.max_tiles_per_geometry:
                logger.debug(
                    "Generated geohash coverage",
                    precision=precision,
                    tile_count=len(tiles),
                    geometry_type=type(geometry).__name__,
                )
                return tiles
        tiles = _compute_raw_geohash_tiles_for_box(
            min_lon, min_lat, max_lon, max_lat, config.min_geohash_precision
        )
        if config.use_hierarchical_merging:
            tiles = _hierarchically_merge_tiles(tiles)
        if len(tiles) > config.max_tiles_per_geometry:
            logger.warning(
                "Truncating geohash tiles to maximum limit",
                original_count=len(tiles),
                max_tiles=config.max_tiles_per_geometry,
            )
            tiles = tiles[: config.max_tiles_per_geometry]
    except Exception as e:
        msg = f"Failed to generate geohash coverage: {e}"
        raise GeohashTilingError(msg) from e
    else:
        return tiles


def _determine_optimal_geohash_for_point(
    longitude: float,
    latitude: float,
    precision: int = 6,
) -> str:
    """Determine optimal geohash for a single point."""
    return pgh.encode(latitude, longitude, precision=precision)


class GeohashError(Exception):
    """Base exception for geohash processing operations in the NWS geographic data system.

    This exception serves as the parent class for all geohash-related errors that can
    occur during WKT parsing, spatial indexing, and geohash tile generation. It provides
    a consistent error hierarchy for handling geographic data processing failures in
    the NWS weather data routing system.
    """


class WktParsingError(GeohashError):
    """Exception raised when Well-Known Text (WKT) geometry parsing fails.

    This exception is raised when the WKT string from NWS weather products cannot be
    parsed into a valid geometric object, or when the parsed geometry is of an
    unsupported type. The NWS geohash system currently supports only Point and Polygon
    geometries for spatial indexing and topic generation.
    """


class GeohashTilingError(GeohashError):
    """Exception raised when geohash tile generation or optimization operations fail.

    This exception occurs during the spatial tiling process when geohash generation
    encounters invalid coordinates, precision parameters outside acceptable ranges,
    or geometric processing errors that prevent successful tile creation. It indicates
    failures in the core spatial indexing algorithm that converts geometric areas
    into hierarchical geohash tiles for MQTT topic routing.
    """
