# MQTT Topic Structure

This document describes the MQTT topic structure used by the NWWS-to-MQTT pipeline for publishing National Weather Service (NWS) text products.

## Overview

The MQTT topic structure is designed to enable efficient filtering by weather station (CCCC) and product type while maintaining flexibility for future enhancements. The structure leverages existing standardized fields from the pyIEM library without requiring hardcoded lookup tables.

## Default Topic Pattern

```
{prefix}/{cccc}/{product_type}/{awipsid}/{product_id}
```

### Components

| Component | Description | Example Values |
|-----------|-------------|----------------|
| `prefix` | Configurable topic prefix | `nwws` (default) |
| `cccc` | 4-character NWS office identifier | `KALY`, `KTBW`, `KBOX` |
| `product_type` | Product type indicator (see below) | `TO.W`, `SV.A`, `AFD` |
| `awipsid` | Full AWIPS/AFOS product identifier | `TORALY`, `AFDDMX`, `ZFPBOX` |
| `product_id` | Unique IEM product identifier | `202307131915-KALY-WFUS51-TORALY` |

## Product Type Determination

The `product_type` component is determined using the following priority:

1. **VTEC Codes (Priority 1)**: If the product contains VTEC (Valid Time Event Code) information, the first VTEC record's `phenomena.significance` is used.
2. **AWIPS ID Prefix (Priority 2)**: If no VTEC codes are present, the first 3 characters of the AWIPS ID are used (converted to uppercase).
3. **Fallback (Priority 3)**: If neither VTEC nor sufficient AWIPS ID is available, `GENERAL` is used.

### VTEC-Based Product Types

For products with VTEC codes, the format is `{phenomena}.{significance}`:

| Product Type | Description | Example Products |
|--------------|-------------|------------------|
| `TO.W` | Tornado Warning | Tornado warnings |
| `SV.W` | Severe Thunderstorm Warning | Severe thunderstorm warnings |
| `SV.A` | Severe Thunderstorm Watch | Severe thunderstorm watches |
| `FF.W` | Flash Flood Warning | Flash flood warnings |
| `FL.W` | Flood Warning | River flood warnings |
| `FL.Y` | Flood Advisory | Minor flooding advisories |
| `WS.W` | Winter Storm Warning | Winter storm warnings |
| `WW.Y` | Winter Weather Advisory | Winter weather advisories |

### AWIPS ID-Based Product Types

For products without VTEC codes, the first 3 characters of the AWIPS ID are used:

| Product Type | Description | Example AWIPS IDs |
|--------------|-------------|-------------------|
| `AFD` | Area Forecast Discussion | `AFDDMX`, `AFDALY`, `AFDBOX` |
| `ZFP` | Zone Forecast Product | `ZFPBOX`, `ZFPALY`, `ZFPDMX` |
| `NOW` | Short Term Forecast | `NOWPHI`, `NOWALY`, `NOWBOX` |
| `HWO` | Hazardous Weather Outlook | `HWODMX`, `HWOALY`, `HWOBOX` |
| `LSR` | Local Storm Report | `LSRDMX`, `LSRALY`, `LSRBOX` |

## Example Topics

### Warning Products (with VTEC)
```
nwws/KALY/TO.W/TORALY/202307131915-KALY-WFUS51-TORALY
nwws/KTBW/SV.W/SVRALY/202307132030-KTBW-WFUS51-SVRALY
nwws/KBOX/FF.W/FFWBOX/202307132100-KBOX-WFUS51-FFWBOX
```

### Forecast Products (without VTEC)
```
nwws/KDMX/AFD/AFDDMX/202307131830-KDMX-FXUS63-AFDDMX
nwws/KPHI/ZFP/ZFPPHI/202307131700-KPHI-FXUS61-ZFPPHI
nwws/KALY/NOW/NOWALY/202307132200-KALY-FXUS61-NOWALY
```

## Subscription Patterns

