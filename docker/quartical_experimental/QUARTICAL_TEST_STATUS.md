# QuartiCal Testing Status

## Configuration Created

Created QuartiCal configuration file:
- Location: `/scratch/calibration_test/quartical_config.yaml`
- Format: Based on QuartiCal documentation examples
- Terms: Bandpass (B) and Gain (G) calibration

## MS File Information

- **Path**: `/scratch/ms/timesetv3/quartical/2025-10-29T13:54:17.qrtcal.ms`
- **Size**: ~5.1 GB
- **Fields**: 24 (meridian fields with time-dependent phase centers)
- **Spectral Windows**: 16 (48 channels each, ~1311-1487 MHz)
- **Antennas**: 117
- **Rows**: 1,787,904

## Current Status

QuartiCal command runs but exits immediately with only a deprecation warning.
This suggests:
1. Configuration format may need adjustment
2. May need MODEL_DATA column populated first
3. May need to check QuartiCal's actual CLI interface

## Next Steps

1. Verify QuartiCal CLI interface and expected config format
2. Check if MODEL_DATA column exists in MS
3. Populate MODEL_DATA if needed (point source model for calibrator)
4. Adjust configuration based on actual QuartiCal requirements
5. Re-run calibration

## Notes

- QuartiCal installed successfully
- All dependencies resolved
- Configuration file created
- Need to verify correct usage format
