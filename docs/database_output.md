# Database Output Module

The Database Output module provides persistent storage for NWWS pipeline events using SQLAlchemy with support for multiple database backends.

## Features

- **Multiple Database Support**: SQLite, PostgreSQL, MySQL, and other SQLAlchemy-supported databases
- **Automatic Schema Creation**: Tables are created automatically if they don't exist
- **Event Deduplication**: Prevents duplicate events from being stored
- **Comprehensive Metadata Storage**: Stores both pipeline metadata and custom metadata
- **Content Separation**: Raw and processed content stored separately for efficiency
- **Connection Pooling**: Configurable connection pooling for production environments
- **Error Handling**: Robust error handling with transaction rollback

## Database Schema

The module creates three main tables:

### weather_events
- Primary event information (AWIPS ID, CCCC, timestamps, etc.)
- Indexed columns for efficient querying
- Unique constraint on event_id

### weather_event_content
- Raw NOAA Port content
- Processed content (JSON for text products, XML for XML events)
- One-to-one relationship with weather_events

### weather_event_metadata
- Pipeline metadata (source, stage, timestamps)
- Custom metadata from events
- Key-value pairs for flexible storage

## Configuration

### Basic Configuration

```python
from nwws.outputs.database import DatabaseConfig, DatabaseOutput

# SQLite (for development/testing)
config = DatabaseConfig(
    database_url="sqlite:///weather_events.db",
    create_tables=True
)

# PostgreSQL (for production)
config = DatabaseConfig(
    database_url="postgresql://user:password@localhost/weather_db",
    pool_size=10,
    max_overflow=20,
    echo_sql=False
)
```

### Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `database_url` | `"sqlite:///weather_events.db"` | SQLAlchemy database URL |
| `echo_sql` | `False` | Log SQL statements |
| `pool_size` | `5` | Connection pool size (non-SQLite) |
| `max_overflow` | `10` | Maximum overflow connections |
| `pool_timeout` | `30` | Timeout for getting connection |
| `pool_recycle` | `3600` | Connection recycle time (seconds) |
| `create_tables` | `True` | Auto-create tables if missing |

## Usage

### Basic Usage

```python
import asyncio
from nwws.outputs.database import DatabaseConfig, DatabaseOutput

async def main():
    config = DatabaseConfig(database_url="sqlite:///weather.db")
    output = DatabaseOutput(config=config)
    
    await output.start()
    try:
        # Send events through pipeline
        await output.send(weather_event)
    finally:
        await output.stop()

asyncio.run(main())
```

### Pipeline Integration

```python
from nwws.pipeline import Pipeline
from nwws.outputs.database import DatabaseConfig, DatabaseOutput

# Create pipeline with database output
config = DatabaseConfig(database_url="postgresql://user:pass@localhost/weather")
db_output = DatabaseOutput(output_id="weather-db", config=config)

pipeline = Pipeline()
pipeline.add_output(db_output)
```

## Supported Event Types

The database output handles all `NoaaPortEventData` subclasses:

- **NoaaPortEventData**: Basic NOAA Port events
- **TextProductEventData**: Text products with JSON processing
- **XmlEventData**: XML events with XML content storage

Non-NOAA Port events are automatically skipped.

## Database URL Examples

### SQLite
```python
# File-based SQLite
database_url = "sqlite:///path/to/weather.db"

# In-memory SQLite (testing only)
database_url = "sqlite:///:memory:"
```

### PostgreSQL
```python
# Basic PostgreSQL
database_url = "postgresql://user:password@localhost/weather_db"

# With specific port and options
database_url = "postgresql://user:pass@localhost:5432/weather?sslmode=require"
```

### MySQL
```python
# MySQL
database_url = "mysql+pymysql://user:password@localhost/weather_db"
```

## Performance Considerations

### Production Recommendations

1. **Use PostgreSQL or MySQL** for production environments
2. **Configure connection pooling** appropriately:
   ```python
   config = DatabaseConfig(
       database_url="postgresql://user:pass@localhost/weather",
       pool_size=20,
       max_overflow=30,
       pool_recycle=3600
   )
   ```
3. **Monitor database size** - content can grow quickly
4. **Index additional columns** if needed for your queries
5. **Set up regular maintenance** (VACUUM for PostgreSQL, etc.)

### SQLite Limitations

- Single writer limitation
- No connection pooling
- Suitable for development/testing only
- File locking issues in high-concurrency scenarios

## Monitoring and Statistics

The database output provides runtime statistics:

```python
stats = db_output.stats
print(f"Events stored: {stats['events_stored']}")
print(f"Events failed: {stats['events_failed']}")
print(f"Last event: {stats['last_event_time']}")

# Check connection status
if db_output.is_connected:
    print("Database is connected")
```

## Error Handling

The module includes comprehensive error handling:

- **Connection failures**: Logged with retry capability
- **Duplicate events**: Silently skipped (not errors)
- **Transaction failures**: Automatic rollback
- **Schema issues**: Clear error messages

## Querying Stored Data

### Direct SQL Queries

```sql
-- Get recent weather events
SELECT event_id, awipsid, cccc, subject, created_at 
FROM weather_events 
ORDER BY created_at DESC 
LIMIT 10;

-- Get events with content
SELECT we.product_id, we.subject, wec.processed_content
FROM weather_events we
JOIN weather_event_content wec ON we.id = wec.event_id
WHERE we.event_type = 'text_product';

-- Query metadata
SELECT we.product_id, wem.key, wem.value
FROM weather_events we
JOIN weather_event_metadata wem ON we.id = wem.event_id
WHERE wem.key LIKE 'custom_%';
```

### Using SQLAlchemy

```python
from sqlalchemy.orm import Session
from nwws.outputs.database import WeatherEvent, WeatherEventContent

with Session(engine) as session:
    # Query recent events
    recent_events = session.query(WeatherEvent)\
        .order_by(WeatherEvent.created_at.desc())\
        .limit(10)\
        .all()
    
    # Query with content
    events_with_content = session.query(WeatherEvent)\
        .join(WeatherEventContent)\
        .filter(WeatherEvent.event_type == 'text_product')\
        .all()
```

## Security Considerations

1. **Database credentials**: Store in environment variables
2. **URL masking**: Passwords are automatically masked in logs
3. **SQL injection**: Protected by SQLAlchemy ORM
4. **Network security**: Use SSL/TLS for remote databases

## Troubleshooting

### Common Issues

1. **Connection failures**
   - Check database URL format
   - Verify database server is running
   - Check network connectivity and firewall rules

2. **Permission errors**
   - Ensure database user has CREATE TABLE permissions
   - Check file permissions for SQLite databases

3. **High memory usage**
   - Monitor connection pool size
   - Consider content archiving for large deployments

4. **Slow performance**
   - Add indexes on frequently queried columns
   - Monitor database size and consider partitioning
   - Tune connection pool settings

### Debug Mode

Enable SQL logging for debugging:

```python
config = DatabaseConfig(
    database_url="your_database_url",
    echo_sql=True  # Shows all SQL statements
)
```

## Migration and Maintenance

### Schema Updates

The module uses SQLAlchemy's metadata to create tables. For schema changes:

1. Update model definitions in `database.py`
2. Use Alembic for production migrations
3. Test changes thoroughly with sample data

### Data Retention

Implement data retention policies based on your needs:

```sql
-- Example: Delete events older than 30 days
DELETE FROM weather_events 
WHERE created_at < NOW() - INTERVAL '30 days';
```