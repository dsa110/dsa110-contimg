# Radio Astronomy Workflow Improvements Needed

## Critical Issues (High Priority)

### 1. Calibration Table Compatibility Validation
**Problem**: No validation that existing calibration tables match the MS file
- **Risk**: Applying calibration from wrong observation/frequency/antenna set
- **Solution**: Add validation checks:
  - Verify antennas in cal table match MS antennas
  - Verify frequency ranges overlap
  - Check time ranges are reasonable
  - Warn if cal table is from different observation

### 2. Reference Antenna Validation
**Problem**: Refant '103' is hardcoded, no validation it exists
- **Risk**: Calibration fails silently or uses wrong antenna
- **Solution**: 
  - Dropdown showing available antennas from MS
  - Validate refant exists before calibration
  - Show antenna positions/health status

### 3. Flagging Statistics & Inspection
**Problem**: Cannot see what data is flagged
- **Risk**: Using bad data without knowing it
- **Solution**:
  - Display flagging summary (fraction flagged per antenna/baseline/frequency)
  - Show flagging reasons
  - Visual flagging map/plot

### 4. Data Column Warning
**Problem**: Can image uncorrected data without warning
- **Risk**: Accidentally imaging raw data that should be calibrated
- **Solution**:
  - Warn if imaging DATA column when CORRECTED_DATA exists
  - Warn if imaging CORRECTED_DATA when no calibration tables were applied
  - Check calibration was applied before imaging

### 5. Missing Critical Metadata
**Problem**: Essential information not displayed
- **Risk**: Making decisions without full context
- **Solution**: Display:
  - Field centers (RA/Dec) for each field
  - Antenna positions/geometry
  - Baseline statistics
  - UV coverage (min/max UV distance)
  - List of available antennas

## Important Issues (Medium Priority)

### 6. Calibration Solution Inspection
**Problem**: Cannot visually inspect calibration solutions
- **Solution**: Add plots:
  - Phase vs time (per antenna)
  - Amplitude vs frequency (bandpass)
  - Solution SNR plots
  - Flag fraction per antenna

### 7. Time Range Validation
**Problem**: No validation of time ranges
- **Solution**:
  - Validate start_time < end_time
  - Check MJD format
  - Warn if time range is suspiciously large/small
  - Display time range in multiple formats (MJD, ISO, etc.)

### 8. Phase Wrapping & Continuity Checks
**Problem**: No warnings about phase issues
- **Solution**:
  - Detect phase wrapping
  - Warn about large phase jumps
  - Check phase continuity across time/frequency

### 9. Bandpass Quality Visualization
**Problem**: Cannot inspect bandpass shape
- **Solution**: 
  - Plot bandpass amplitude vs frequency
  - Show bandpass phase
  - Highlight discontinuities

### 10. Flux Scale Display
**Problem**: Flux scale not visible
- **Solution**:
  - Display flux scale used (Perley-Butler 2017, etc.)
  - Show calibrator flux values
  - Allow flux scale selection

## Nice-to-Have (Lower Priority)

### 11. Image Coordinate System Info
- Display WCS information
- Show coordinate system/projection

### 12. UV Coverage Visualization
- Plot UV coverage
- Show missing baselines

### 13. Workflow Validation
- Check correct order of operations
- Warn about skipped steps

### 14. Calibrator Transit Information
- Show when calibrator transits
- Display calibrator elevation during observation

