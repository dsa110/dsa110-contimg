# Testing Strategy: Successful Mosaic for 0834 Transit

**Date:** 2025-11-02  
**Goal:** Create a successful mosaic around calibrator 0834+555 (0834)  
**Timeline:** Progressive testing approach to reach production-ready mosaic

---

## Overview

This document outlines a systematic testing strategy to successfully create a mosaic from tiles around the 0834+555 calibrator transit. The strategy follows a progressive approach: validate individual components, test with small datasets, then scale to full mosaic.

---

## Phase 1: Pre-Flight Checks & Data Discovery

### 1.1 Verify Tile Availability

**Objective:** Ensure we have PB-corrected tiles available for 0834 transit

**Commands:**
```bash
# Check database for available tiles
sqlite3 state/products.sqlite3 "
SELECT 
    COUNT(*) as total_tiles,
    COUNT(CASE WHEN pbcor=1 THEN 1 END) as pbcor_tiles,
    MIN(created_at) as earliest,
    MAX(created_at) as latest
FROM images;
"

# Find tiles around 0834 transit time (if known)
# Example: If transit was around 2025-10-03 15:15 UTC
sqlite3 state/products.sqlite3 "
SELECT path, created_at, pbcor 
FROM images 
WHERE pbcor=1 
  AND created_at >= $(date -d '2025-10-03 15:00' +%s) 
  AND created_at <= $(date -d '2025-10-03 16:00' +%s)
ORDER BY created_at;
"
```

**Success Criteria:**
- At least 6-12 PB-corrected tiles found (for ~1 hour mosaic)
- Tiles span reasonable time window (≤2 hours)
- All tile paths are accessible

**If tiles missing:**
- Run imaging pipeline to generate tiles from MS files
- Verify imaging completed with PB correction
- Check `images` table has `pbcor=1` entries

---

### 1.2 Verify Primary Beam Images

**Objective:** Ensure PB images exist for all tiles (required for weighted combination)

**Commands:**
```bash
# Quick check: verify PB images exist
python3 << 'EOF'
import sqlite3
from pathlib import Path

conn = sqlite3.connect('state/products.sqlite3')
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT path, ms_path FROM images 
    WHERE pbcor=1 
    ORDER BY created_at DESC LIMIT 20
""").fetchall()

missing_pb = []
for row in rows:
    tile_path = Path(row['path'])
    # PB image should be tile_path.parent / (tile_path.stem + '.pb')
    pb_path = tile_path.parent / (tile_path.stem.replace('.pbcor', '.pb'))
    if not pb_path.exists():
        missing_pb.append(str(tile_path))

if missing_pb:
    print(f"Missing PB images for {len(missing_pb)} tiles:")
    for p in missing_pb[:5]:
        print(f"  - {p}")
else:
    print(f"✓ All {len(rows)} tiles have PB images")
EOF
```

**Success Criteria:**
- All tiles have corresponding `.pb` images
- PB images are readable CASA images

**If PB images missing:**
- Re-run imaging with PB correction enabled
- Check imaging logs for PB generation errors

---

### 1.3 Verify Disk Space & Permissions

**Objective:** Ensure sufficient space and write permissions for mosaic build

**Commands:**
```bash
# Check available disk space (need ~3x largest tile size)
df -h /scratch/dsa110-contimg

# Check write permissions
mkdir -p /scratch/dsa110-contimg/mosaics/0834_test
touch /scratch/dsa110-contimg/mosaics/0834_test/.test_write
rm /scratch/dsa110-contimg/mosaics/0834_test/.test_write
echo "✓ Write permissions OK"
```

**Success Criteria:**
- At least 50 GB free space available
- Write permissions verified

---

## Phase 2: Dry-Run Validation

### 2.1 Plan Mosaic from Available Tiles

**Objective:** Create mosaic plan and validate without building

