"""Geo API endpoints for weather data."""

import time
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from nwws.utils.geo_provider import WeatherGeoDataProvider


def create_geo_endpoints(router: APIRouter, geo_provider: WeatherGeoDataProvider) -> None:
    """Create geographic data endpoints.

    Args:
        router: FastAPI router to add endpoints to
        geo_provider: Geographic data provider

    """

    @router.get("/api/geo/boundaries")
    async def get_office_boundaries(simplification: str = "web") -> JSONResponse:  # type: ignore[no-untyped-def]
        """Get Weather Forecast Office boundaries as GeoJSON."""
        try:
            geojson_data = geo_provider.get_cwa_geojson(simplification)
            return JSONResponse(content=geojson_data)
        except Exception:
            logger.exception("Failed to get office boundaries")
            raise HTTPException(
                status_code=500, detail="Failed to retrieve office boundaries"
            )

    @router.get("/api/geo/metadata")
    async def get_office_metadata() -> JSONResponse:  # type: ignore[no-untyped-def]
        """Get office locations, regions, and coverage metadata."""
        try:
            metadata = geo_provider.get_office_metadata()
            return JSONResponse(content=metadata)
        except Exception:
            logger.exception("Failed to get office metadata")
            raise HTTPException(status_code=500, detail="Failed to retrieve office metadata")

    @router.get("/api/geo/regions")
    async def get_region_summary() -> JSONResponse:  # type: ignore[no-untyped-def]
        """Get summary statistics by NWS region."""
        try:
            regions = geo_provider.get_region_summary()
            return JSONResponse(content=regions)
        except Exception:
            logger.exception("Failed to get region summary")
            raise HTTPException(status_code=500, detail="Failed to retrieve region summary")

    @router.get("/api/geo/activity")
    async def get_geographic_activity() -> JSONResponse:  # type: ignore[no-untyped-def]
        """Get geographic activity data for map visualization."""
        try:
            activity_data: dict[str, Any] = {
                "regions": {},
                "offices": {},
                "timestamp": time.time(),
            }
            return JSONResponse(content=activity_data)
        except Exception:
            logger.exception("Failed to get geographic activity")
            raise HTTPException(
                status_code=500, detail="Failed to retrieve geographic activity"
            )
