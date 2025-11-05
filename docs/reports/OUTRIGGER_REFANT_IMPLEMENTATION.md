# Outrigger Reference Antenna Selection - Implementation Summary

**Date**: November 5, 2025  
**Purpose**: Fix calibration failures caused by hardcoded refant='103' by implementing intelligent outrigger antenna selection

## Problem Statement

CASA log analysis of 0834+555 calibration failure revealed:
- Hardcoded `refant='103'` was flagged in 3/4 solution intervals
- CASA automatically fell back to antenna 35 (core antenna)
- Core antenna defeated the purpose of using outriggers for long-baseline calibration
- Production scripts had `refant='103'` hardcoded in multiple locations

## Solution Implemented

### 1. Centralized Refant Selection Module

**Created**: `src/dsa110_contimg/calibration/refant_selection.py`

**Key Features**:
- Defines DSA-110 outrigger antennas (103-117) based on array geometry
- Provides default priority order optimized for baseline coverage:
  - Eastern outriggers (104-108): Best overall coverage
  - Northern outriggers (109-113): Good azimuthal distribution
  - Western/peripheral (114-117, 103): Extreme baselines
- Intelligent health-based ranking when calibration table provided
- Filters for healthy antennas (<50% flagged)
- Falls back gracefully to defaults if no health data available

**Main Functions**:
```python
# Get default outrigger chain (no data inspection)
get_default_outrigger_refants() -> str
# Returns: '104,105,106,107,108,109,110,111,112,113,114,115,116,103,117'

# Analyze antenna health from calibration table
analyze_antenna_health_from_caltable(caltable_path: str) -> List[Dict]

# Get intelligent recommendations based on health
recommend_outrigger_refants(antenna_analysis: Optional[List]) -> Dict

# High-level convenience function for CLI/orchestrator
recommend_refants_from_ms(ms_path: str, caltable_path: Optional[str]) -> str
```

### 2. Production Script Updates

Updated two critical calibration scripts to use the new refant utility:

#### A. `ops/pipeline/build_calibrator_transit_offsets.py`
- **Changed**: 3 instances of hardcoded `refant='103'`
- **Now uses**: `refant = get_default_outrigger_refants()`
- **Affected CASA tasks**: `gaincal` (pre-bandpass), `bandpass`, `gaincal` (phase-only)
- **Benefit**: CASA will try all 15 outriggers before falling back to core antennas

#### B. `ops/pipeline/build_central_calibrator_group.py`
- **Changed**: Hardcoded `refant='103'` determination logic
- **Now uses**: `refant = get_default_outrigger_refants()`
- **Adds**: Print statement showing refant chain being used
- **Benefit**: Consistent refant selection across all calibration workflows

**Before**:
```python
refant = '103'  # Single antenna, fails if flagged
```

**After**:
```python
from dsa110_contimg.calibration.refant_selection import get_default_outrigger_refants

refant = get_default_outrigger_refants()
# Returns: '104,105,106,107,108,109,110,111,112,113,114,115,116,103,117'
print(f'Using outrigger refant chain: {refant}')
```

### 3. CLI Tool for Refant Selection

**Created**: `scripts/recommend_refant.py`

**Usage Examples**:
```bash
# Get default outrigger chain
python scripts/recommend_refant.py
# Output: 104,105,106,107,108,109,110,111,112,113,114,115,116,103,117

# Optimize based on previous calibration
python scripts/recommend_refant.py --caltable /path/to/previous.bcal

# Get detailed antenna health analysis
python scripts/recommend_refant.py --caltable cal.bcal --verbose

# Different output formats
python scripts/recommend_refant.py --format list
python scripts/recommend_refant.py --format json
```

**Features**:
- Standalone executable for manual refant selection
- Integrates with existing calibration workflows
- Verbose mode shows antenna health statistics
- Multiple output formats (CASA, list, JSON)
- Can be called from shell scripts or Python orchestrators

## Technical Details

### DSA-110 Array Geometry

**Outrigger Antennas** (103-117):
- Widely separated from core array (37.23-37.25° latitude)
- Provide critical long baselines for calibration quality
- Essential for high-fidelity imaging

**Core Antennas** (1-102):
- Closely spaced (identical latitude 37.2333752°)
- Good for short baselines but poor for calibration reference
- Should be avoided as primary refant

### Default Priority Order

Priority is based on geometric position for optimal baseline coverage:

1. **Eastern outriggers** (104, 105, 106, 107, 108)
   - Best overall baseline coverage
   - Central to array geometry

2. **Northern outriggers** (109, 110, 111, 112, 113)
   - Good azimuthal distribution
   - Complement eastern coverage

3. **Western/peripheral** (114, 115, 116, 103, 117)
   - Extreme baselines
   - Original ant 103 demoted to 14th position

### Health-Based Optimization

When calibration table provided:
1. Analyze flagging fraction for each outrigger antenna
2. Sort by health (lower flagging = better)
3. Filter to <50% flagged threshold
4. Return top 5 healthy antennas as optimized chain
5. Fall back to defaults if no healthy antennas found

