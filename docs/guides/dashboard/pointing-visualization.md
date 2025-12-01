# Pointing Visualization Feature

**Date:** 2025-11-07  
**Status:** :check: Implemented  
**Location:** Dashboard Page

---

## Overview

The pointing visualization feature provides a live, interactive sky map showing
the DSA-110 telescope's current pointing position and historical pointing trail.
This enables real-time monitoring of telescope operations and analysis of sky
coverage.

---

## Features

### Live Pointing Display

- **Current Position**: Shows the most recent pointing position as a green
  marker
- **Real-time Updates**: Refreshes every 30 seconds from the pointing monitor
- **Status Indicators**: Displays monitor health and running status

### Historical Trail

- **Pointing History**: Shows pointing trail from the last 7 days (configurable)
- **Trail Visualization**: Blue line connecting historical pointing positions
- **Sparse Markers**: Displays markers at regular intervals for performance

### Interactive Features

- **Hover Tooltips**: Shows RA/Dec coordinates on hover
- **Zoom & Pan**: Plotly.js interactive controls
- **Responsive Design**: Adapts to screen size

---

## Component Details

### Location

- **Component**: `frontend/src/components/PointingVisualization.tsx`
- **Dashboard**: `frontend/src/pages/DashboardPage.tsx`
- **API Hook**: `frontend/src/api/queries.ts` - `usePointingHistory()`

### Props

```typescript
interface PointingVisualizationProps {
  height?: number; // Plot height in pixels (default: 500)
  showHistory?: boolean; // Show historical trail (default: true)
  historyDays?: number; // Days of history to show (default: 7)
}
```

### Data Sources

1. **Pointing Monitor Status**: `/api/pointing-monitor/status`
   - Provides monitor health and metrics
   - Updates every 30 seconds

2. **Pointing History**: `/api/pointing_history?start_mjd=X&end_mjd=Y`
   - Provides historical pointing data
   - Updates every 60 seconds
   - Automatically calculates MJD range from `historyDays`

---

## Usage

### In Dashboard

The pointing visualization is automatically displayed on the dashboard:

```tsx
<PointingVisualization height={500} showHistory={true} historyDays={7} />
```

### Standalone Usage

```tsx
import PointingVisualization from "../components/PointingVisualization";

<PointingVisualization
  height={600}
  showHistory={true}
  historyDays={14} // Show 2 weeks of history
/>;
```

---

## Visualization Details

### Coordinate System

- **X-axis**: Right Ascension (0-360 degrees)
- **Y-axis**: Declination (-90 to +90 degrees)
- **Grid**: 30-degree intervals for easy reading

### Visual Elements

- **Current Pointing**: Green circle marker (size 15)
- **Historical Trail**: Blue line (50% opacity, width 2)
- **Historical Points**: Blue markers (30% opacity, size 4, sparse)

### Color Scheme

- Matches dashboard dark theme (`#1e1e1e` background)
- White text for readability
- Green for current position (success indicator)
- Blue for historical data

---

## API Integration

### Endpoints Used

1. **Pointing Monitor Status**

   ```
   GET /api/pointing-monitor/status
   ```

   Returns:

   ```json
   {
     "running": true,
     "healthy": true,
     "metrics": {
       "files_processed": 1234,
       "success_rate_percent": 99.68
     }
   }
   ```

2. **Pointing History**
   ```
   GET /api/pointing_history?start_mjd=60300&end_mjd=60400
   ```
   Returns:
   ```json
   {
     "items": [
       {
         "timestamp": 60300.5,
         "ra_deg": 183.73,
         "dec_deg": 54.57
       }
     ]
   }
   ```

### Data Flow

```
Pointing Monitor :arrow_right: Database :arrow_right: API :arrow_right: Frontend Hook :arrow_right: Component :arrow_right: Plotly.js
```

---

## Performance Considerations

### Optimization Strategies

1. **Sparse Markers**: Only displays every Nth marker for large datasets
2. **Caching**: React Query caches data for 30 seconds
3. **Debounced Updates**: Status updates every 30 seconds, history every 60
   seconds
4. **Efficient Rendering**: Plotly.js handles large datasets efficiently

### Limits

- **History Days**: Default 7 days (configurable)
- **Marker Density**: Maximum 20 markers displayed (sparse sampling)
- **Update Frequency**: Status 30s, History 60s

---

## Status Indicators

### Monitor Status

- **Running**: Green chip "Monitoring"
- **Stopped**: Gray chip "Stopped"
- **Unhealthy**: Red chip "Unhealthy"

### Alerts

- **Monitor Not Running**: Warning alert
- **Health Check Failed**: Error alert with issue details

### Metrics Display

- Current RA/Dec coordinates
- Files processed count
- Success rate percentage

---

## Troubleshooting

### No Data Displayed

1. **Check Monitor Status**: Verify pointing monitor is running

   ```bash
   sudo systemctl status contimg-pointing-monitor.service
   ```

2. **Check Database**: Verify pointing data exists

   ```bash
   sqlite3 /data/dsa110-contimg/state/db/products.sqlite3 \
     "SELECT COUNT(*) FROM pointing_history;"
   ```

3. **Check API**: Test endpoint directly
   ```bash
   curl http://localhost:8000/api/pointing-monitor/status
   ```

### Visualization Not Updating

1. **Check Browser Console**: Look for API errors
2. **Verify Network**: Check API connectivity
3. **Check React Query**: Verify hooks are refreshing

### Performance Issues

1. **Reduce History Days**: Lower `historyDays` prop
2. **Disable History**: Set `showHistory={false}`
3. **Check Data Volume**: Verify database query performance

---

## Future Enhancements

### Potential Improvements

1. **Sky Map Projection**: Add Aitoff/Hammer projection option
2. **Time Slider**: Interactive time range selector
3. **Coverage Heatmap**: Show observation density
4. **Calibrator Overlay**: Show calibrator positions
5. **Export Functionality**: Export pointing data as CSV/JSON
6. **Custom Time Ranges**: User-selectable date ranges
7. **Animation**: Animate pointing trail over time

---

## Related Documentation

- **Pointing Monitor**: `docs/how-to/pointing-monitor-deployment.md`
- **API Reference**: `docs/reference/dashboard_backend_api.md`
- **Dashboard Guide**: `docs/how-to/control-panel-quickstart.md`

---

## Testing

### Manual Testing

1. Navigate to dashboard: `http://localhost:3000/`
2. Verify pointing visualization appears
3. Check status indicators
4. Hover over points to see coordinates
5. Test zoom/pan functionality

### Automated Testing

```bash
# Type check
cd frontend && npm run type-check

# Build test
cd frontend && npm run build
```

---

## Component Architecture

```
DashboardPage
  └── PointingVisualization
       ├── usePointingMonitorStatus() :arrow_right: API status
       ├── usePointingHistory() :arrow_right: API history
       └── Plotly.js :arrow_right: Visualization
```

---

**Status**: :check: Production Ready  
**Last Updated**: 2025-11-07
