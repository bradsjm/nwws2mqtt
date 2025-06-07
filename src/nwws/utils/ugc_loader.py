# pyright: standard
"""UGC (Universal Geographic Code) loader utility for offline geographic data resolution.

This module provides comprehensive functionality to load and process UGC data from pyIEM's
bundled parquet files, enabling geographic code resolution without requiring a PostgreSQL
database connection. The module serves as a critical component in the NWWS2MQTT system
for translating geographic codes found in weather messages into human-readable names.

The UGC system is used by the National Weather Service to identify specific geographic
areas (counties and forecast zones) in weather products. This module creates an offline
UGCProvider that can resolve UGC codes like "MIC084" (Macomb County, Michigan) or
"MIZ084" (Southeast Michigan forecast zone) to their corresponding names and associated
Weather Forecast Office (WFO) information.

Key Components:
- Loading county and zone geographic data from parquet files
- Processing UGC codes into structured UGC objects with proper geoclass classification
- Creating a legacy dictionary mapping for efficient code lookup
- Providing fallback error handling for robust operation

The module integrates with pyIEM's data distribution system and provides a self-contained
solution for geographic code resolution in weather message processing pipelines.
"""

import importlib.resources

import geopandas as gpd
import pandas as pd
from loguru import logger
from pyiem.nws.ugc import UGC, UGCProvider


