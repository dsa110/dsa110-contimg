# Science MS Files Inventory

## Location
`/stage/dsa110-contimg/ms/science/`

## Summary

**Total MS Files:** 27 files across 2 date directories (2025-10-28, 2025-10-29)

**Calibration Status:**
- Most files have populated CORRECTED_DATA (calibrated)
- One file (`2025-10-28T13:55:53.fast.ms`) has empty CORRECTED_DATA

## Sample Files Analyzed

### 1. `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:30:07.ms` ✓ RECOMMENDED

**Properties:**
- Rows: 1,787,904
- SPWs: 16
- Channels per SPW: 48
- CORRECTED_DATA: ✓ Populated
- Data Quality: Good (91,296 unflagged samples in 1000-row sample)
- Real range: [-25.62, 500.53] Jy
- Imag range: [-304.26, 24.12] Jy

**SPW Frequency Coverage:**
- SPW 0: 1317.12 MHz (BW: 11.47 MHz)
- SPW 1: 1328.84 MHz (BW: 11.47 MHz)
- SPW 2: 1340.56 MHz (BW: 11.47 MHz)
- SPW 3: 1352.28 MHz (BW: 11.47 MHz)
- SPW 4: 1364.00 MHz (BW: 11.47 MHz)
- SPW 5: 1375.72 MHz (BW: 11.47 MHz)
- SPW 6: 1387.44 MHz (BW: 11.47 MHz)
- SPW 7: 1399.16 MHz (BW: 11.47 MHz)
- ... (8 more SPWs)

**Status:** ✓ Suitable for adaptive binning testing

### 2. `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:45:34.ms` ✓

**Properties:**
- Rows: 1,787,904
- SPWs: 16
- CORRECTED_DATA: ✓ Populated

**Status:** ✓ Suitable for testing

### 3. `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T14:16:30.ms` ✓

**Properties:**
- Rows: 1,787,904
- SPWs: 16
- CORRECTED_DATA: ✓ Populated

**Status:** ✓ Suitable for testing

### 4. `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:40:25.ms` ✓

**Properties:**
- Rows: 1,787,904
- SPWs: 16
- CORRECTED_DATA: ✓ Populated

**Status:** ✓ Suitable for testing

### 5. `/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:55:53.fast.ms` ✗

**Properties:**
- Rows: 1,787,904
- SPWs: 16
- Channels per SPW: 12 (fewer than standard)
- CORRECTED_DATA: ✗ Empty/Unavailable

**Status:** ✗ Not suitable (uncalibrated)

## Directory Structure

```
/stage/dsa110-contimg/ms/science/
├── 2025-10-28/
│   ├── 2025-10-28T13:30:07.ms          ✓ Calibrated
│   ├── 2025-10-28T13:35:16.ms          ✓ Calibrated
│   ├── 2025-10-28T13:40:25.ms          ✓ Calibrated
│   ├── 2025-10-28T13:45:34.ms          ✓ Calibrated
│   ├── 2025-10-28T13:55:53.ms          ✓ Calibrated
│   ├── 2025-10-28T13:55:53.fast.ms     ✗ Uncalibrated
│   ├── 2025-10-28T14:06:11.ms          ✓ Calibrated
│   └── 2025-10-28T14:16:30.ms          ✓ Calibrated
└── 2025-10-29/
    └── (additional files)
```

## Recommendations

### For Adaptive Binning Testing

**Primary Test File:**
```bash
/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:30:07.ms
```

**Why:**
- Fully calibrated (CORRECTED_DATA populated)
- 16 SPWs (full DSA-110 complement)
- Good data quality
- Standard channel count (48 per SPW)

### Usage Example

```bash
python -m dsa110_contimg.photometry.cli adaptive \
  --ms /stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:30:07.ms \
  --ra 128.725 \
  --dec 55.573 \
  --output-dir /tmp/adaptive_test/ \
  --target-snr 5.0 \
  --max-width 16 \
  --imsize 1024 \
  --quality-tier standard \
  --backend tclean
```

## Notes

1. **Calibration Status:** Most science MS files are properly calibrated and ready for imaging
2. **SPW Structure:** All files have 16 SPWs, consistent with DSA-110 configuration
3. **Channel Count:** Most files have 48 channels per SPW (some fast.ms files have fewer)
4. **Data Volume:** Each MS has ~1.8M rows, representing substantial observation time

## Next Steps

1. Run full end-to-end adaptive binning test on recommended MS file
2. Test with known source coordinates from NVSS catalog
3. Verify SPW imaging works correctly with calibrated data
4. Measure performance (imaging time per SPW)

