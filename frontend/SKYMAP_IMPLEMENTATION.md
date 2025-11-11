# Interactive Sky Map Implementation

**Date:** 2025-01-XX  
**Component:** `SkyMap.tsx` (Sky View Page)

## Summary

Implemented an interactive sky coverage map component that displays telescope pointing history and observed field positions. The component uses Plotly.js for visualization and follows the existing `PointingVisualization` component patterns.

## API Endpoints Used

### 1. `/api/pointing_history`
- **Endpoint:** `GET /api/pointing_history?start_mjd={start}&end_mjd={end}`
- **Hook:** `usePointingHistory(startMjd, endMjd)`
- **Returns:** `PointingHistoryList` with items containing:
  - `timestamp: number` - Unix timestamp
  - `ra_deg: number` - Right Ascension (degrees)
  - `dec_deg: number` - Declination (degrees)
- **Purpose:** Telescope pointing positions over time

### 2. `/api/images`
- **Endpoint:** `GET /api/images?limit=1000`
- **Hook:** `useImages({ limit: 1000 })`
- **Returns:** `ImageList` with items containing:
  - `center_ra_deg?: number` - Field center RA (degrees)
  - `center_dec_deg?: number` - Field center Dec (degrees)
  - `created_at: string` - Observation timestamp
  - `noise_jy?: number` - Noise level (Jy)
  - `type: string` - Image type
  - Other image metadata
- **Purpose:** Observed field positions and metadata

## Component Features

### Visualization

1. **Pointing History Trail**
   - Line plot showing telescope pointing path
   - Color-coded by observation time (blue = older, red = recent)
   - Sparse markers for performance (max 50 recent points)
   - Hover tooltips with RA/Dec and timestamp

2. **Observed Fields**
   - Scatter plot of field center positions
   - Color-coded by observation time (purple = older, yellow = recent)
   - Size-coded by noise level (lower noise = larger marker)
   - Hover tooltips with field name, RA/Dec, noise, and timestamp
   - Clickable markers to view field details

3. **Plot Layout**
   - RA axis: 0-360 degrees
   - Dec axis: -90 to +90 degrees
   - Dark theme matching dashboard style
   - Grid lines for easy coordinate reading
   - Legend showing data series

### Interactivity

1. **Click Handling**
   - Click on observed field markers opens detail dialog
   - Dialog shows:
     - Image path
     - RA/Dec coordinates
     - Observation time
     - Image type
     - Noise level
     - Beam parameters
     - Field size

2. **Hover Tooltips**
   - Pointing history: RA, Dec, timestamp
   - Observed fields: Field name, RA, Dec, noise, timestamp

### UI Components

- **Material-UI Card:** Paper component for layout
- **Loading State:** CircularProgress with message
- **Error Handling:** Alert component for API errors
- **Status Chips:** Display count of pointing measurements and observed fields
- **Dialog:** Material-UI Dialog for field details

## Component Props

```typescript
interface SkyMapProps {
  height?: number;              // Plot height in pixels (default: 600)
  historyDays?: number;         // Days of pointing history to show (default: 7)
  showPointingHistory?: boolean; // Show telescope pointing trail (default: true)
  showObservedFields?: boolean;  // Show observed field positions (default: true)
}
```

## Integration

The component is integrated into `SkyViewPage.tsx`:

```typescript
<SkyMap
  height={500}
  historyDays={7}
  showPointingHistory={true}
  showObservedFields={true}
/>
```

Placed at the top of the Sky View page, above the image browser and viewer.

## Data Processing

### Pointing History
- Converts MJD range to Unix timestamps for date range calculation
- Normalizes timestamps for color interpolation
- Filters to recent points for marker display (performance)

### Observed Fields
- Filters images to only those with RA/Dec coordinates
- Normalizes observation times for color interpolation
- Calculates marker sizes based on noise level (inverted: lower noise = larger)
- Stores image ID in customdata for click handling

## Color Coding

### Pointing History
- **Color Scale:** Blue (old) → Red (recent)
- **Interpolation:** RGB(0, 100, 255) → RGB(255, 100, 0)

### Observed Fields
- **Color Scale:** Purple (old) → Yellow (recent)
- **Interpolation:** RGB(0, 0, 255) → RGB(255, 200, 0)

## Performance Considerations

1. **Data Limiting**
   - Pointing history: Shows sparse markers (max 50 recent points)
   - Observed fields: Limited to 1000 images (configurable via limit)

2. **Plot Optimization**
   - Uses Plotly.js for efficient rendering
   - Sparse marker display for large datasets
   - Responsive plot sizing

3. **Memoization**
   - `useMemo` for plot data and layout calculation
   - Prevents unnecessary recalculations

## Styling

- Matches existing `PointingVisualization` component style
- Dark theme (`#1e1e1e` background)
- White text and grid lines
- Consistent with dashboard Material-UI theme

## Dependencies

- `react-plotly.js` - Plotly.js React wrapper (already installed)
- `plotly.js` - Plotting library (already installed)
- `@mui/material` - Material-UI components
- `dayjs` - Date formatting

## Future Enhancements

1. **Zoom and Pan Controls**
   - Add Plotly zoom/pan controls
   - Save zoom state in URL params

2. **Time Range Filter**
   - Add date range picker for pointing history
   - Filter observed fields by observation time

3. **Field Selection**
   - Click field in map → select in ImageBrowser
   - Highlight selected field on map

4. **Coverage Heatmap**
   - Density visualization of observed fields
   - Show gaps in coverage

5. **Calibrator Positions**
   - Overlay calibrator positions on map
   - Color-code by calibrator quality

6. **Export Options**
   - Export map as PNG
   - Export field list as CSV

## Testing

Test cases should verify:
1. Pointing history displays correctly
2. Observed fields display correctly
3. Click handling opens dialog with correct data
4. Color coding reflects observation time
5. Marker sizes reflect noise levels
6. Loading states display correctly
7. Error handling displays alerts
8. Empty states display correctly

## Known Limitations

1. **Field Count Limit**
   - Currently fetches up to 1000 images
   - May need pagination for large datasets

2. **Coordinate Availability**
   - Only displays fields with RA/Dec coordinates
   - Some images may not have coordinates

3. **Performance**
   - Large datasets may slow rendering
   - Consider virtualization for 1000+ fields

---

**Status:** ✅ Implementation Complete  
**Backend Support:** ✅ Endpoints Available