**Commands:**
```bash
# Determine time window for 0834 transit
# Option 1: Use recent tiles (last hour)
SINCE=$(date -d '1 hour ago' +%s)
UNTIL=$(date +%s)

# Option 2: Use specific transit time window
# SINCE=$(date -d '2025-10-03 15:00 UTC' +%s)
# UNTIL=$(date -d '2025-10-03 16:00 UTC' +%s)

# Plan mosaic
python3 -m dsa110_contimg.mosaic.cli plan \
    --products-db state/products.sqlite3 \
    --name 0834_test_plan \
    --since $SINCE \
    --until $UNTIL \
    --method pbweighted
```

**Success Criteria:**
- Plan created successfully
- Plan contains 6-12 tiles
- No errors during planning

**If planning fails:**
- Check tile count: may need to adjust time window
- Verify database connectivity
- Check tile paths are accessible

---

### 2.2 Dry-Run Validation

**Objective:** Validate all tiles without building (measure twice, cut once)

**Commands:**
```bash
# Dry-run: validate without building
python3 -m dsa110_contimg.mosaic.cli build \
    --products-db state/products.sqlite3 \
    --name 0834_test_plan \
    --output /scratch/dsa110-contimg/mosaics/0834_test/mosaic_0834 \
    --dry-run
```

**Expected Output:**
- Pre-flight validation checks
- Tile consistency validation
- Resource estimates
- "DRY-RUN MODE: Validation complete, not building mosaic"

**Success Criteria:**
- All pre-flight checks pass
- Tile consistency validation passes
- No validation errors reported
- Resource estimates reasonable (< 100 GB, < 60 minutes)

**If validation fails:**
- Review validation issues
- Fix missing PB images
- Fix grid mismatches
- Fix calibration inconsistencies

---

## Phase 3: Small-Scale Test Build

### 3.1 Build Mosaic with 2-3 Tiles

**Objective:** Test mosaic building with minimal tiles to catch issues early

**Commands:**
```bash
# Manually select 2-3 tiles for testing
python3 << 'EOF'
import sqlite3
from pathlib import Path

conn = sqlite3.connect('state/products.sqlite3')
conn.row_factory = sqlite3.Row

# Get 3 most recent tiles
tiles = conn.execute("""
    SELECT path FROM images 
    WHERE pbcor=1 
    ORDER BY created_at DESC 
    LIMIT 3
""").fetchall()

tile_paths = [row['path'] for row in tiles]
print("\n".join(tile_paths))
EOF

# Create manual plan with selected tiles
python3 << 'EOF'
import sqlite3
from pathlib import Path
import time

conn = sqlite3.connect('state/products.sqlite3')
conn.execute("""
    INSERT OR REPLACE INTO mosaics (name, created_at, status, method, tiles)
    VALUES (?, ?, ?, ?, ?)
""", (
    '0834_test_mini',
    time.time(),
    'planned',
    'pbweighted',
    '\n'.join(['/path/to/tile1', '/path/to/tile2', '/path/to/tile3'])  # Replace with actual paths
))
conn.commit()
print("✓ Mini mosaic plan created")
EOF

# Build mini mosaic
python3 -m dsa110_contimg.mosaic.cli build \
    --products-db state/products.sqlite3 \
    --name 0834_test_mini \
    --output /scratch/dsa110-contimg/mosaics/0834_test/mosaic_mini
```

**Success Criteria:**
- Mosaic builds successfully
- Output image exists and is readable
- No crashes or errors
- Mosaic has reasonable size/shape

**If build fails:**
- Check error messages
- Verify PB images exist
- Check grid compatibility
- Review validation output

---

### 3.2 Validate Mini Mosaic Quality

**Objective:** Verify mini mosaic meets quality standards

**Commands:**
```bash
# Check mosaic exists and is readable
python3 << 'EOF'
from casacore.images import image as casaimage
from pathlib import Path

mosaic_path = Path('/scratch/dsa110-contimg/mosaics/0834_test/mosaic_mini.image')
if mosaic_path.exists():
    img = casaimage(str(mosaic_path))
    data = img.getdata()
    print(f"✓ Mosaic shape: {data.shape}")
    print(f"✓ Data range: {data.min():.3e} to {data.max():.3e}")
    print(f"✓ Non-NaN pixels: {(~np.isnan(data)).sum() / data.size * 100:.1f}%")
else:
    print(f"✗ Mosaic not found: {mosaic_path}")
EOF
```

