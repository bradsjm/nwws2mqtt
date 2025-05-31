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
    """Configuration for geohash-based geographic subscriptions.

    This configuration controls how geographic areas are tiled into geohashes
    for efficient spatial indexing and topic routing.
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
                f"min_geohash_precision must be between 1 and 12, "
                f"got {self.min_geohash_precision}"
            )
            raise ValueError(msg)

        if not 1 <= self.max_geohash_precision <= 12:
            msg = (
                f"max_geohash_precision must be between 1 and 12, "
                f"got {self.max_geohash_precision}"
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
            msg = (
                f"coverage_threshold must be between 0.0 and 1.0, "
                f"got {self.coverage_threshold}"
            )
            raise ValueError(msg)


def get_geohash_topics(
    wkt_string: str, config: GeohashConfig | None = None
) -> list[str]:
    """Generate geohash-based topic prefixes for a WKT geometry string."""
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
        for precision in range(
            config.max_geohash_precision, config.min_geohash_precision - 1, -1
        ):
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
    """Base exception for NWS Geospatial Subscriber operations."""


class WktParsingError(GeohashError):
    """Exception raised when WKT parsing fails."""


class GeohashTilingError(GeohashError):
    """Exception raised when geohash tiling operations fail."""
