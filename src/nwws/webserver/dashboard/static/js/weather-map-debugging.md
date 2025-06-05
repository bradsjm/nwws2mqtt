# Weather Map Debugging Guide

This document describes the debugging features and fixes implemented in the WeatherOfficeMap class to help troubleshoot data updating issues.

## Issues Addressed

### 1. New Offices Not Appearing After Initial Load
**Problem**: When new weather offices start sending data, they don't appear on the map even though the active office counter increases.

**Solution**: Added detection logic in `updateActivityLevels()` that:
- Tracks existing office IDs on the map
- Compares against activity data to find new offices
- Dispatches a `newOfficesDetected` event to trigger boundary reload

### 2. Last Message Time Always Shows Latest Retrieval Time
**Problem**: All offices show the same "last activity" time instead of their actual last message time.

**Solution**: Enhanced validation and logging to help identify if the issue is:
- Frontend timestamp formatting
- Backend providing incorrect timestamps
- Data transmission issues

### 3. Recent Activity Border Highlighting Not Working
**Problem**: Offices with recent activity should have highlighted borders, but this wasn't working consistently.

**Solution**: 
- Fixed typo in popup update ("layr" → "layer")
- Enhanced recent activity detection with better error handling
- Added comprehensive validation for activity data structure

## New Debugging Features

### Debug Mode Control
Enable detailed logging for recent activity detection:
```javascript
// Enable debug mode
weatherMap.setDebugMode(true);

// Disable debug mode
weatherMap.setDebugMode(false);
```

### Activity Data Validation
Automatically validates activity data structure and logs issues:
```javascript
// Manual validation
const issues = weatherMap.validateActivityData(activityData);
console.log("Validation issues:", issues);
```

### Comprehensive Activity Data Debug
Get detailed information about all office activity:
```javascript
// Debug all activity data
weatherMap.debugActivityData();
```

### Map State Summary
Get overview of current map state:
```javascript
const summary = weatherMap.getMapSummary();
console.log("Map summary:", summary);
// Returns:
// {
//   totalOffices: 120,
//   officesOnMap: 118,
//   officesWithRecentActivity: 5,
//   officesByActivityLevel: { idle: 110, low: 5, medium: 2, high: 1, error: 0 },
//   selectedOffice: "KBOU",
//   rainViewerEnabled: false,
//   pollingInterval: 5000
// }
```

### Individual Office Information
Get detailed info about a specific office:
```javascript
const info = weatherMap.getOfficeInfo("KBOU");
console.log("Office info:", info);
// Returns:
// {
//   officeId: "KBOU",
//   onMap: true,
//   activity: { last_activity: 1640995200, activity_level: "medium", ... },
//   activityLevel: "medium",
//   hasRecentActivity: true,
//   isSelected: false,
//   properties: { name: "Boulder", region: "CR", ... }
// }
```

### Force Office Updates
Manually update a specific office's styling and popup:
```javascript
// Force update for specific office
const updated = weatherMap.forceUpdateOffice("KBOU");
console.log("Office updated:", updated);
```

### Check for New Offices
Manually trigger detection of new offices:
```javascript
const newOffices = weatherMap.checkForNewOffices();
console.log("New offices found:", newOffices);
```

## Event Handling

### New Offices Detected Event
Listen for when new offices are detected:
```javascript
document.addEventListener('newOfficesDetected', (event) => {
    console.log('New offices detected:', event.detail);
    // Trigger reload of office boundaries
    loadOfficeBoundaries();
});
```

### Office Selection Event
Listen for office selection changes:
```javascript
document.addEventListener('officeSelected', (event) => {
    console.log('Office selected:', event.detail.officeId);
});
```

## Troubleshooting Common Issues

### Issue: Offices not updating visually
**Check:**
1. Verify activity data is being received: `weatherMap.debugActivityData()`
2. Check if office exists on map: `weatherMap.getOfficeInfo(officeId)`
3. Force update: `weatherMap.forceUpdateOffice(officeId)`

### Issue: Recent activity highlighting not working
**Check:**
1. Enable debug mode: `weatherMap.setDebugMode(true)`
2. Verify timestamp format in activity data
3. Check polling interval setting: `weatherMap.pollingInterval`

### Issue: New offices not appearing
**Check:**
1. Monitor for new office events: Listen to `newOfficesDetected`
2. Manually check: `weatherMap.checkForNewOffices()`
3. Verify boundary data includes new offices

### Issue: Popup showing wrong data
**Check:**
1. Verify activity data structure: `weatherMap.validateActivityData()`
2. Check specific office data: `weatherMap.getOfficeInfo(officeId)`
3. Force popup refresh: `weatherMap.forceUpdateOffice(officeId)`

## Enhanced Logging

The updated code provides structured logging for:
- Activity data validation issues
- Recent activity detection details
- New office discovery
- Update operation results
- Error conditions with context

All logging respects the debug mode setting to prevent console spam while still providing essential information.

## Best Practices

1. **Enable debug mode temporarily** when investigating issues
2. **Use the summary function** to get quick overview of map state
3. **Check for new offices periodically** if you suspect missing offices
4. **Validate activity data** when data seems inconsistent
5. **Monitor browser console** for automatic validation warnings

## Data Validation

The system now validates:
- Activity data object structure
- Timestamp validity and reasonableness
- Required field presence and types
- Future or very old timestamps (potential data issues)

Validation issues are logged as warnings but don't prevent map operation.