**Success Criteria:**
- Mosaic image readable
- Reasonable data range
- Good coverage (non-NaN pixels > 50%)

---

## Phase 4: Full Mosaic Build

### 4.1 Build Full Mosaic

**Objective:** Build complete mosaic with all available tiles

**Commands:**
```bash
# Build full mosaic
python3 -m dsa110_contimg.mosaic.cli build \
    --products-db state/products.sqlite3 \
    --name 0834_test_plan \
    --output /scratch/dsa110-contimg/mosaics/0834/mosaic_0834_full
```

**Monitor Progress:**
- Watch for validation messages
- Monitor disk space usage
- Check for errors/warnings

**Success Criteria:**
- Mosaic builds without errors
- All tiles processed successfully
- Mosaic metrics generated
- Post-mosaic validation passes

---

### 4.2 Post-Mosaic Validation

**Objective:** Verify final mosaic quality

**Commands:**
```bash
# Check mosaic quality metrics
python3 << 'EOF'
from casacore.images import image as casaimage
import numpy as np

mosaic_path = '/scratch/dsa110-contimg/mosaics/0834/mosaic_0834_full.image'
img = casaimage(mosaic_path)
data = img.getdata()

# Extract first plane if multi-dimensional
if len(data.shape) > 2:
    data = data[0, 0, :, :]

# Quality metrics
valid_mask = ~np.isnan(data) & np.isfinite(data)
coverage = valid_mask.sum() / data.size

# RMS noise (use robust statistics)
valid_data = data[valid_mask]
rms = np.percentile(np.abs(valid_data), 50) * 1.4826  # MAD estimate

# Dynamic range
max_val = np.abs(valid_data).max()
dynamic_range = max_val / rms if rms > 0 else 0

print(f"Mosaic Quality Metrics:")
print(f"  Coverage: {coverage:.1%}")
print(f"  RMS noise: {rms:.3e} Jy/beam")
print(f"  Dynamic range: {dynamic_range:.1f}")
print(f"  Max value: {max_val:.3e} Jy/beam")
EOF
```

**Success Criteria:**
- Coverage > 80% (good tile overlap)
- RMS noise reasonable (< 0.001 Jy/beam typical)
- Dynamic range > 100
- No obvious artifacts

---

### 4.3 Visual Inspection

**Objective:** Visually verify mosaic quality

**Commands:**
```bash
# Export to FITS for visualization
python3 << 'EOF'
from casatasks import exportfits

mosaic_path = '/scratch/dsa110-contimg/mosaics/0834/mosaic_0834_full.image'
fits_path = mosaic_path.replace('.image', '.fits')

exportfits(
    imagename=mosaic_path,
    fitsimage=fits_path,
    overwrite=True
)
print(f"✓ Exported to {fits_path}")
EOF

# View with ds9 or similar
# ds9 /scratch/dsa110-contimg/mosaics/0834/mosaic_0834_full.fits
```

**Visual Checks:**
- Smooth transitions between tiles
- No obvious discontinuities
- Reasonable noise level
- Sources visible if expected

---

## Phase 5: Troubleshooting Common Issues

### Issue: Missing PB Images

**Symptoms:**
- Validation fails with "Missing primary beam image"
- Build falls back to noise-weighted

**Solution:**
```bash
# Check if PB images exist
find /scratch/dsa110-contimg/images -name "*.pb" | head -5

# If missing, re-run imaging with PB correction
# Or check imaging logs for PB generation errors
```

---

### Issue: Grid Mismatch

**Symptoms:**
- Validation fails with "Grid mismatch"
- Tiles have different pixel scales or sizes

