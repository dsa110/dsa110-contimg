# Pointing Visualization - User Guide

**Last Updated:** 2025-11-07  
**Status:** Production Ready

---

## Quick Start

1. **Access Dashboard**: Navigate to `http://localhost:5173/` (or your frontend
   URL)
2. **View Visualization**: The pointing visualization appears on the main
   dashboard
3. **Monitor Status**: Check the status indicators at the top of the
   visualization

---

## Understanding the Visualization

### Visual Elements

#### Current Pointing Position

- **Green Circle Marker**: Shows the most recent telescope pointing position
- **Size**: Larger marker (15px) for visibility
- **Updates**: Every 30-60 seconds automatically

#### Historical Trail

- **Blue Line**: Connects past pointing positions
- **Opacity**: 50% for trail, 30% for markers
- **Time Range**: Default 7 days (configurable)
- **Markers**: Sparse markers every Nth point for performance

### Coordinate System

- **X-Axis**: Right Ascension (0-360 degrees)
- **Y-Axis**: Declination (-90 to +90 degrees)
- **Grid**: 30-degree intervals
- **Units**: Degrees (decimal)

### Status Indicators

#### Monitor Status Chip

- **Green "Monitoring"**: Service is running and healthy
- **Gray "Stopped"**: Service is not running
- **Red "Unhealthy"**: Service has issues

#### Metrics Display

- **Current RA**: Right Ascension in degrees (4 decimal places)
- **Current Dec**: Declination in degrees (4 decimal places)
- **Files Processed**: Total number of files processed by monitor
- **Success Rate**: Percentage of successful processing

---

## Interactive Features

### Hover Tooltips

- Hover over any point to see:
  - RA coordinate
  - Dec coordinate
  - Current vs Historical distinction

### Zoom & Pan

- **Zoom**: Mouse wheel or pinch gesture
- **Pan**: Click and drag
- **Reset**: Double-click or use toolbar buttons

### Plot Controls

- **Zoom**: Select area to zoom in
- **Pan**: Move around the plot
- **Reset**: Return to default view
- **Download**: Export plot as PNG

---

## Status Messages

### Normal Operation

- **"Waiting for pointing data..."**: No data available yet (normal on first
  start)
- **Status indicators show green**: Everything working correctly

### Warnings

- **"Pointing monitor is not running"**: Service stopped
  - **Action**: Check service status:
    `sudo systemctl status contimg-pointing-monitor.service`
- **"Pointing monitor health check failed"**: Service has issues
  - **Action**: Check logs:
    `sudo journalctl -u contimg-pointing-monitor.service -n 50`

### No Data

- **"No pointing data available"**: Database is empty
  - **Normal**: If no files have been processed yet
  - **Action**: Wait for new observation files to arrive

---

## Data Updates

### Update Frequency

- **Monitor Status**: Every 30 seconds
- **Pointing History**: Every 60 seconds
- **Automatic**: No manual refresh needed

### When New Data Appears

1. New `*_sb00.hdf5` file arrives in `/data/incoming/`
2. Pointing monitor detects and processes it
3. Pointing data stored in database
4. Visualization updates within 30-60 seconds
5. New point appears on plot
6. Historical trail extends

---

## Troubleshooting

### Visualization Not Showing

**Check 1: Frontend Server**

```bash
curl http://localhost:5173
```

Should return HTML. If not, start frontend:

```bash
cd /data/dsa110-contimg/frontend
npm run dev
```

**Check 2: API Server**

```bash
curl http://localhost:8000/api/pointing-monitor/status
```

Should return JSON. If not, check API service.

**Check 3: Browser Console**

- Open browser developer tools (F12)
- Check Console tab for errors
- Check Network tab for failed API requests

### No Data Displayed

**Check Database:**

```bash
sqlite3 /data/dsa110-contimg/state/products.sqlite3 \
  "SELECT COUNT(*) FROM pointing_history;"
```

**Check Monitor:**

```bash
sudo systemctl status contimg-pointing-monitor.service
cat /data/dsa110-contimg/state/pointing-monitor-status.json | jq
```

**Check API:**

```bash
curl "http://localhost:8000/api/pointing_history?start_mjd=60300&end_mjd=60400" | jq
```

### Data Not Updating

**Check Monitor Logs:**

```bash
sudo journalctl -u contimg-pointing-monitor.service -f
```

**Check for New Files:**

```bash
ls -lt /data/incoming/*_sb00.hdf5 | head -5
```

**Verify Processing:**

- Monitor should log: "Processed pointing from file: ..."
- Database count should increase
- Status file should show `files_processed` increasing

### Performance Issues

**If Plot is Slow:**

- Reduce `historyDays` prop (default: 7)
- Disable history: `showHistory={false}`
- Check data volume: Large datasets may be slow

**If Updates are Slow:**

- Check network latency
- Verify API response times
- Check browser performance

---

## Configuration

### Component Props

```typescript
<PointingVisualization
  height={500}           // Plot height in pixels
  showHistory={true}     // Show historical trail
  historyDays={7}        // Days of history to display
/>
```

### Customization

**Change History Range:**

```tsx
<PointingVisualization historyDays={14} /> // 2 weeks
```

**Disable History:**

```tsx
<PointingVisualization showHistory={false} /> // Current only
```

**Adjust Height:**

```tsx
<PointingVisualization height={600} /> // Taller plot
```

---

## API Reference

### Endpoints Used

**Monitor Status:**

```
GET /api/pointing-monitor/status
```

Returns monitor health and metrics.

**Pointing History:**

```
GET /api/pointing_history?start_mjd=X&end_mjd=Y
```

Returns pointing entries in MJD range.

### Data Format

**Pointing Entry:**

```json
{
  "timestamp": 60986.73,
  "ra_deg": 204.5,
  "dec_deg": 54.01
}
```

**Monitor Status:**

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

---

## Best Practices

### For Operators

1. **Monitor Status**: Check status indicators regularly
2. **Watch Trail**: Historical trail shows observation patterns
3. **Verify Updates**: Ensure data updates when files arrive
4. **Check Health**: Monitor health warnings

### For Developers

1. **Error Handling**: Component handles missing data gracefully
2. **Performance**: Sparse markers optimize large datasets
3. **Updates**: Automatic refresh reduces manual intervention
4. **Testing**: Test with empty, sparse, and dense datasets

---

## Related Documentation

- **Deployment**: `docs/how-to/pointing-monitor-deployment.md`
- **API Reference**: `docs/reference/dashboard_backend_api.md`
- **Testing (archived)**: `docs/archive/reports/POINTING_VISUALIZATION_TEST.md`

---

## Support

**Issues?**

1. Check troubleshooting section above
2. Review monitor logs
3. Verify API endpoints
4. Check browser console for errors

**Questions?**

- See technical documentation: `docs/how-to/pointing-visualization.md`
- Check API documentation: `docs/reference/dashboard_api.md`

---

**Status**: ✅ Production Ready  
**Version**: 1.0.0  
**Last Updated**: 2025-11-07
