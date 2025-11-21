# CASA Calibration Status

## Check Results

**Status**: Calibration did not complete

**Findings**:

- MS file exists: `/scratch/ms/timesetv3/caltables/2025-10-29T13:54:17.cal.ms`
- No calibration tables found (_bpcal_, _gpcal_)
- Calibration process is not currently running

## Possible Reasons

1. Calibration may have failed silently
2. Calibration may have been interrupted
3. Calibration tables may be in a different location
4. Calibration may still be in progress (unlikely)

## Next Steps

1. Re-run calibration with fixed phase centers:

   ```bash
   python -m dsa110_contimg.calibration.cli calibrate \
     --ms /scratch/ms/timesetv3/caltables/2025-10-29T13:54:17.cal.ms \
     --auto-fields \
     --preset standard
   ```

2. Or proceed with CubiCal testing (independent of CASA calibration)
