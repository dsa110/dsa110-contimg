# Phase 1: Wider Bins Adaptive Binning Test Results

**Date:** 2025-11-09  
**Test Type:** Adaptive binning with higher target SNR to force binning  
**MS:** `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:45:34.ms`  
**Target:** RA=124.526792°, Dec=54.620694° (known source)

## Test Configuration

- **Target SNR:** 8.0 (higher than previous test to force binning)
- **Max bin width:** 4
- **Image size:** 512 pixels
- **Quality tier:** development
- **Backend:** tclean
- **Parallel workers:** 4
- **Max SPWs:** 8 (for faster testing)

## Results Summary

### Performance
- **Total runtime:** ~13.6 minutes (818 seconds)
- **SPW imaging time:** ~1.7 minutes per SPW average (with 4 parallel workers)
- **All 8 SPWs imaged successfully**

### Detections
- **Total detections:** 3
- **Adaptive binning triggered:** ✓ Yes
- **Max bin width used:** 2
- **Binned detections:** 1 out of 3

### Detection Details

| Detection | SPWs | SNR | Flux (Jy) | RMS (Jy) | Bin Width | Freq (MHz) |
|-----------|------|-----|-----------|----------|-----------|------------|
| 1 | 6, 7 | 11.15 | 0.001195 | 0.000107 | **2** | 1393.3 |
| 2 | 8 | 9.51 | 0.001334 | 0.000140 | 1 | 1410.9 |
| 3 | 9 | 11.60 | 0.001454 | 0.000125 | 1 | 1422.6 |

## Key Findings

1. **Adaptive binning working correctly:** The algorithm successfully combined SPWs 6 and 7 to achieve SNR=11.15, exceeding the target SNR of 8.0.

2. **Binning strategy:** When individual SPWs (6 and 7) couldn't reach SNR=8.0 alone, the algorithm combined them into a single bin (bin_width=2), achieving the target SNR.

3. **Selective binning:** Not all SPWs required binning. SPWs 8 and 9 individually exceeded SNR=8.0, so they remained unbinned (bin_width=1).

4. **Performance:** Parallel imaging continued to work correctly, processing 8 SPWs in ~13.6 minutes.

## Comparison with Previous Test

| Metric | SNR=5.0 Test | SNR=8.0 Test |
|--------|--------------|--------------|
| Detections | 13 | 3 |
| Max bin width | 1 | 2 |
| Binning used | No | Yes |
| SPWs processed | 16 | 8 |

The higher target SNR (8.0) successfully forced adaptive binning, demonstrating that the algorithm correctly combines SPWs when individual SPWs cannot achieve the target SNR.

## Next Steps

1. **Test multiple sources:** Run adaptive binning on multiple known sources simultaneously.

2. **Test with even higher SNR:** Test with SNR=10.0 or higher to force wider bins (bin_width=3 or 4).

3. **Pipeline integration:** Integrate adaptive binning into the main pipeline orchestrator.

## Files Generated

- **SPW images:** `/tmp/adaptive_binning_wider_bins/spw_images/*.pbcor.fits` (8 images)
- **Results JSON:** `/tmp/adaptive_binning_wider_bins_results.json`
- **Log file:** `/tmp/adaptive_binning_wider_bins.log`

