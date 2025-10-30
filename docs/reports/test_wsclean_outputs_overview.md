# Overview of Output Files in `/scratch/dsa110-contimg/test_wsclean/`

## Directory Contents Summary

**Total Size:** ~507 MB  
**Total Files:** ~100+ FITS files + 1 MS directory + auxiliary files

---

## File Categories

### 1. Input Data

**`2025-10-13T13:28:03.ms/`** (Directory)
- **Type:** Measurement Set (MS)
- **Size:** ~500 MB (MS directory)
- **Description:** DSA-110 observation data for calibrator field 0702+445
- **Polarization:** 2-pol (RR, LL)
- **Contents:** Visibility data, calibration tables, metadata

**`0702_445.skymodel`** (213 bytes)
- **Type:** DP3 sky model format (text file)
- **Description:** DP3-compatible sky model for calibrator 0702+445
- **Format:** DP3 text format with calibrator point source
- **Content:** Single point source (RA=07:02:53.679, Dec=+44:31:11.940, Flux=2.4 Jy)

---

### 2. Hybrid Workflow Test Outputs (Latest)

**Base Name:** `0702_445_hybrid_test-MFS-*`

These are the **combined MFS (Multi-Frequency Synthesis) images** from the hybrid workflow test:
- **`-MFS-image-pb.fits`** - Primary beam corrected restored image ⭐ (Main science product)
- **`-MFS-image.fits`** - Restored image (without PB correction)
- **`-MFS-model.fits`** - CLEAN model (deconvolved sources)
- **`-MFS-model-pb.fits`** - CLEAN model with PB correction
- **`-MFS-residual.fits`** - Residual image (data - model)
- **`-MFS-residual-pb.fits`** - Residual with PB correction
- **`-MFS-dirty.fits`** - Dirty image (before deconvolution)
- **`-MFS-psf.fits`** - Point spread function (synthesized beam)
- **`-MFS-beam-0.fits`** - Primary beam model (term 0)
- **`-MFS-beam-9.fits`** - Primary beam model (term 9)
- **`-MFS-beam-15.fits`** - Primary beam model (term 15)

**Image Properties:**
- Size: 1024 × 1024 pixels
- Pixel scale: 2 arcsec/pixel
- Units: JY/BEAM (images), JY/PIXEL (models)
- Multi-term: 2 terms (MFS with spectral index fitting)

---

### 3. Per-Channel Outputs (Multi-Term Deconvolution)

**Base Names:** `0702_445_hybrid_test-0000-*` through `0702_445_hybrid_test-0007-*`

WSClean created **8 separate channel images** (one per spectral window) for multi-term deconvolution:

**Channels:** 0000-0007 (8 channels total)
- Each channel has the same file types as MFS outputs:
  - `-dirty.fits`
  - `-image.fits`
  - `-image-pb.fits`
  - `-model.fits`
  - `-model-pb.fits`
  - `-residual.fits`
  - `-residual-pb.fits`
  - `-psf.fits`
  - `-beam-0.fits`, `-beam-9.fits`, `-beam-15.fits`

**Purpose:** Multi-term deconvolution (`-fit-spectral-pol 2`) creates separate images per channel, then combines them into the MFS image.

**Frequency Coverage:**
- Channel 0000: ~1311-1335 MHz
- Channel 0001: ~1335-1358 MHz
- Channel 0002: ~1358-1382 MHz
- Channel 0003: ~1382-1405 MHz
- Channel 0004: ~1405-1428 MHz
- Channel 0005: ~1428-1452 MHz
- Channel 0006: ~1452-1475 MHz
- Channel 0007: ~1475-1499 MHz

---

### 4. Earlier Test Runs

**`0702_445_wsclean_hybrid-*`**
- Earlier hybrid workflow test (before latest run)
- Same file types as `0702_445_hybrid_test-MFS-*`
- May have different parameters

**`test_image-*`** and **`test_image_pb-*`**
- Initial WSClean test runs
- Without primary beam correction (`test_image-*`)
- With primary beam correction (`test_image_pb-*`)
- Includes PNG visualization: `test_image_pb-image-pb.png` (1.39 MB)

---

## File Type Descriptions

### Image Files

| File Type | Description | Units | Use Case |
|-----------|-------------|-------|----------|
| **`-image.fits`** | Restored CLEAN image (model convolved with PSF) | JY/BEAM | Science analysis |
| **`-image-pb.fits`** | PB-corrected restored image ⭐ | JY/BEAM | **Primary science product** |
| **`-dirty.fits`** | Dirty image (before deconvolution) | JY/BEAM | Quality assessment |
| **`-model.fits`** | CLEAN model (deconvolved sources) | JY/PIXEL | Source extraction |
| **`-model-pb.fits`** | PB-corrected CLEAN model | JY/BEAM | Flux measurements |
| **`-residual.fits`** | Residual (data - model) | JY/BEAM | Quality check |
| **`-residual-pb.fits`** | PB-corrected residual | JY/BEAM | Convergence check |
| **`-psf.fits`** | Point spread function | JY/BEAM | Beam characterization |

