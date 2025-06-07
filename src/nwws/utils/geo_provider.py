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
    """Provides optimized geographic data services for weather operations dashboard.

    This class manages the loading, caching, and delivery of National Weather Service
    geographic data including County Warning Area (CWA) boundaries, weather office
    metadata, and real-time activity overlays. It serves as the primary geographic
    data provider for web-based weather operations dashboards, offering multiple
    levels of geometry simplification for optimal web performance.

    The provider handles automatic data loading from pyiem geodata sources, implements
    intelligent caching with TTL-based invalidation, and provides geographic data
    enrichment capabilities for operational metrics visualization. All geographic
    data is normalized to WGS84 (EPSG:4326) coordinate system for web mapping
    compatibility.

    Key capabilities include:
    - Automated loading of CWA boundaries from pyiem parquet data sources
    - Multi-level geometry simplification (overview, web, detailed) for performance
    - Office metadata extraction with regional classification and timezone mapping
    - Real-time activity overlay generation combining geographic and metrics data
    - Comprehensive regional summary statistics and coverage analysis
    """

    def __init__(self) -> None:
        """Initialize the geographic data provider with lazy-loading cache architecture.

        Sets up the provider with uninitialized data containers and cache management
        parameters. Geographic data loading is deferred until first access to optimize
        startup performance. The cache system uses a 1-hour TTL to balance data
        freshness with performance, automatically refreshing stale data when accessed.

        Cache containers are initialized as None to enable lazy loading detection,
        and the cache timestamp tracking enables TTL-based invalidation for
        operational data consistency.
        """
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

            # Set geometry column properly for GeoDataFrame
            if "geom" in self._cwa_df.columns:
                self._cwa_df = self._cwa_df.set_geometry("geom")
            else:
                logger.error(
                    f"'geom' column not found in CWA dataframe. Available columns: {list(self._cwa_df.columns)}"
                )

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

            # Calculate centroid for office location - access geometry directly from DataFrame
            try:
                geometry: BaseGeometry | None = self._cwa_df.loc[cwa_str, "geom"]  # type: ignore[misc]
            except (KeyError, IndexError):
                geometry = None
            if geometry is not None:
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
            logger.warning("CWA DataFrame is None, cannot create simplified geometries")
            return

        logger.debug(f"Creating simplified geometries for {len(self._cwa_df)} CWA features")

        simplification_levels = {
            "overview": 0.05,  # Very simplified for overview map
            "web": 0.01,  # Standard web simplification
            "detailed": 0.005,  # More detailed for closer zoom
        }

        simplified_data = {}

        for level, tolerance in simplification_levels.items():
            level_data = {}
            logger.debug(f"Processing simplification level '{level}' with tolerance {tolerance}")

            for cwa_id, _row in self._cwa_df.iterrows():  # type: ignore[misc]
                if not cwa_id or (isinstance(cwa_id, str) and pd.isna(cwa_id)):  # type: ignore[misc]
                    continue

                # Access geometry directly from DataFrame instead of row
                try:
                    geometry: BaseGeometry | None = self._cwa_df.loc[str(cwa_id), "geom"]  # type: ignore[misc]
                except (KeyError, IndexError):
                    geometry = None

                logger.debug(
                    f"CWA {cwa_id}: geometry type = {type(geometry)}, "
                    f"has_simplify = {hasattr(geometry, 'simplify') if geometry else False}"
                )

                if geometry:
                    try:
                        # Simplify geometry for web performance
                        simplified = geometry.simplify(tolerance, preserve_topology=True)  # type: ignore[misc]
                        if simplified and not simplified.is_empty:
                            level_data[str(cwa_id)] = simplified
                            logger.debug(f"Successfully simplified {cwa_id} for {level}")
                        else:
                            logger.warning(f"Simplified geometry for {cwa_id} is empty or None")
                    except (AttributeError, ValueError, TypeError) as e:
                        logger.error(f"Failed to simplify geometry for {cwa_id}: {e}")
                else:
                    logger.warning(f"CWA {cwa_id}: geometry is None or lacks simplify method")

            logger.info(f"Simplification level '{level}': created {len(level_data)} geometries")
            simplified_data[level] = level_data

        self._simplified_geometries = simplified_data
        logger.info(
            f"Created simplified geometries: {[f'{k}: {len(v)}' for k, v in simplified_data.items()]}"
        )

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
        """Generate GeoJSON representation of County Warning Area boundaries with optimized geometry.

        Retrieves and formats National Weather Service County Warning Area (CWA)
        boundaries as a standards-compliant GeoJSON FeatureCollection. The method
        applies intelligent geometry simplification based on the requested level to
        optimize web delivery performance while maintaining geographic accuracy
        appropriate for the use case.

        The function ensures data freshness by invoking the cache validation system,
        applies the requested simplification level with automatic fallback to 'web'
        level if the requested level is unavailable, and enriches each CWA feature
        with essential metadata including office names and regional classifications.

        Geometry simplification levels:
        - "overview": Highly simplified for continental/regional views (fastest)
        - "web": Balanced simplification for interactive web maps (default)
        - "detailed": Minimal simplification for detailed analysis (most accurate)

        Args:
            simplification_level: Geometry simplification level for web optimization.
                                 Must be one of "overview", "web", or "detailed".
                                 Defaults to "web" for optimal web performance.

        Returns:
            GeoJSON FeatureCollection containing CWA boundary features with properties
            including CWA identifier, office name, and regional classification. Each
            feature includes simplified geometry appropriate for the requested level.
            Includes metadata with simplification level, feature count, and generation
            timestamp for cache management.

        Raises:
            RuntimeError: If geographic data loading fails or required data is corrupted.

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
        """Retrieve comprehensive metadata for all National Weather Service offices.

        Provides detailed operational metadata for Weather Forecast Offices including
        geographic coordinates, regional classifications, coverage area calculations,
        and timezone assignments. This metadata supports operational dashboards,
        routing systems, and geographic analysis workflows requiring accurate office
        location and coverage information.

        The metadata includes calculated centroid coordinates for each CWA boundary,
        enabling precise office location mapping, regional grouping based on NWS
        administrative structure, coverage area measurements in square kilometers
        for capacity planning, and timezone assignments for temporal correlation
        of weather events and operational activities.

        Returns:
            Dictionary containing complete office metadata organized in two sections:
            - 'offices': Maps CWA identifiers to detailed office metadata including
              ID, name, region, coordinates, coverage area, and timezone
            - 'summary': Aggregate statistics including total office count, unique
              regions list, and generation timestamp for cache validation

        Raises:
            RuntimeError: If office metadata creation fails due to corrupted
                         geographic data or coordinate transformation errors.

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
        """Generate activity-enriched geographic overlay combining CWA boundaries with operational metrics.

        Creates a comprehensive geographic visualization layer by merging base CWA
        boundary geometries with real-time operational metrics from the monitoring
        system. This enables dynamic geographic visualization of National Weather
        Service office activity levels, performance indicators, and operational
        status across the continental United States.

        The function retrieves optimized CWA boundaries at web simplification level
        for performance, correlates metrics data with office boundaries using CWA
        identifiers, calculates derived metrics including activity levels and health
        status, and enriches each geographic feature with operational context for
        dashboard visualization.

        Activity enrichment includes message processing counts, error rates and
        totals, average processing latency measurements, timestamp of last message
        activity, calculated activity level classification (high/medium/low/idle),
        and overall office status determination (healthy/warning/error/offline).

        Args:
            metrics_data: Real-time metrics data from operational collectors organized
                         by WMO office identifiers. Expected to contain 'by_wmo' section
                         with per-office metrics including message counts, error rates,
                         latency measurements, and activity timestamps.

        Returns:
            GeoJSON FeatureCollection with activity-enriched CWA boundaries. Each
            feature contains base geographic properties plus operational metrics,
            activity classifications, and status indicators. Includes metadata
            section with enrichment type, source metrics timestamp, and generation
            time for cache coordination.

        Raises:
            ValueError: If metrics_data structure is invalid or missing required sections.
            RuntimeError: If geographic data correlation fails or metric calculations error.

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
            office_metrics = metrics_data.get("by_wmo", {}).get(cwa_id, {})

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
        """Generate comprehensive regional statistics for National Weather Service operations.

        Calculates and aggregates operational statistics organized by NWS administrative
        regions to support strategic planning, resource allocation, and operational
        oversight. The summary provides region-level office counts, total geographic
        coverage calculations, and office distribution analysis for management
        dashboards and capacity planning workflows.

        The function processes office metadata to group offices by regional assignments
        according to NWS administrative structure, calculates total coverage area
        per region by summing individual office CWA areas, tracks office counts and
        identifiers for each region, and provides aggregate statistics across all
        regions for system-wide operational visibility.

        Regional aggregation supports operational decision-making by providing insights
        into geographic coverage distribution, office density variations across regions,
        and total operational capacity measurements for strategic resource planning.

        Returns:
            Dictionary containing regional analysis with two main sections:
            - 'regions': Maps region identifiers to detailed statistics including
              office count, total coverage area in square kilometers, and complete
              list of office identifiers within each region
            - 'summary': System-wide aggregate statistics including total regions
              count, total offices across all regions, and generation timestamp
              for data freshness verification

        Raises:
            RuntimeError: If regional classification fails or coverage calculations
                         encounter invalid geometric data.

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