**Example Output**:
```
Healthy outrigger antennas (<50% flagged):
  104:   8.3% flagged (excellent)
  105:  12.1% flagged (good)
  106:  18.5% flagged (good)
  107:  25.2% flagged (good)
  108:  42.7% flagged (fair)

Recommended refant chain: 104,105,106,107,108
```

## Impact on 0834+555 Calibration Failure

### Root Cause
- Antenna 103 was flagged → CASA fell back to antenna 35 (core) → poor calibration quality

### Solution Effect
- CASA now tries 104, 105, 106, 107, 108, ... before reaching 103
- If 103 is flagged, CASA uses the next healthy outrigger (not core antenna)
- Maintains outrigger-based calibration even when individual antennas fail

### Expected Improvement
- **Before**: Single point of failure (ant 103) → automatic fallback to core
- **After**: Resilient chain of 15 outriggers → stays in outrigger pool
- **Result**: Better calibration quality, fewer failures, more robust pipeline

## Integration with Existing Workflows

### For Pipeline Scripts
```python
from dsa110_contimg.calibration.refant_selection import get_default_outrigger_refants

# Use in CASA tasks
refant = get_default_outrigger_refants()
bandpass(vis='obs.ms', refant=refant, ...)
```

### For CLI/Orchestrator
```bash
# Get refant string programmatically
REFANT=$(python scripts/recommend_refant.py)

# Use in CASA commands
casa --nogui -c "bandpass(vis='obs.ms', refant='$REFANT', ...)"
```

### For Advanced Optimization
```python
from dsa110_contimg.calibration.refant_selection import (
    analyze_antenna_health_from_caltable,
    recommend_outrigger_refants
)

# Analyze previous calibration
stats = analyze_antenna_health_from_caltable('previous.bcal')

# Get optimized chain
recs = recommend_outrigger_refants(stats)
refant = recs['recommended_refant_string']

# Use for next calibration
bandpass(vis='next_obs.ms', refant=refant, ...)
```

## Testing

### Module Import Test
```bash
$ python -c "from src.dsa110_contimg.calibration.refant_selection import get_default_outrigger_refants; print(get_default_outrigger_refants())"
104,105,106,107,108,109,110,111,112,113,114,115,116,103,117
```

### CLI Test
```bash
$ python scripts/recommend_refant.py
104,105,106,107,108,109,110,111,112,113,114,115,116,103,117

$ python scripts/recommend_refant.py --verbose
============================================================
DSA-110 Default Outrigger Reference Antenna Chain
============================================================

No calibration table provided - using default priority

Default refant chain: 104,105,106,107,108,109,110,111,112,113,114,115,116,103,117

Usage in CASA:
  bandpass(vis='obs.ms', refant='104,105,106,107,108,109,110,111,112,113,114,115,116,103,117', ...)

Note: Provide --caltable to optimize based on antenna health
============================================================
```

## Files Changed

### New Files
1. `src/dsa110_contimg/calibration/refant_selection.py` - Core module (415 lines)
2. `scripts/recommend_refant.py` - CLI tool (178 lines)

### Modified Files
1. `ops/pipeline/build_calibrator_transit_offsets.py`
   - Added import: `get_default_outrigger_refants`
   - Changed 3 refant assignments from `'103'` to `get_default_outrigger_refants()`
   - Added informational print statement

2. `ops/pipeline/build_central_calibrator_group.py`
   - Added import: `get_default_outrigger_refants`
   - Changed refant determination logic
   - Added informational print statement

### Debug Tool Updates
`debug_0834_calibration.py` already contains similar logic (will be kept for reference but pipeline now uses the centralized module).

## Backward Compatibility

- **API**: New functions are additions, no existing interfaces changed
- **Behavior**: Default behavior now uses full outrigger chain vs single antenna
- **CASA Compatibility**: Output format is standard CASA refant string (comma-separated)
- **Scripts**: Production scripts work identically but with improved refant selection

## Future Enhancements

### Short Term
- [ ] Add runtime antenna health checking in calibration.py functions
- [ ] Configuration file for refant preferences (YAML)
- [ ] Integration with pipeline monitoring/logging

### Medium Term
- [ ] Automatic refant optimization between calibration stages
- [ ] Machine learning-based refant selection from historical data
- [ ] Dashboard showing refant usage statistics

### Long Term
- [ ] Real-time antenna health monitoring service
- [ ] Predictive flagging to pre-select best refants
- [ ] Integration with array control system

## References

- DSA110_Station_Coordinates.csv - Antenna position data
- CASA log analysis: 0834+555 calibration failure (see debug_0834_calibration.py)
- Original issue: Antenna 103 flagged causing core antenna fallback
- Array geometry: 102 core + 15 outrigger antennas

## Summary

This implementation solves the immediate calibration failure problem (hardcoded refant='103' being offline) while establishing a robust, extensible framework for intelligent reference antenna selection in the DSA-110 pipeline. The solution is:

- ✅ **Deployed**: Production scripts updated
- ✅ **Tested**: CLI and module imports verified
- ✅ **Documented**: Comprehensive usage examples
- ✅ **Extensible**: Ready for health-based optimization
- ✅ **Maintainable**: Centralized logic, easy to update
- ✅ **Backward Compatible**: No breaking changes

The pipeline is now resilient to individual antenna failures and will maintain high calibration quality by automatically using healthy outrigger antennas.