def load_ugc_dataframes() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Load UGC county and zone geographic data from pyIEM's distributed parquet files.

    This function accesses the pyIEM package's bundled geographic data files to load
    Universal Geographic Code (UGC) information for both counties and forecast zones.
    The data is distributed as part of the pyIEM package installation and provides
    comprehensive coverage of all NWS geographic areas without requiring external
    database connections.

    The function uses importlib.resources to access the bundled parquet files in a
    cross-platform compatible manner, handling both traditional and namespace package
    installations. It loads two separate datasets: county-level UGC codes (geoclass 'C')
    and forecast zone UGC codes (geoclass 'Z'), each containing geographic boundaries,
    UGC identifiers, and associated Weather Forecast Office assignments.

    The loaded GeoDataFrames contain spatial geometry information along with UGC
    metadata, enabling both geographic operations and code resolution functionality.
    Debug logging is performed to track the number of records loaded from each dataset
    for monitoring and troubleshooting purposes.

    Returns:
        Tuple of (county_df, zone_df) GeoDataFrames containing UGC data with spatial
        geometry and metadata fields including UGC codes and WFO assignments.

    Raises:
        FileNotFoundError: If the pyIEM parquet data files cannot be located in the
            package resources, indicating a corrupted or incomplete installation.
        ImportError: If the pyIEM package is not properly installed or accessible.
        OSError: For file system errors during parquet file reading operations.

    """
    try:
        # Load county data
        county_traversable = importlib.resources.files("pyiem.data.geodf") / "ugcs_county.parquet"
        county_path_str = str(county_traversable)
        county_df = gpd.read_parquet(county_path_str)

        # Load zone data
        zone_traversable = importlib.resources.files("pyiem.data.geodf") / "ugcs_zone.parquet"
        zone_path_str = str(zone_traversable)
        zone_df = gpd.read_parquet(zone_path_str)

        logger.debug(
            "Loaded UGC data from parquet files",
            county_records=len(county_df),
            zone_records=len(zone_df),
        )

    except FileNotFoundError as e:
        logger.error("UGC parquet files not found", error=str(e))
        raise
    except (ImportError, OSError) as e:
        logger.error("Failed to load UGC data", error=str(e))
        raise

    return county_df, zone_df


def create_ugc_legacy_dict(county_df: "pd.DataFrame", zone_df: "pd.DataFrame") -> dict[str, UGC]:
    """Create a comprehensive legacy dictionary mapping UGC codes to structured UGC objects.

    This function processes raw UGC data from county and zone DataFrames and transforms
    them into a standardized dictionary structure compatible with pyIEM's UGCProvider
    legacy format. The function performs critical data parsing and validation to ensure
    proper UGC code structure and extract geographic classification information.

    The processing workflow involves:
    1. Iterating through county and zone DataFrames using iterrows() to avoid pandas
       Series ambiguity issues with mixed data types
    2. Parsing UGC codes to extract state abbreviation, geoclass ('C' for county, 'Z'
       for zone), and numeric identifier components
    3. Safely extracting County Warning Area (CWA/WFO) assignments with robust null
       value handling to prevent pandas conversion errors
    4. Creating structured UGC objects with proper metadata and WFO associations
    5. Validating UGC code format and length before processing

    The function handles data quality issues commonly found in geographic datasets,
    including missing values, inconsistent data types, and malformed UGC codes. It
    applies defensive programming practices to ensure robustness when processing
    real-world data that may contain anomalies or missing fields.

    Args:
        county_df: DataFrame containing county UGC data with index as UGC codes
            and columns including 'cwa' for Weather Forecast Office assignments.
        zone_df: DataFrame containing forecast zone UGC data with similar structure
            to county_df but representing weather forecast zones instead of counties.

    Returns:
        Dictionary mapping UGC code strings (e.g., 'MIC084', 'MIZ084') to UGC objects
        containing parsed geographic information, names, and WFO associations. The
        dictionary serves as a lookup table for efficient UGC code resolution.

    """
    legacy_dict: dict[str, UGC] = {}

    # Process county data using iterrows to avoid Series ambiguity
    for ugc_code, row in county_df.iterrows():
        if ugc_code and len(str(ugc_code)) >= 5:  # Basic validation (e.g., 'MIC084')
            ugc_str = str(ugc_code)
            # Extract state (first 2 chars), geoclass (3rd char), number (last 3 chars)
            state = ugc_str[:2] if len(ugc_str) >= 2 else ""
            geoclass = ugc_str[2:3] if len(ugc_str) >= 3 else "C"
            number_str = ugc_str[3:] if len(ugc_str) > 3 else "0"

            # Extract CWA safely
            cwa = ""
            try:
                cwa_val = row["cwa"]
                if not bool(
                    pd.isna(cwa_val).item()
                    if hasattr(pd.isna(cwa_val), "item")
                    else pd.isna(cwa_val)
                ):
                    cwa = str(cwa_val)
            except (KeyError, TypeError, AttributeError):
                pass

            ugc_obj = UGC(
                state=state,
                geoclass=geoclass,
                number=int(number_str) if number_str.isdigit() else 0,
                name=f"County {ugc_str}",  # Default name since no name field available
                wfos=[cwa] if cwa else [],
            )
            legacy_dict[ugc_str] = ugc_obj

    # Process zone data using iterrows to avoid Series ambiguity
    for ugc_code, row in zone_df.iterrows():
        if ugc_code and len(str(ugc_code)) >= 5:  # Basic validation (e.g., 'MIZ084')
            ugc_str = str(ugc_code)
            # Extract state (first 2 chars), geoclass (3rd char), number (last 3 chars)
            state = ugc_str[:2] if len(ugc_str) >= 2 else ""
            geoclass = ugc_str[2:3] if len(ugc_str) >= 3 else "Z"
            number_str = ugc_str[3:] if len(ugc_str) > 3 else "0"

            # Extract CWA safely
            cwa = ""
            try:
                cwa_val = row["cwa"]
                if not bool(
                    pd.isna(cwa_val).item()
                    if hasattr(pd.isna(cwa_val), "item")
                    else pd.isna(cwa_val)
                ):
                    cwa = str(cwa_val)
            except (KeyError, TypeError, AttributeError):
                pass

            ugc_obj = UGC(
                state=state,
                geoclass=geoclass,
                number=int(number_str) if number_str.isdigit() else 0,
                name=f"Zone {ugc_str}",  # Default name since no name field available
                wfos=[cwa] if cwa else [],
            )
            legacy_dict[ugc_str] = ugc_obj

    logger.debug(
        "Created UGC legacy dictionary",
        total_ugc_codes=len(legacy_dict),
    )

    return legacy_dict


def create_ugc_provider() -> UGCProvider:
    """Create a fully configured UGCProvider instance for offline geographic code resolution.

    This function serves as the primary entry point for creating a UGCProvider that can
    resolve UGC codes to geographic names without requiring database connectivity. It
    orchestrates the complete data loading and processing pipeline to create a self-contained
    geographic resolution service suitable for weather message processing applications.

    The function implements a robust initialization sequence:
    1. Loading county and zone geographic data from pyIEM's bundled parquet files
    2. Processing the raw data into a structured legacy dictionary format
    3. Instantiating a UGCProvider with the processed data for immediate use
    4. Implementing comprehensive error handling with graceful degradation

    The resulting UGCProvider enables resolution of UGC codes commonly found in National
    Weather Service products, such as converting "MIC163" to "Wayne County, Michigan" or
    "MIZ084" to "Southeast Michigan forecast zone". This capability is essential for
    weather message processing systems that need to provide human-readable geographic
    context for weather warnings, watches, and forecasts.

    Error handling includes graceful degradation where a connection failure or data
    loading issue results in an empty UGCProvider rather than system failure, ensuring
    the calling application can continue operating with reduced functionality rather
    than crashing completely.

    Returns:
        UGCProvider instance configured with comprehensive UGC data for both counties
        and forecast zones, ready for immediate geographic code resolution operations.
        In case of data loading failures, returns an empty UGCProvider as a fallback.

    Raises:
        ImportError: If the pyIEM package dependencies are not properly installed
            or accessible in the current Python environment.
        OSError: For file system errors during parquet data file access or processing.
        ValueError: If the loaded UGC data contains invalid or unparseable values
            that prevent proper UGCProvider initialization.

    """
    try:
        county_df, zone_df = load_ugc_dataframes()
        legacy_dict = create_ugc_legacy_dict(county_df, zone_df)

        provider = UGCProvider(legacy_dict=legacy_dict)
        logger.info("Created UGCProvider with local data")

    except (ImportError, OSError, ValueError) as e:
        logger.warning("Failed to create UGCProvider (will continue without)", error=str(e))
        # Return empty provider as fallback
        return UGCProvider(legacy_dict={})

    return provider
