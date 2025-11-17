# Image Gallery Filters Implementation

**Date:** 2025-11-14  
**Component:** `ImageBrowser.tsx` (Sky View Page)

## Summary

Extended the Image Gallery filtering system with advanced filters including date
range, declination range, quality threshold, and calibrator detection flag. All
filters are synchronized with URL query parameters for shareable filtered views.

## Changes Made

### 1. Extended `ImageFilters` Type (`frontend/src/api/types.ts`)

Added new filter fields:

- `start_date?: string` - ISO date string (UTC) for start date
- `end_date?: string` - ISO date string (UTC) for end date
- `dec_min?: number` - Declination minimum (degrees)
- `dec_max?: number` - Declination maximum (degrees)
- `noise_max?: number` - Maximum noise level (Jy)
- `has_calibrator?: boolean` - Calibrator detected flag

### 2. Updated `useImages` Hook (`frontend/src/api/queries.ts`)

Extended the hook to pass new filter parameters to the API:

- `start_date` - ISO date string
- `end_date` - ISO date string
- `dec_min` - Declination minimum (degrees)
- `dec_max` - Declination maximum (degrees)
- `noise_max` - Maximum noise level (Jy)
- `has_calibrator` - Boolean flag

### 3. Enhanced `ImageBrowser` Component (`frontend/src/components/Sky/ImageBrowser.tsx`)

#### New Features:

1. **URL Query Parameter Synchronization**
   - Filters are read from URL params on component mount
   - Filters are written to URL params when changed
   - Shareable filtered views via URL

2. **Advanced Filters UI** (Collapsible Section)
   - **Date Range Filters:**
     - Start Date (UTC) - DateTimePicker
     - End Date (UTC) - DateTimePicker
     - Uses MUI DateTimePicker with dayjs adapter

   - **Declination Range Filter:**
     - Range slider (-90° to +90°)
     - Real-time value display
     - Marks at -90°, 0°, and 90°

   - **Quality Threshold Filter:**
     - TextField for maximum noise level
     - Input in mJy (converted to Jy for API)
     - Helper text: "Leave empty for no limit"

   - **Calibrator Detected Flag:**
     - Checkbox control
     - Label: "Has Calibrator Detected"

3. **UI Improvements:**
   - Collapsible advanced filters section
   - Expand/collapse icon button
   - Clear visual separation between basic and advanced filters
   - Consistent Material-UI component styling

## Filter Implementation Details

### Date Range Filter

- **Component:** `DateTimePicker` from `@mui/x-date-pickers`
- **Format:** ISO 8601 date strings (UTC)
- **Storage:** Stored as ISO strings in filters, converted from Dayjs objects
- **URL Param:** `start_date`, `end_date`

### Declination Range Filter

- **Component:** `Slider` from `@mui/material`
- **Range:** -90° to +90°
- **Step:** 0.1 degrees
- **Display:** Shows current range values
- **URL Params:** `dec_min`, `dec_max`

### Quality Threshold Filter

- **Component:** `TextField` (number type)
- **Unit:** mJy (display) → Jy (API)
- **Conversion:** User input in mJy, converted to Jy for API call
- **URL Param:** `noise_max` (stored in Jy)

### Calibrator Detected Flag

- **Component:** `Checkbox` with `FormControlLabel`
- **Type:** Boolean
- **URL Param:** `has_calibrator` (true/false string)

## URL Query Parameter Format

Example URL with filters:

```
/sky?start_date=2025-01-01T00:00:00Z&end_date=2025-01-31T23:59:59Z&dec_min=-30&dec_max=30&noise_max=0.001&has_calibrator=true&image_type=image&pbcor=true
```

## API Endpoint Support

The implementation assumes the backend `GET /api/images` endpoint supports these
query parameters:

- `start_date` - ISO date string
- `end_date` - ISO date string
- `dec_min` - Float (degrees)
- `dec_max` - Float (degrees)
- `noise_max` - Float (Jy)
- `has_calibrator` - Boolean string ("true"/"false")

**Note:** If the backend doesn't support these parameters yet, they will be sent
but may be ignored. The frontend implementation is complete and ready for
backend support.

## Testing

Test file location:
`/data/dsa110-contimg/src/dsa110_contimg/frontend/src/pages/SkyView/__tests__/ImageGallery.test.tsx`

Test cases should verify:

1. Declination range filtering
2. Quality threshold (noise level) filtering
3. Calibrator detected flag filtering
4. Date range filtering
5. URL parameter synchronization
6. Filter persistence across page reloads

## Usage Example

```typescript
// Filters are automatically synced with URL
// User can share filtered views via URL

// Example: Filter images from last week with declination -30° to +30°
// URL: /sky?start_date=2025-01-15T00:00:00Z&end_date=2025-01-22T23:59:59Z&dec_min=-30&dec_max=30
```

## Dependencies

- `@mui/x-date-pickers` - Date/time picker components
- `@mui/x-date-pickers/AdapterDayjs` - Dayjs adapter for date pickers
- `react-router-dom` - URL parameter management (`useSearchParams`)
- `dayjs` - Date manipulation and formatting

## Future Enhancements

1. **Filter Presets:** Save/load common filter combinations
2. **Filter Chips:** Display active filters as removable chips
3. **Clear Filters Button:** Reset all filters to defaults
4. **Filter Validation:** Ensure start_date < end_date, dec_min < dec_max
5. **Backend Integration:** Verify and implement backend support for all filters

---

**Status:** ✅ Implementation Complete  
**Backend Support:** ⚠️ Pending verification
