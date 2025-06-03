# Database Cleanup Feature

The Database Output module includes an intelligent cleanup system that automatically removes expired weather events based on National Weather Service (NWS) product specifications and timing standards.

## Overview

Weather data has varying validity periods depending on the product type. The cleanup system uses multiple strategies to determine when data should be removed:

1. **Product Expiration**: Uses explicit expiration times from NWS products
2. **VTEC Event Timing**: Leverages Valid Time Event Code (VTEC) event ending times
3. **Product-Specific Retention**: Applies different retention periods based on product types
4. **Age-Based Fallback**: Default time-based cleanup for products without specific timing

## Configuration

### Basic Configuration

```python
from nwws.outputs.database import DatabaseConfig, DatabaseOutput

config = DatabaseConfig(
    database_url="sqlite:///weather_events.db",

    # Enable cleanup
    cleanup_enabled=True,
    cleanup_interval_hours=6,  # Run cleanup every 6 hours

    # Safety settings
    dry_run_mode=False,  # Set to True for testing
    max_deletions_per_cycle=500,

    # NWS timing compliance
    respect_product_expiration=True,
    respect_vtec_expiration=True,
    respect_ugc_expiration=True,
    use_product_specific_retention=True,
)

db_output = DatabaseOutput(output_id="weather-db", config=config)
```

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cleanup_enabled` | `False` | Enable/disable automatic cleanup |
| `cleanup_interval_hours` | `6` | How often to run cleanup (hours) |
| `dry_run_mode` | `False` | Test mode - log what would be deleted without actually deleting |
| `max_deletions_per_cycle` | `500` | Maximum events to delete per cleanup cycle |
| `respect_product_expiration` | `True` | Use NWS product expiration times |
| `respect_vtec_expiration` | `True` | Use VTEC event ending times |
| `respect_ugc_expiration` | `True` | Use UGC (Universal Geographic Code) expiration times |
| `use_product_specific_retention` | `True` | Apply product-type-specific retention rules |
| `vtec_expiration_buffer_hours` | `2` | Keep data N hours past VTEC expiration |
| `default_retention_days` | `7` | Default retention for products without specific rules |

### Product-Specific Retention Periods

| Parameter | Default | Product Types |
|-----------|---------|---------------|
| `short_duration_retention_hours` | `1` | TOR, SVR, EWW, SMW (Warnings) |
| `medium_duration_retention_hours` | `24` | FFW, FLW, CFW (Flood/Coastal products) |
| `long_duration_retention_hours` | `72` | WSW, FFA (Watches, Winter weather) |
| `routine_retention_hours` | `12` | ZFP, NOW (Forecasts, Short-term) |
| `administrative_retention_days` | `30` | PNS, LSR, PSH (Reports, Statements) |

## Cleanup Strategies

### 1. Product Expiration-Based Cleanup

Removes products that have passed their documented expiration times. Based on NWS standards:
- Watch/Warning/Advisory products: ≤24 hours from issuance
- Uses UGC expiration times stored in product metadata

### 2. VTEC Event-Based Cleanup

Uses Valid Time Event Code (VTEC) timing information:
- Respects event beginning and ending times from P-VTEC strings
- Handles "Until Further Notice" events (coded as `000000T0000Z`)
- Applies configurable buffer time past event expiration

### 3. Product-Type-Specific Cleanup

Applies retention rules based on NWS product specifications:

#### Short-Duration Products (1 hour retention)
- **TOR**: Tornado Warning (15-45 minutes validity)
- **SVR**: Severe Thunderstorm Warning (30-60 minutes validity)
- **EWW**: Extreme Wind Warning (up to 3 hours)
- **SMW**: Special Marine Warning

#### Medium-Duration Products (24 hours retention)
- **FFW**: Flash Flood Warning
- **FLW**: Flood Warning
- **CFW**: Coastal Flood Warning

#### Long-Duration Products (72 hours retention)
- **WSW**: Winter Storm Warning/Watch
- **FFA**: Flood Watch

#### Routine Products (12 hours retention)
- **ZFP**: Zone Forecast Product
- **NOW**: Short Term Forecast
- **SPS**: Special Weather Statement

#### Administrative Products (30 days retention)
- **PNS**: Public Information Statement
- **LSR**: Local Storm Report
- **PSH**: Post Tropical Cyclone Report

### 4. Age-Based Fallback Cleanup

For products without specific timing information:
- Uses `default_retention_days` setting
- Applied after other cleanup methods
- Ensures no data accumulates indefinitely

## Usage

### Automatic Cleanup

Cleanup runs automatically when enabled:

```python
config = DatabaseConfig(
    cleanup_enabled=True,
    cleanup_interval_hours=6,
)

db_output = DatabaseOutput(config=config)
await db_output.start()  # Cleanup scheduler starts automatically
```

### Manual Cleanup

Trigger cleanup manually:

```python
# Trigger immediate cleanup
results = await db_output.trigger_cleanup()

print(f"Deleted {results.total_deleted} events:")
print(f"  Product expired: {results.product_expired}")
print(f"  Event expired: {results.event_expired}")
print(f"  Product specific: {results.product_specific}")
print(f"  Time based: {results.time_based}")
```

### Monitoring Cleanup

Check cleanup status and configuration:

```python
# Get cleanup statistics
cleanup_stats = db_output.get_cleanup_stats()
print(f"Cleanup enabled: {cleanup_stats['cleanup_enabled']}")
print(f"Service running: {cleanup_stats['cleanup_service_running']}")
print(f"Dry run mode: {cleanup_stats['dry_run_mode']}")

# Check database connection
if db_output.is_connected:
    print("Database connected")

