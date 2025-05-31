# pyright: standard
"""UGC (Universal Geographic Code) loader utility.

This module provides functionality to load UGC data from pyIEM's bundled
parquet files and create a UGCProvider for resolving UGC codes to names
without requiring a PostgreSQL database.
"""

import importlib.resources

import geopandas as gpd
import pandas as pd
from loguru import logger
from pyiem.nws.ugc import UGC, UGCProvider


def load_ugc_dataframes() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Load UGC county and zone data from pyIEM's bundled parquet files.

    Returns:
        Tuple of (county_df, zone_df) GeoDataFrames containing UGC data.

    Raises:
        FileNotFoundError: If the parquet files cannot be found.
        Exception: For other errors during file loading.

    """
    try:
        # Load county data
        county_traversable = (
            importlib.resources.files("pyiem.data.geodf") / "ugcs_county.parquet"
        )
        county_path_str = str(county_traversable)
        county_df = gpd.read_parquet(county_path_str)

        # Load zone data
        zone_traversable = (
            importlib.resources.files("pyiem.data.geodf") / "ugcs_zone.parquet"
        )
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


def create_ugc_legacy_dict(
    county_df: "pd.DataFrame", zone_df: "pd.DataFrame"
) -> dict[str, UGC]:
    """Create a legacy dictionary mapping UGC codes to UGC objects.

    Args:
        county_df: DataFrame containing county UGC data.
        zone_df: DataFrame containing zone UGC data.

    Returns:
        Dictionary mapping UGC codes (e.g., 'MIZ084') to UGC objects.

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
    """Create a UGCProvider with local data for UGC name resolution.

    Returns:
        UGCProvider instance configured with local UGC data.

    Raises:
        Exception: If UGC data cannot be loaded or processed.

    """
    try:
        county_df, zone_df = load_ugc_dataframes()
        legacy_dict = create_ugc_legacy_dict(county_df, zone_df)

        provider = UGCProvider(legacy_dict=legacy_dict)
        logger.debug("Created UGCProvider with local data")

    except (ImportError, OSError, ValueError) as e:
        logger.error("Failed to create UGCProvider", error=str(e))
        # Return empty provider as fallback
        return UGCProvider(legacy_dict={})

    return provider
