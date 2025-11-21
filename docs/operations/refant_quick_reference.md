# Quick Reference: Outrigger Refant Selection

## For Pipeline Users

### What Changed?

Production calibration scripts now automatically use **all 15 outrigger
antennas** as reference antenna fallback chain, instead of just antenna 103.

### Why?

- Antenna 103 was frequently flagged, causing CASA to fall back to core antennas
- Core antennas provide poor calibration quality (short baselines only)
- Full outrigger chain ensures high-quality calibration even when individual
  antennas fail

### Quick Usage

#### 1. Default (No Changes Needed)

Production scripts automatically use the new refant chain:

```bash
# No changes needed - scripts updated automatically
python ops/pipeline/build_central_calibrator_group.py <args>
```

#### 2. Get Refant String for Manual Use

```bash
# Simple output
python scripts/recommend_refant.py
# Output: 104,105,106,107,108,109,110,111,112,113,114,115,116,103,117

# Detailed information
python scripts/recommend_refant.py --verbose
```

#### 3. Optimize Based on Previous Calibration

```bash
# Analyze antenna health from calibration table
python scripts/recommend_refant.py --caltable /path/to/previous.bcal --verbose
```

#### 4. Use in Custom Scripts

```python
from dsa110_contimg.calibration.refant_selection import get_default_outrigger_refants

refant = get_default_outrigger_refants()
# Use in CASA tasks
bandpass(vis='obs.ms', refant=refant, ...)
```

## Default Outrigger Priority

**Primary** (Eastern - Best Coverage):

- 104, 105, 106, 107, 108

**Secondary** (Northern - Good Azimuth):

- 109, 110, 111, 112, 113

**Tertiary** (Western/Peripheral):

- 114, 115, 116, 103, 117

**Note**: Antenna 103 (original hardcoded choice) is now 14th in priority.

## Troubleshooting

### Problem: Calibration still failing with new refant chain

**Solution**: Check antenna health with diagnostic tool:

```bash
python scripts/recommend_refant.py --caltable <your_cal.bcal> --verbose
```

Look for problematic antennas (>80% flagged) and investigate array status.

### Problem: Need to use specific refant for testing

**Solution**: Override in your script:

```python
# For testing specific antenna
refant = '104'  # or any other antenna ID

# For testing specific chain
refant = '104,105,106'  # first 3 only
```

### Problem: Want to check which refant CASA actually used

**Solution**: Check CASA log output:

```
grep "refant" casa-*.log
```

CASA will log which antenna from the chain it selected.

## FAQ

**Q: Why not just use antenna 104 instead of 103?**  
A: Individual antennas can fail unpredictably. Using a chain of 15 antennas
ensures robustness.

**Q: Will this slow down calibration?**  
A: No. CASA selects the first healthy antenna from the chain immediately.

**Q: Can I still use the old way (refant='103')?**  
A: Yes, but not recommended. The new chain is strictly better - it includes 103
as fallback.

**Q: How do I know if an antenna is healthy?**  
A: Use the CLI tool with --verbose flag on a recent calibration table.

**Q: Does this affect imaging or only calibration?**  
A: Only calibration. Refant is a calibration-solve parameter, not used in
imaging.

## Production Script Locations

Updated files:

- `ops/pipeline/build_calibrator_transit_offsets.py`
- `ops/pipeline/build_central_calibrator_group.py`

Core module:

- `src/dsa110_contimg/calibration/refant_selection.py`

CLI tool:

- `scripts/recommend_refant.py`

## Getting Help

For questions or issues:

1. Check detailed docs: `docs/reports/OUTRIGGER_REFANT_IMPLEMENTATION.md`
2. Run diagnostic: `python debug_0834_calibration.py <ms> <caltable>`
3. Check antenna health:
   `python scripts/recommend_refant.py --caltable <cal> --verbose`