**Solution:**
- Ensure all tiles imaged with same `imsize` and `cell`
- Check imaging parameters consistency
- Regridding should handle this automatically, but verify

---

### Issue: Calibration Inconsistency

**Symptoms:**
- Validation warnings about calibration tables
- Different calibration applied to different tiles

**Solution:**
```bash
# Check calibration status
sqlite3 state/products.sqlite3 "
SELECT DISTINCT ms_path, cal_applied 
FROM images 
JOIN ms_index ON images.ms_path = ms_index.path 
WHERE images.pbcor=1 
LIMIT 10;
"

# Verify all tiles use same calibration set
```

---

### Issue: Disk Space

**Symptoms:**
- Pre-flight check fails
- Build fails during regridding

**Solution:**
```bash
# Check disk space
df -h /scratch/dsa110-contimg

# Clean up temporary files
find /scratch/dsa110-contimg -name "*.tmp" -delete
find /scratch/dsa110-contimg -name "*regrid*" -type d -exec rm -rf {} +

# Use scratch directory if available
```

---

## Phase 6: Production-Ready Mosaic

### 6.1 Optimize Mosaic Parameters

**Objective:** Fine-tune mosaic for best quality

**Considerations:**
- Tile selection: Include only high-quality tiles
- Time window: Optimize for best coverage
- Weighting method: Use `pbweighted` for best flux accuracy

**Commands:**
```bash
# Re-plan with optimized parameters
python3 -m dsa110_contimg.mosaic.cli plan \
    --products-db state/products.sqlite3 \
    --name 0834_production \
    --since $OPTIMIZED_SINCE \
    --until $OPTIMIZED_UNTIL \
    --method pbweighted
```

---

### 6.2 Final Build & Documentation

**Objective:** Create production mosaic with full documentation

**Commands:**
```bash
# Build final mosaic
python3 -m dsa110_contimg.mosaic.cli build \
    --products-db state/products.sqlite3 \
    --name 0834_production \
    --output /scratch/dsa110-contimg/mosaics/0834/mosaic_0834_final

# Verify mosaic in database
sqlite3 state/products.sqlite3 "
SELECT name, status, output_path, validation_issues 
FROM mosaics 
WHERE name='0834_production';
"
```

---

## Success Criteria Summary

### Minimum Viable Mosaic:
- ✓ At least 6 tiles combined
- ✓ PB-weighted combination successful
- ✓ Mosaic image readable and valid
- ✓ Coverage > 50%
- ✓ No validation errors

### Production-Ready Mosaic:
- ✓ 12+ tiles covering full transit
- ✓ PB-weighted combination
- ✓ Coverage > 80%
- ✓ RMS noise < 0.001 Jy/beam
- ✓ Dynamic range > 100
- ✓ Post-mosaic validation passes
- ✓ Metrics generated successfully
- ✓ No visual artifacts

---

## Testing Checklist

- [ ] Phase 1: Pre-flight checks complete
- [ ] Phase 2: Dry-run validation passes
- [ ] Phase 3: Mini mosaic builds successfully
- [ ] Phase 4: Full mosaic builds successfully
- [ ] Phase 5: All issues resolved
- [ ] Phase 6: Production mosaic created

---

## Timeline Estimate

- **Phase 1:** 15 minutes (data discovery)
- **Phase 2:** 10 minutes (dry-run validation)
- **Phase 3:** 30 minutes (mini mosaic test)
- **Phase 4:** 60 minutes (full mosaic build)
- **Phase 5:** Variable (troubleshooting)
- **Phase 6:** 30 minutes (final build)

**Total:** ~2-3 hours (excluding troubleshooting)

---

## Next Steps

1. Start with Phase 1.1: Verify tile availability
2. Proceed sequentially through phases
3. Document any issues encountered
4. Adjust strategy based on findings
5. Iterate until production-ready mosaic achieved

---

## Notes

- Use `--dry-run` flag liberally to validate without building
- Check logs at each phase for warnings/errors
- Keep intermediate mosaics for comparison
- Document any deviations from expected behavior

