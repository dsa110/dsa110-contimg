# Reference: CLI

- Streaming worker
```
python -m dsa110_contimg.conversion.streaming.streaming_converter --help
```
- Imaging worker
```
python -m dsa110_contimg.imaging.worker --help
```
- Converter orchestrator
```
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator --help
```
- Standalone converter (single UVH5 → MS)
```
python -m dsa110_contimg.conversion.uvh5_to_ms --help
```
- Downsample UVH5 (unified CLI)
```
python -m dsa110_contimg.conversion.downsample_uvh5.cli --help
python -m dsa110_contimg.conversion.downsample_uvh5.cli single --help
python -m dsa110_contimg.conversion.downsample_uvh5.cli fast --help
python -m dsa110_contimg.conversion.downsample_uvh5.cli batch --help
```
- Legacy entrypoints (still available)
```
python -m dsa110_contimg.conversion.downsample_uvh5.downsample_hdf5 --help
python -m dsa110_contimg.conversion.downsample_uvh5.downsample_hdf5_batch --help
python -m dsa110_contimg.conversion.downsample_uvh5.downsample_hdf5_fast --help
```
- Registry CLI
```
python -m dsa110_contimg.database.registry_cli --help
```
- Mosaic CLI
```
python -m dsa110_contimg.mosaic.cli --help
```
- Calibration CLI
```
python -m dsa110_contimg.calibration.cli --help
```
- Calibration catalog CLI
```
python -m dsa110_contimg.calibration.catalog_cli --help
```
- Photometry (forced peak and adaptive binning)
```
python -m dsa110_contimg.photometry.cli --help
python -m dsa110_contimg.photometry.cli peak --help
python -m dsa110_contimg.photometry.cli adaptive --help
```
- Imaging CLI
```
python -m dsa110_contimg.imaging.cli --help
python -m dsa110_contimg.imaging.cli image --help
```

**Imaging CLI Masking Parameters:**
- `--no-nvss-mask`: Disable NVSS-based masking (masking enabled by default for 2-4x faster imaging)
- `--mask-radius-arcsec`: Mask radius around NVSS sources in arcseconds (default: 60.0, range: 10-300)

**Example:**
```bash
# Image with masking enabled (default)
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/data.ms \
    --imagename /path/to/output.img

# Image with custom mask radius
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/data.ms \
    --imagename /path/to/output.img \
    --mask-radius-arcsec 120.0

# Disable masking (not recommended - slower)
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/data.ms \
    --imagename /path/to/output.img \
    --no-nvss-mask
```

**See Also:** [Masking Guide](../how-to/masking-guide.md) for detailed usage instructions.

---

**Photometry CLI Adaptive Binning Parameters:**
- `--serialize-ms-access`: Serialize MS access using file locking to prevent CASA table lock conflicts when multiple processes access the same MS. **Recommended when processing multiple sources in parallel.**

**Example:**
```bash
# Single source (no locking needed)
python -m dsa110_contimg.photometry.cli adaptive \
    --ms /path/to/data.ms \
    --ra 124.526792 --dec 54.620694 \
    --output-dir /tmp/results \
    --target-snr 5.0

# Multiple sources in parallel (with locking)
python -m dsa110_contimg.photometry.cli adaptive \
    --ms /path/to/data.ms \
    --ra 124.526792 --dec 54.620694 \
    --output-dir /tmp/results1 \
    --target-snr 5.0 \
    --serialize-ms-access &
PID1=$!

python -m dsa110_contimg.photometry.cli adaptive \
    --ms /path/to/data.ms \
    --ra 124.530000 --dec 54.625000 \
    --output-dir /tmp/results2 \
    --target-snr 5.0 \
    --serialize-ms-access &
PID2=$!

wait $PID1 $PID2
```

**See Also:** 
- [MS Access Serialization](../testing/MS_LOCKING_IMPLEMENTATION.md) for detailed documentation
- [Phase 1 Multiple Sources Test Results](../testing/PHASE1_MULTIPLE_SOURCES_TEST_RESULTS.md) for background on why serialization is needed
