# Phase 1: 16-SPW Adaptive Binning Test Results

**Date:** 2025-11-09  
**Test Type:** Full 16-SPW adaptive binning with parallel imaging  
**MS:** `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:45:34.ms`  
**Target:** RA=124.526792°, Dec=54.620694° (known source)

## Test Configuration

- **Target SNR:** 5.0
- **Max bin width:** 4
- **Image size:** 512 pixels
- **Quality tier:** development
- **Backend:** tclean
- **Parallel workers:** 4
- **Total SPWs:** 16

## Results Summary

### Performance
- **Total runtime:** ~23.5 minutes (1413 seconds)
- **SPW imaging time:** ~1.5 minutes per SPW average (with 4 parallel workers)
- **All 16 SPWs imaged successfully**
- **Parallel imaging:** ✓ Working correctly

### Detections
- **Total detections:** 13 out of 16 SPWs
- **SNR range:** 6.71 - 11.60
- **All detections above target SNR (5.0):** ✓ Yes
- **Binning used:** No (all detections used bin_width=1)

### Detection Details

| SPW | SNR | Flux (Jy) | RMS (Jy) | Bin Width | Freq (MHz) |
|-----|-----|-----------|----------|-----------|------------|
| 0   | 10.83 | 0.001372 | 0.000127 | 1 | 1317.1 |
| 2   | 7.49  | 0.001275 | 0.000170 | 1 | 1340.6 |
| 3   | 10.00 | 0.001480 | 0.000148 | 1 | 1352.3 |
| 4   | 6.71  | 0.001074 | 0.000160 | 1 | 1364.0 |
| 6   | 7.98  | 0.001201 | 0.000151 | 1 | 1387.4 |
| 7   | 7.79  | 0.001190 | 0.000153 | 1 | 1399.2 |
| 8   | 9.51  | 0.001334 | 0.000140 | 1 | 1410.9 |
| 9   | 11.60 | 0.001454 | 0.000125 | 1 | 1422.6 |
| 10  | 9.35  | 0.001314 | 0.000141 | 1 | 1434.3 |
| 11  | 9.14  | 0.001189 | 0.000130 | 1 | 1446.0 |
| 13  | 8.57  | 0.001166 | 0.000136 | 1 | 1469.5 |
| 14  | 9.57  | 0.000933 | 0.000097 | 1 | 1481.2 |
| 15  | 7.75  | 0.000794 | 0.000102 | 1 | 1492.9 |

**SPWs without detections:** 1, 5, 12

## Observations

1. **No binning required:** All detections achieved SNR > 5.0 using single SPWs (bin_width=1). This indicates the source is bright enough that adaptive binning wasn't necessary for this target.

2. **Frequency coverage:** Detections span the full frequency range (1317-1493 MHz), showing good spectral coverage.

3. **Parallel imaging:** The 4-worker parallel implementation successfully reduced imaging time compared to sequential processing.

4. **Missing SPWs:** SPWs 1, 5, and 12 did not produce detections above the SNR threshold. This could be due to:
   - RFI or calibration issues in those specific frequency ranges
   - Lower source flux at those frequencies
   - Higher noise in those SPWs

## Next Steps

1. **Test wider bins:** Run with lower target SNR or weaker sources to exercise the adaptive binning algorithm (bin_width > 1).

2. **Test multiple sources:** Run adaptive binning on multiple known sources simultaneously.

3. **Investigate missing SPWs:** Check SPWs 1, 5, and 12 for RFI or calibration issues.

4. **Pipeline integration:** Integrate adaptive binning into the main pipeline orchestrator.

## Files Generated

- **SPW images:** `/tmp/adaptive_binning_16spw/spw_images/*.pbcor.fits` (16 images)
- **Results JSON:** `/tmp/adaptive_binning_results.json`
- **Log file:** `/tmp/adaptive_binning_16spw_parallel.log`

