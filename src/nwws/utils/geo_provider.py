# pyright: standard
"""Geographic data provider for weather operations dashboard.

This module provides optimized geographic data loading and web delivery for
Weather Forecast Office boundaries, office metadata, and activity overlays.
"""

from __future__ import annotations

import importlib.resources
import time
from typing import TYPE_CHECKING, Any

import geopandas as gpd
import pandas as pd
from loguru import logger

if TYPE_CHECKING:
    from shapely.geometry.base import BaseGeometry


class WeatherGeoDataProvider:
    """Manages geographic data loading and web optimization for dashboard."""

    def __init__(self) -> None:
        """Initialize the geographic data provider with cached data loading."""
        self._cwa_df: gpd.GeoDataFrame | None = None
        self._office_metadata: dict[str, Any] | None = None
        self._simplified_geometries: dict[str, dict[str, Any]] | None = None
        self._last_cache_time: float = 0.0
        self._cache_ttl: float = 3600.0  # 1 hour cache TTL

    def _load_base_data(self) -> None:
        """Load and cache base geographic data from pyiem parquet files."""
        try:
            # Load CWA (County Warning Area) boundaries
            cwa_traversable = importlib.resources.files("pyiem.data.geodf") / "cwa.parquet"
            cwa_path_str = str(cwa_traversable)
            self._cwa_df = gpd.read_parquet(cwa_path_str)  # type: ignore[misc]

            # Ensure CRS is WGS84 for web mapping
            if self._cwa_df.crs != "EPSG:4326":
                self._cwa_df = self._cwa_df.to_crs("EPSG:4326")

            # Create office metadata lookup
            self._create_office_metadata()

            # Pre-compute simplified geometries for different zoom levels
            self._create_simplified_geometries()

            self._last_cache_time = time.time()

            logger.info(
                "Geographic data loaded successfully",
                cwa_count=len(self._cwa_df),
                cache_time=self._last_cache_time,
            )

        except Exception as e:
            logger.error("Failed to load geographic data", error=str(e))
            raise

    def _create_office_metadata(self) -> None:
        """Create office metadata lookup from CWA dataframe."""
        if self._cwa_df is None:
            return

        office_data = {}

        for cwa_id, row in self._cwa_df.iterrows():
            if not cwa_id or (isinstance(cwa_id, str) and pd.isna(cwa_id)):
                continue

            cwa_str = str(cwa_id)

            # Calculate centroid for office location
            geometry = getattr(row, "geometry", None)
            if geometry is not None and hasattr(geometry, "centroid"):
                centroid = geometry.centroid
                lat, lon = float(centroid.y), float(centroid.x)
            else:
                lat, lon = None, None

            # Extract office information
            office_name = str(getattr(row, "name", f"Weather Office {cwa_str}"))
            region = self._determine_region(cwa_str)

            office_data[cwa_str] = {
                "id": cwa_str,
                "name": office_name,
                "region": region,
                "latitude": lat,
                "longitude": lon,
                "coverage_area": self._calculate_coverage_area(geometry),
                "timezone": self._determine_timezone(cwa_str),
            }

        self._office_metadata = office_data

    def _create_simplified_geometries(self) -> None:
        """Create simplified geometries for different web zoom levels."""
        if self._cwa_df is None:
            return

        simplification_levels = {
            "overview": 0.05,  # Very simplified for overview map
            "web": 0.01,  # Standard web simplification
            "detailed": 0.005,  # More detailed for closer zoom
        }

        simplified_data = {}

        for level, tolerance in simplification_levels.items():
            level_data = {}

            for cwa_id, row in self._cwa_df.iterrows():  # type: ignore[misc]
                if not cwa_id or (isinstance(cwa_id, str) and pd.isna(cwa_id)):  # type: ignore[misc]
                    continue

                geometry = (
                    row.get("geometry") if hasattr(row, "get") else getattr(row, "geometry", None)
                )  # type: ignore[misc]
                if geometry and hasattr(geometry, "simplify"):
                    # Simplify geometry for web performance
                    simplified = geometry.simplify(tolerance, preserve_topology=True)  # type: ignore[misc]
                    level_data[str(cwa_id)] = simplified

            simplified_data[level] = level_data

        self._simplified_geometries = simplified_data

    def _determine_region(self, cwa_id: str) -> str:  # noqa: PLR0911
        """Determine NWS region from CWA identifier."""
        # NWS regional mapping based on CWA identifier patterns
        eastern_offices = {
            "AKQ",
            "ALY",
            "BGM",
            "BOX",
            "BUF",
            "CAE",
            "CHS",
            "CTP",
            "GSP",
            "GYX",
            "ILM",
            "LWX",
            "MHX",
            "OKX",
            "PHI",
            "RAH",
            "RLX",
            "RNK",
        }

        central_offices = {
            "ABR",
            "APX",
            "ARX",
            "BIS",
            "BOU",
            "CYS",
            "DDC",
            "DLH",
            "DMX",
            "DTX",
            "DVN",
            "EAX",
            "FGF",
            "FSD",
            "GID",
            "GJT",
            "GLD",
            "GRB",
            "GRR",
            "ICT",
            "ILX",
            "IND",
            "IWX",
            "JKL",
            "LBF",
            "LMK",
            "LOT",
            "LSX",
            "MKX",
            "MPX",
            "MQT",
            "OAX",
            "PAH",
            "PUB",
            "RIW",
            "SGF",
            "TOP",
            "UNR",
        }

        southern_offices = {
            "ABQ",
            "AMA",
            "BMX",
            "BRO",
            "CRP",
            "EPZ",
            "EWX",
            "FFC",
            "FWD",
            "HGX",
            "HUN",
            "JAN",
            "JAX",
            "KEY",
            "LCH",
            "LIX",
            "LUB",
            "LZK",
            "MAF",
            "MEG",
            "MFL",
            "MLB",
            "MOB",
            "MRX",
            "OHX",
            "OUN",
            "SHV",
            "SJT",
            "SJU",
            "TAE",
            "TBW",
            "TSA",
        }

        western_offices = {
            "BOI",
            "BYZ",
            "EKA",
            "FGZ",
            "GGW",
            "HNX",
            "LKN",
            "LOX",
            "MFR",
            "MSO",
            "MTR",
            "OTX",
            "PDT",
            "PIH",
            "PQR",
            "PSR",
            "REV",
            "SEW",
            "SGX",
            "SLC",
            "STO",
            "TFX",
            "TWC",
            "VEF",
        }

        alaska_offices = {"AFC", "AFG", "AJK", "ALU", "NSB", "ORR", "PAC", "WCZ"}

        pacific_offices = {"GUM", "HFO", "PPG"}

        if cwa_id in eastern_offices:
            return "Eastern"
        if cwa_id in central_offices:
            return "Central"
        if cwa_id in southern_offices:
            return "Southern"
        if cwa_id in western_offices:
            return "Western"
        if cwa_id in alaska_offices:
            return "Alaska"
        if cwa_id in pacific_offices:
            return "Pacific"
        return "Unknown"

    def _calculate_coverage_area(self, geometry: BaseGeometry | None) -> float | None:
        """Calculate coverage area in square kilometers."""
        if not geometry:
            return None

        try:
            # Rough conversion from decimal degrees to km² (very approximate)
            # For proper calculation, would need proper projection
            area_deg_sq = geometry.area
            area_km_sq = area_deg_sq * 111.32 * 111.32  # Very rough approximation

            return round(area_km_sq, 2)

        except (AttributeError, TypeError, ValueError):
            return None

    def _determine_timezone(self, cwa_id: str) -> str:  # noqa: PLR0911
        """Determine timezone for office based on CWA identifier."""
        # Simplified timezone mapping based on CWA location
        eastern_tz = {
            "AKQ",
            "ALY",
            "BGM",
            "BOX",
            "BUF",
            "CAE",
            "CHS",
            "CTP",
            "GSP",
            "GYX",
            "ILM",
            "JAX",
            "JKL",
            "KEY",
            "LWX",
            "MFL",
            "MHX",
            "MLB",
            "OKX",
            "PHI",
            "RAH",
            "RLX",
            "RNK",
            "TAE",
            "TBW",
        }

        central_tz = {
            "ABR",
            "APX",
            "ARX",
            "BIS",
            "BMX",
            "BRO",
            "CRP",
            "DDC",
            "DLH",
            "DMX",
            "DVN",
            "EAX",
            "EWX",
            "FFC",
            "FGF",
            "FSD",
            "FWD",
            "GID",
            "GRB",
            "GRR",
            "HGX",
            "HUN",
            "ICT",
            "ILX",
            "IND",
            "IWX",
            "JAN",
            "LBF",
            "LCH",
            "LIX",
            "LMK",
            "LOT",
            "LSX",
            "LUB",
            "LZK",
            "MEG",
            "MKX",
            "MOB",
            "MPX",
            "MQT",
            "MRX",
            "OAX",
            "OHX",
            "OUN",
            "PAH",
            "SGF",
            "SHV",
            "SJT",
            "TOP",
            "TSA",
        }

        mountain_tz = {
            "ABQ",
            "AMA",
            "BOU",
            "BYZ",
            "CYS",
            "GJT",
            "GLD",
            "GGW",
            "MAF",
            "MSO",
            "OTX",
            "PIH",
            "PUB",
            "RIW",
            "SLC",
            "TFX",
            "UNR",
        }

        pacific_tz = {
            "BOI",
            "EKA",
            "FGZ",
            "HNX",
            "LKN",
            "LOX",
            "MFR",
            "MTR",
            "PDT",
            "PQR",
            "REV",
            "SEW",
            "SGX",
            "STO",
        }

        alaska_tz = {"AFC", "AFG", "AJK", "ALU", "NSB", "ORR", "PAC", "WCZ"}

        if cwa_id in eastern_tz:
            return "America/New_York"
        if cwa_id in central_tz:
            return "America/Chicago"
        if cwa_id in mountain_tz:
            return "America/Denver"
        if cwa_id in pacific_tz:
            return "America/Los_Angeles"
        if cwa_id in alaska_tz:
            return "America/Anchorage"
        if cwa_id == "HFO":
            return "Pacific/Honolulu"
        if cwa_id == "GUM":
            return "Pacific/Guam"
        if cwa_id == "PPG":
            return "Pacific/Pago_Pago"
        return "America/New_York"

    def _ensure_data_loaded(self) -> None:
        """Ensure geographic data is loaded and not stale."""
        current_time = time.time()

        if (
            self._cwa_df is None
            or self._office_metadata is None
            or (current_time - self._last_cache_time) > self._cache_ttl
        ):
            self._load_base_data()

    def get_cwa_geojson(self, simplification_level: str = "web") -> dict[str, Any]:
        """Return CWA boundaries as GeoJSON with specified simplification.

        Args:
            simplification_level: Level of geometry simplification
                                 ("overview", "web", "detailed")

        Returns:
            GeoJSON FeatureCollection with CWA boundaries

        """
        self._ensure_data_loaded()

        if not self._simplified_geometries or self._cwa_df is None or self._cwa_df.empty:
            return {"type": "FeatureCollection", "features": []}

        # Get simplified geometries for the requested level
        geometries = self._simplified_geometries.get(simplification_level, {})
        if not geometries:
            # Fallback to web level if requested level not available
            geometries = self._simplified_geometries.get("web", {})

        features: list[dict[str, Any]] = []

        for cwa_id, row in self._cwa_df.iterrows():  # type: ignore[misc]
            if not cwa_id or (isinstance(cwa_id, str) and pd.isna(cwa_id)):  # type: ignore[misc]
                continue

            cwa_str = str(cwa_id)
            simplified_geom = geometries.get(cwa_str)

            if simplified_geom and hasattr(simplified_geom, "__geo_interface__"):
                # Convert to GeoJSON feature
                office_name = (
                    row.get("name", f"Weather Office {cwa_str}")
                    if hasattr(row, "get")
                    else f"Weather Office {cwa_str}"
                )  # type: ignore[misc]
                feature = {
                    "type": "Feature",
                    "id": cwa_str,
                    "properties": {
                        "cwa": cwa_str,
                        "name": str(office_name),
                        "region": self._determine_region(cwa_str),
                    },
                    "geometry": simplified_geom.__geo_interface__,
                }
                features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "simplification_level": simplification_level,
                "feature_count": len(features),
                "generated_at": time.time(),
            },
        }

    def get_office_metadata(self) -> dict[str, Any]:
        """Return office locations, regions, and coverage areas.

        Returns:
            Dictionary mapping CWA IDs to office metadata

        """
        self._ensure_data_loaded()

        if not self._office_metadata:
            return {}

        return {
            "offices": self._office_metadata.copy(),
            "summary": {
                "total_offices": len(self._office_metadata),
                "regions": list({office["region"] for office in self._office_metadata.values()}),
                "generated_at": time.time(),
            },
        }

    def get_activity_overlay_data(self, metrics_data: dict[str, Any]) -> dict[str, Any]:
        """Combine geographic boundaries with current metrics for activity overlay.

        Args:
            metrics_data: Current metrics data from collectors

        Returns:
            GeoJSON with activity-enriched office boundaries

        """
        self._ensure_data_loaded()

        # Get base CWA boundaries
        base_geojson = self.get_cwa_geojson("web")

        # Enrich with activity data
        activity_features: list[dict[str, Any]] = []

        for feature in base_geojson.get("features", []):
            cwa_id = feature.get("id")
            properties = feature.get("properties", {}).copy()

            # Add activity metrics if available
            office_metrics = metrics_data.get("by_office", {}).get(cwa_id, {})

            properties.update(
                {
                    "message_count": office_metrics.get("messages_processed_total", 0),
                    "error_count": office_metrics.get("errors_total", 0),
                    "avg_latency_ms": office_metrics.get("avg_processing_latency_ms", 0),
                    "last_activity": office_metrics.get("last_message_time"),
                    "activity_level": self._calculate_activity_level(office_metrics),
                    "status": self._determine_office_status(office_metrics),
                }
            )

            activity_feature = {
                **feature,
                "properties": properties,
            }
            activity_features.append(activity_feature)

        return {
            "type": "FeatureCollection",
            "features": activity_features,
            "metadata": {
                "enriched_with": "activity_metrics",
                "metrics_timestamp": metrics_data.get("timestamp"),
                "generated_at": time.time(),
            },
        }

    def _calculate_activity_level(self, office_metrics: dict[str, Any]) -> str:
        """Calculate activity level classification for office.

        Args:
            office_metrics: Metrics data for a specific office

        Returns:
            Activity level: "high", "medium", "low", "idle"

        """
        message_count = office_metrics.get("messages_processed_total", 0)

        # Simple classification based on message volume
        if message_count > 100:
            return "high"
        if message_count > 20:
            return "medium"
        if message_count > 0:
            return "low"
        return "idle"

    def _determine_office_status(self, office_metrics: dict[str, Any]) -> str:
        """Determine overall status of weather office.

        Args:
            office_metrics: Metrics data for a specific office

        Returns:
            Status: "healthy", "warning", "error", "offline"

        """
        last_activity = office_metrics.get("last_message_time")
        current_time = time.time()
        error_rate = office_metrics.get("error_rate", 0.0)

        # Check if office has been inactive for too long
        if last_activity and (current_time - last_activity) > 3600:  # 1 hour
            return "offline"

        # Check error rate
        if error_rate > 0.1:  # More than 10% errors
            return "error"
        if error_rate > 0.05:  # More than 5% errors
            return "warning"
        return "healthy"

    def get_region_summary(self) -> dict[str, Any]:
        """Get summary statistics by NWS region.

        Returns:
            Dictionary with office counts and coverage by region

        """
        self._ensure_data_loaded()

        if not self._office_metadata:
            return {}

        region_stats: dict[str, Any] = {}

        for office in self._office_metadata.values():
            region = office["region"]

            if region not in region_stats:
                region_stats[region] = {
                    "office_count": 0,
                    "total_coverage_km2": 0.0,
                    "offices": [],
                }

            region_stats[region]["office_count"] += 1
            region_stats[region]["offices"].append(office["id"])

            coverage = office.get("coverage_area")
            if coverage:
                region_stats[region]["total_coverage_km2"] += coverage

        return {
            "regions": region_stats,
            "summary": {
                "total_regions": len(region_stats),
                "total_offices": sum(r["office_count"] for r in region_stats.values()),
                "generated_at": time.time(),
            },
        }