MQTT supports wildcard subscriptions using `+` (single level) and `#` (multi-level) wildcards:

### By Weather Station
```bash
# All products from Tampa Bay (KTBW)
nwws/KTBW/#

# All products from Albany (KALY)
nwws/KALY/#
```

### By Product Type (All Stations)
```bash
# All tornado warnings from any station
nwws/+/TO.W/#

# All area forecast discussions from any station
nwws/+/AFD/#

# All severe thunderstorm watches from any station
nwws/+/SV.A/#
```

### By Significance Level
```bash
# All warnings (any phenomena) from Tampa Bay
nwws/KTBW/+.W/#

# All watches (any phenomena) from any station
nwws/+/+.A/#

# All advisories (any phenomena) from Albany
nwws/KALY/+.Y/#
```

### Specific Product Types from Specific Stations
```bash
# Tornado warnings from Tampa Bay
nwws/KTBW/TO.W/#

# Area forecast discussions from Des Moines
nwws/KDMX/AFD/#

# Flash flood warnings from Boston
nwws/KBOX/FF.W/#
```

### Complex Filtering Examples
```bash
# All severe weather warnings (tornado, severe thunderstorm, flash flood)
nwws/+/TO.W/# nwws/+/SV.W/# nwws/+/FF.W/#

# All forecast products from a specific station
nwws/KALY/AFD/# nwws/KALY/ZFP/# nwws/KALY/NOW/#

# All winter weather products from any station
nwws/+/WS.W/# nwws/+/WW.A/# nwws/+/WW.Y/#
```

## Configuration

### Topic Prefix

The topic prefix can be configured via the `topic_prefix` setting (default: `nwws`):

```python
config = MQTTOutputConfig(
    broker="localhost",
    topic_prefix="weather"  # Changes topics to weather/KALY/TO.W/...
)
```

### Custom Topic Patterns

The topic pattern can be customized via the `topic_pattern` setting. Available variables:

- `{prefix}`: The configured topic prefix
- `{cccc}`: The 4-character station identifier
- `{product_type}`: The determined product type
- `{awipsid}`: The full AWIPS ID
- `{product_id}`: The unique product identifier

#### Example Custom Patterns

```python
# Reverse order pattern
topic_pattern = "{prefix}/{product_type}/{cccc}/{product_id}"
# Results in: nwws/TO.W/KALY/202307131915-KALY-WFUS51-TORALY

# Simplified pattern (no AWIPS ID)
topic_pattern = "{prefix}/{cccc}/{product_type}/{product_id}"
# Results in: nwws/KALY/TO.W/202307131915-KALY-WFUS51-TORALY

# Product-first pattern for type-based filtering
topic_pattern = "{prefix}/{product_type}/{cccc}/{awipsid}"
# Results in: nwws/TO.W/KALY/TORALY
```

## Benefits

1. **Station-Based Filtering**: Easy subscription to all products from specific weather offices
2. **Product Type Filtering**: Efficient filtering by warning/watch/advisory types
3. **Standardized Categories**: Uses official NWS VTEC codes for consistent categorization
4. **No Hardcoded Logic**: Relies entirely on pyIEM fields, automatically adapting to NWS changes
5. **Flexible Patterns**: Configurable topic structure for different use cases
6. **Hierarchical Structure**: Natural filtering from general to specific

## Migration Notes

If upgrading from a previous version with a different topic structure:

1. **Old Format**: `nwws/{cccc}/{awipsid}/{product_id}`
2. **New Format**: `nwws/{cccc}/{product_type}/{awipsid}/{product_id}`

The main change is the addition of the `{product_type}` level between `{cccc}` and `{awipsid}`. Existing subscriptions will need to be updated to include the product type level or use wildcards appropriately.

## Future Extensibility

The pattern-based approach allows for easy customization of topic structures without code changes. Future enhancements might include:

- Additional variables (e.g., `{severity}`, `{urgency}`)
- Environment-specific prefixes
- Geographic region groupings
- Time-based organization