# Get general database statistics
stats = db_output.stats
print(f"Events stored: {stats['events_stored']}")
print(f"Events failed: {stats['events_failed']}")
```

## Configuration Examples

### Development/Testing Configuration

```python
config = DatabaseConfig(
    database_url="sqlite:///test_weather.db",

    # Conservative cleanup for testing
    cleanup_enabled=True,
    cleanup_interval_hours=1,  # Frequent cleanup for testing
    dry_run_mode=True,  # Don't actually delete
    max_deletions_per_cycle=100,

    # Longer retention for analysis
    default_retention_days=3,
    short_duration_retention_hours=6,
    medium_duration_retention_hours=48,
)
```

### Production Configuration

```python
config = DatabaseConfig(
    database_url="postgresql://user:pass@localhost/weather_db",

    # Efficient production cleanup
    cleanup_enabled=True,
    cleanup_interval_hours=4,  # Clean every 4 hours
    dry_run_mode=False,
    max_deletions_per_cycle=5000,

    # Standard retention periods
    respect_product_expiration=True,
    respect_vtec_expiration=True,
    use_product_specific_retention=True,

    # Optimized for storage efficiency
    vtec_expiration_buffer_hours=1,
    default_retention_days=5,

    # Database performance
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600,
)
```

### Archival/Research Configuration

```python
config = DatabaseConfig(
    database_url="postgresql://user:pass@archive-db/weather_archive",

    # Extended retention for research
    cleanup_enabled=True,
    cleanup_interval_hours=24,  # Daily cleanup

    # Keep data longer for research
    respect_product_expiration=False,  # Don't use product expiration
    respect_vtec_expiration=True,      # But respect event timing
    use_product_specific_retention=True,

    # Extended retention periods
    short_duration_retention_hours=24,   # Keep warnings 1 day
    medium_duration_retention_hours=168, # Keep flood products 1 week
    long_duration_retention_hours=720,   # Keep watches 30 days
    administrative_retention_days=365,   # Keep reports 1 year

    # Conservative deletion limits
    max_deletions_per_cycle=1000,
    vtec_expiration_buffer_hours=24,  # Large safety buffer
    default_retention_days=30,
)
```

## Safety Features

### Dry Run Mode

Test cleanup without deleting data:

```python
config = DatabaseConfig(
    cleanup_enabled=True,
    dry_run_mode=True,  # Log what would be deleted
)
```

### Deletion Limits

Prevent accidental mass deletion:

```python
config = DatabaseConfig(
    max_deletions_per_cycle=1000,  # Limit deletions per cycle
)
```

### Buffer Times

Keep data past official expiration for safety:

```python
config = DatabaseConfig(
    vtec_expiration_buffer_hours=2,  # Keep 2 hours past VTEC expiration
)
```

### Graceful Degradation

If intelligent cleanup fails, system falls back to time-based cleanup.

## Monitoring and Logging

The cleanup service provides detailed logging:

```
INFO - Starting database cleanup scheduler interval_hours=6 dry_run=False
DEBUG - Deleted expired events events=42 content_records=42 metadata_records=158 reason=vtec_expiration
INFO - Database cleanup completed product_expired=15 event_expired=42 product_specific=23 time_based=8 total_deleted=88
```

### Log Levels

- **INFO**: Cleanup start/stop, completion summaries
- **DEBUG**: Detailed deletion counts by category
- **WARNING**: Non-fatal cleanup failures, deletion limits exceeded
- **ERROR**: Critical cleanup failures

## Best Practices

### Production Deployment

1. **Start with dry run mode** to understand deletion patterns
2. **Monitor logs** for unexpected deletion volumes
3. **Set conservative deletion limits** initially
4. **Use database-specific optimizations** (connection pooling)
5. **Schedule cleanup during low-traffic periods**

### Database Maintenance

1. **Monitor database size** trends after enabling cleanup
2. **Vacuum/optimize** database periodically (especially SQLite)
3. **Index frequently queried columns** for cleanup performance
4. **Set up monitoring alerts** for cleanup failures

### Configuration Tuning

1. **Adjust retention periods** based on storage capacity and requirements
2. **Tune cleanup frequency** based on data volume
3. **Monitor cleanup duration** and adjust batch sizes
4. **Test configuration changes** in dry run mode first

## Troubleshooting

### Common Issues

#### Cleanup Not Running
- Check `cleanup_enabled=True`
- Verify database connection
- Check logs for startup errors

#### High Memory Usage
- Reduce `max_deletions_per_cycle`
- Increase `cleanup_interval_hours`
- Monitor database connection pool

#### Slow Cleanup Performance
- Add indexes on `created_at`, `awipsid` columns
- Tune database connection pool settings
- Consider running cleanup during off-peak hours

#### Unexpected Deletions
- Enable `dry_run_mode` to test
- Review retention period settings
- Check product-specific rules

### Debug Commands

```python
# Check if cleanup service is running
cleanup_stats = db_output.get_cleanup_stats()
print(f"Service running: {cleanup_stats['cleanup_service_running']}")

# Test cleanup in dry run mode
config.dry_run_mode = True
results = await db_output.trigger_cleanup()
print(f"Would delete: {results.total_deleted}")

# Check database connection
if not db_output.is_connected:
    print("Database connection issue")
```

## Migration Considerations

When upgrading to include cleanup functionality:

1. **Backup existing data** before enabling cleanup
2. **Start with longer retention periods** than needed
3. **Monitor data deletion** patterns for several cycles
4. **Gradually reduce retention periods** as confidence increases
5. **Document custom retention requirements** for your use case

The cleanup system is designed to be conservative by default, ensuring data safety while providing flexible configuration for various deployment scenarios.
