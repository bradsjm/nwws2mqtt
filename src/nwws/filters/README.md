# NWWS Filters Package

The filters package provides pipeline event filtering capabilities for the NWWS2MQTT system. Filters allow you to selectively process or reject events based on configurable criteria, helping to reduce noise and focus on relevant weather data.

## Overview

Filters are used in the pipeline to determine whether an event should continue through the processing chain. They implement a simple boolean interface: `should_process(event) -> bool`. Filters are applied before transformers and outputs, making them efficient for early rejection of unwanted data.

## Architecture

All filters inherit from the base `Filter` class provided by the pipeline framework:

```python
from nwws.pipeline.filters import Filter

class MyFilter(Filter):
    def should_process(self, event: PipelineEvent) -> bool:
        # Return True to continue processing, False to reject
        return True
```

## Available Filters

### DuplicateFilter

Rejects duplicate weather products within a configurable time window to prevent redundant processing.

**Key Features:**
- Time-based duplicate detection using product ID
- Configurable time window (default: 5 minutes)
- Automatic cleanup of expired entries
- Cache statistics for monitoring

**Usage Example:**
```python
from nwws.filters import DuplicateFilter

# Create with default 5-minute window
filter = DuplicateFilter()

# Create with custom 10-minute window
filter = DuplicateFilter("my-duplicate-filter", window_seconds=600.0)

# Check if event should be processed
if filter.should_process(event):
    # Process the event
    pass

# Get cache statistics
stats = filter.get_cache_stats()
print(f"Tracking {stats['total_tracked']} products")
```

**Configuration:**
- `filter_id`: Unique identifier for the filter instance
- `window_seconds`: Time window in seconds to track duplicates (default: 300.0)

**Behavior:**
- Uses the event's `id` attribute as the product identifier
- Maintains an in-memory cache of recently seen product IDs with timestamps
- Automatically cleans up expired entries during processing
- Allows events without product IDs to pass through with a warning

### TestMessageFilter

Filters out test messages that have an AWIPS ID of 'TSTMSG', preventing test data from being processed in production.

**Key Features:**
- Case-insensitive test message detection
- Minimal performance impact
- Detailed logging of filtering decisions

**Usage Example:**
```python
from nwws.filters import TestMessageFilter

# Create the filter
filter = TestMessageFilter()

# Check if event should be processed
if filter.should_process(event):
    # Process non-test messages
    pass
```

**Configuration:**
- `filter_id`: Unique identifier for the filter instance (default: "test-msg-filter")

**Behavior:**
- Checks the event's `awipsid` attribute
- Rejects events where `awipsid` equals 'TSTMSG' (case-insensitive)
- Allows events without `awipsid` attribute to pass through

## Filter Metadata

All filters provide detailed metadata about their filtering decisions through the `get_filter_decision_metadata()` method. This metadata is useful for debugging, monitoring, and understanding why events were filtered.

**Example Metadata:**
```python
{
    "filter_id": "duplicate-filter",
    "filter_type": "DuplicateFilter",
    "filter_result": False,
    "duplicate-filter_product_id": "FXUS61KBOU",
    "duplicate-filter_total_tracked": 150,
    "duplicate-filter_time_since_last_seconds": 45.2,
    "duplicate-filter_reason": "duplicate_within_window"
}
```

## Performance Considerations

### DuplicateFilter
- **Memory Usage**: O(n) where n is the number of unique products within the time window
- **Time Complexity**: O(1) for duplicate checking, O(k) for cleanup where k is expired entries
- **Cleanup Strategy**: Automatic cleanup on each filter evaluation to prevent memory leaks

### TestMessageFilter
- **Memory Usage**: O(1) - no state maintained
- **Time Complexity**: O(1) - simple string comparison
- **Performance Impact**: Minimal - just a string comparison per event

## Error Handling

Filters are designed to be robust and handle edge cases gracefully:

- **Missing Attributes**: Events without required attributes (e.g., `id`, `awipsid`) are allowed to pass through with warnings
- **Invalid Data Types**: Non-string values are handled gracefully with appropriate logging
- **Cleanup Failures**: Automatic cleanup operations are logged but don't affect filtering decisions

## Custom Filter Development

To create a custom filter:

1. **Inherit from Filter**: Use the base `Filter` class from the pipeline framework
2. **Implement should_process()**: Return `True` to allow processing, `False` to reject
3. **Add Metadata**: Override `get_filter_decision_metadata()` for debugging information
4. **Handle Edge Cases**: Gracefully handle missing or invalid data

**Example Custom Filter:**
```python
from nwws.pipeline.filters import Filter
from nwws.pipeline.types import PipelineEvent

class ProductTypeFilter(Filter):
    def __init__(self, filter_id: str = "product-type-filter", allowed_types: set[str] | None = None):
        super().__init__(filter_id)
        self.allowed_types = allowed_types or set()
    
    def should_process(self, event: PipelineEvent) -> bool:
        if not hasattr(event, 'product_type'):
            return True  # Allow events without product_type
        
        product_type = getattr(event, 'product_type', '')
        return product_type in self.allowed_types
    
    def get_filter_decision_metadata(self, event: PipelineEvent, *, result: bool) -> dict[str, Any]:
        metadata = super().get_filter_decision_metadata(event, result=result)
        
        if hasattr(event, 'product_type'):
            product_type = getattr(event, 'product_type', '')
            metadata[f"{self.filter_id}_product_type"] = product_type
            metadata[f"{self.filter_id}_allowed_types"] = list(self.allowed_types)
        
        return metadata
```

## Integration with Pipeline

Filters are typically configured in the pipeline configuration file:

```yaml
filters:
  - type: DuplicateFilter
    config:
      filter_id: "duplicate-filter"
      window_seconds: 300.0
  
  - type: TestMessageFilter
    config:
      filter_id: "test-msg-filter"
```

## Monitoring and Debugging

### Logging
All filters provide structured logging with contextual information:
- Filter decisions (accept/reject)
- Performance metrics
- Error conditions
- Cache statistics (for stateful filters)

### Statistics
Use filter-specific statistics methods:
```python
# For DuplicateFilter
stats = duplicate_filter.get_cache_stats()
logger.info("Duplicate filter stats", **stats)
```

### Pipeline Integration
Filters integrate with the pipeline's error handling and statistics collection:
- Filter errors are captured and logged
- Performance metrics are collected automatically
- Filter metadata is included in pipeline events

## Best Practices

1. **Fail Open**: Design filters to allow events through when in doubt
2. **Log Decisions**: Provide clear logging for debugging filter behavior
3. **Handle Edge Cases**: Gracefully handle missing or malformed data
4. **Monitor Performance**: Track filter performance and memory usage
5. **Test Thoroughly**: Test filters with various event types and edge cases
6. **Clean Up Resources**: Ensure stateful filters clean up expired data

## Thread Safety

All provided filters are thread-safe:
- **DuplicateFilter**: Uses thread-safe operations for cache management
- **TestMessageFilter**: Stateless, inherently thread-safe

When creating custom filters, ensure thread safety if the filter maintains state.