### Primary Beam Files

| File Type | Description | Units | Use Case |
|-----------|-------------|-------|----------|
| **`-beam-0.fits`** | Primary beam (term 0) | JY/BEAM | PB correction |
| **`-beam-9.fits`** | Primary beam (term 9) | JY/BEAM | Multi-term PB correction |
| **`-beam-15.fits`** | Primary beam (term 15) | JY/BEAM | Multi-term PB correction |

**Note:** Multi-term deconvolution (`-fit-spectral-pol 2`) creates separate beam terms for each spectral term.

---

## File Naming Convention

**Pattern:** `{base_name}-{channel}-{type}.fits`

**Examples:**
- `0702_445_hybrid_test-MFS-image-pb.fits` - MFS combined image, PB-corrected
- `0702_445_hybrid_test-0000-image.fits` - Channel 0 image
- `0702_445_hybrid_test-0000-beam-0.fits` - Channel 0 primary beam (term 0)

**Suffixes:**
- `-MFS-` = Multi-Frequency Synthesis (combined across channels)
- `-0000` through `-0007` = Individual channel outputs
- `-pb` = Primary beam corrected
- No suffix = Not PB-corrected

---

## Key Output Files for Science Use

### Primary Science Products

1. **`0702_445_hybrid_test-MFS-image-pb.fits`** ⭐
   - **Use:** Main science image
   - **Description:** CLEAN restored image with primary beam correction
   - **Units:** JY/BEAM
   - **Use for:** Source detection, flux measurements, visualization

2. **`0702_445_hybrid_test-MFS-model-pb.fits`**
   - **Use:** Source catalog extraction
   - **Description:** CLEAN model with PB correction
   - **Units:** JY/BEAM
   - **Use for:** Source finding, flux measurements

3. **`0702_445_hybrid_test-MFS-residual-pb.fits`**
   - **Use:** Quality assessment
   - **Description:** Residual image (should be noise-like)
   - **Units:** JY/BEAM
   - **Use for:** Checking CLEAN convergence, identifying artifacts

### Supporting Products

4. **`0702_445_hybrid_test-MFS-psf.fits`**
   - **Use:** Beam characterization
   - **Description:** Synthesized beam
   - **Units:** JY/BEAM
   - **Use for:** Reporting resolution, source size measurements

5. **`0702_445_hybrid_test-MFS-dirty.fits`**
   - **Use:** Quality assessment
   - **Description:** Dirty image (before CLEAN)
   - **Units:** JY/BEAM
   - **Use for:** Comparing with CLEAN image, checking for sidelobes

---

## Storage Analysis

**Total Files:** ~100+ FITS files  
**Total Size:** ~507 MB  
**Average File Size:** ~4.01 MB per FITS file (1024×1024×float32)

**Breakdown:**
- **Per-channel outputs:** 8 channels × 12 files/channel = 96 files (~384 MB)
- **MFS combined outputs:** 12 files (~48 MB)
- **Earlier test runs:** ~24 files (~96 MB)
- **Input data:** 1 MS directory (~500 MB)
- **Auxiliary files:** <2 MB

---

## Recommendations

### For Production Use

1. **Keep:** MFS combined outputs (`-MFS-*`)
2. **Optional:** Keep per-channel outputs if spectral analysis needed
3. **Delete:** Per-channel outputs if only using MFS combined image
4. **Keep:** `-psf.fits` for beam characterization
5. **Keep:** `-residual-pb.fits` for quality assessment

### Cleanup Script

To remove per-channel outputs while keeping MFS files:
```bash
cd /scratch/dsa110-contimg/test_wsclean
rm -f 0702_445_hybrid_test-0000-* \
      0702_445_hybrid_test-0001-* \
      0702_445_hybrid_test-0002-* \
      0702_445_hybrid_test-0003-* \
      0702_445_hybrid_test-0004-* \
      0702_445_hybrid_test-0005-* \
      0702_445_hybrid_test-0006-* \
      0702_445_hybrid_test-0007-*
```

This would reduce storage from ~507 MB to ~123 MB (keeping only MFS outputs + input MS).

---

## Summary

The `test_wsclean/` directory contains:
- ✅ **1 input MS** (`2025-10-13T13:28:03.ms`)
- ✅ **1 sky model** (`0702_445.skymodel`) for DP3 compatibility testing
- ✅ **Latest hybrid workflow outputs** (`0702_445_hybrid_test-MFS-*`) - **Primary science products**
- ✅ **Per-channel outputs** (`0702_445_hybrid_test-0000-*` through `-0007-*`) - For multi-term analysis
- ✅ **Earlier test runs** (`test_image-*`, `0702_445_wsclean_hybrid-*`)
- ✅ **Visualization** (`test_image_pb-image-pb.png`)

**Main Science Product:** `0702_445_hybrid_test-MFS-image-pb.fits` (4.01 MB, 1024×1024, PB-corrected restored image)

