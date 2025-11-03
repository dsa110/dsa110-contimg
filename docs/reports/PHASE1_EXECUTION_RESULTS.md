# Phase 1 Execution Results: Pre-Flight Checks & Data Discovery

**Date:** 2025-11-02  
**Status:** ⚠️ **PARTIAL SUCCESS - BLOCKED BY MISSING PB-CORRECTED TILES**

---

## Executive Summary

Phase 1 pre-flight checks have been completed. Infrastructure is ready, but **no PB-corrected tiles are currently registered in the database** for mosaicking. However, **9 PB-corrected images have been found in archive directories** that could potentially be used.

---

## 1.1 Tile Availability Check

### Database Status
- **Database:** `state/products.sqlite3` ✓ Accessible
- **Total images:** 8 registered
- **PB-corrected tiles:** 0 ✗

### Image Types in Database
- All 8 images are type: `5min`
- Images are from: 2025-10-07 15:19:35 UTC
- Images registered but **files do not exist on disk**

### Archive Images Found
- **Location:** `/scratch/dsa110-contimg/archive/`
- **PB-corrected images:** 9 found
- **Dates:** October 13, 2025
- **Locations:**
  - `/scratch/dsa110-contimg/archive/central_cal_rebuild/`
  - `/scratch/dsa110-contimg/archive/single_20251013/`

---

## 1.2 Primary Beam Images Check

### Database Images
- **PB images registered:** 2 entries
- **Files exist:** ✗ No (images not on disk)

### Archive Images
- **PB images for archive PB-corrected images:** Checking...
- **Status:** PB images should exist alongside PB-corrected images

---

## 1.3 Disk Space & Permissions Check

### Disk Space
- **Filesystem:** `/dev/nvme0n1p2`
- **Available:** 261 GB ✓
- **Status:** Sufficient for mosaic building

### Permissions
- **Output directory:** `/scratch/dsa110-contimg/mosaics/0834_test`
- **Write permissions:** ✓ OK
- **Directory created:** ✓ Successfully

---

## Findings

### ✓ Passed Checks
1. Database accessible and contains image records
2. Disk space sufficient (261 GB available)
3. Write permissions verified
4. Output directory created successfully

### ⚠️ Issues Identified
1. **No PB-corrected tiles in database**
   - Database has 8 images but none marked as `pbcor=1`
   - Database images point to files that don't exist on disk
   
2. **Archive images available but not registered**
   - Found 9 PB-corrected images in archive
   - These images are not in the products database
   - Need to verify PB images exist for them

---

## Recommendations

### Option A: Register Archive Images (RECOMMENDED)
**Pros:** Fastest path forward, images already exist
**Steps:**
1. Verify PB images exist for archive PB-corrected images
2. Register archive PB-corrected images in products database
3. Set `pbcor=1` flag
4. Verify PB images are accessible
5. Proceed with Phase 2

### Option B: Create PB-Corrected Images from Database Images
**Pros:** Uses registered images
**Cons:** Requires images to exist on disk (they don't)
**Steps:**
1. Locate or restore database image files
2. Verify PB images exist
3. Run CASA `pbcor()` to create PB-corrected images
4. Update database `pbcor` flag
5. Proceed with Phase 2

### Option C: Generate New Tiles for 0834 Transit
**Pros:** Fresh, properly processed tiles
**Cons:** Requires MS files and full imaging pipeline
**Steps:**
1. Find MS files for 0834 transit
2. Run imaging pipeline with PB correction
3. Register new tiles in database
4. Proceed with Phase 2

---

## Next Steps

**Immediate Action Required:**
1. Verify PB images exist for archive PB-corrected images
2. Decide on approach (Option A recommended)
3. Register images in database if using Option A
4. Verify all requirements met
5. Proceed to Phase 2: Dry-Run Validation

---

## Phase 1 Status: ⚠️ **BLOCKED**

**Blocking Issue:** No PB-corrected tiles registered in database

**Action Required:** Choose and execute one of the three options above

**Once PB-corrected tiles are available in database, Phase 1 will be complete and Phase 2 can begin.**

---

## Phase 1 Option A Execution: Registration Complete ✓

### Registration Results

**Images Registered:** 3 PB-corrected tiles

**Details:**
1. `2025-10-13T13:28:03.wproj.image.pbcor`
   - PB image: `2025-10-13T13:28:03.wproj.pb` ✓
   - MS file: `2025-10-13T13:28:03.ms` ✓

2. `2025-10-13T13:34:44.img.image.pbcor`
   - PB image: `2025-10-13T13:34:44.img.pb` ✓
   - MS file: `2025-10-13T13:34:44.ms` ✓

3. `2025-10-13T13:34:44.wproj.image.pbcor`
   - PB image: `2025-10-13T13:34:44.wproj.pb` ✓
   - MS file: `2025-10-13T13:34:44.ms` ✓

### Verification Results

- **Images exist on disk:** 3/3 ✓
- **Images have PB images:** 3/3 ✓
- **PB images verified:** All found and accessible ✓

### Final Status

**✓✓✓ PHASE 1 COMPLETE**

- Database: 11 total images, 3 PB-corrected tiles
- All registered tiles verified and ready
- All tiles have corresponding PB images
- Ready for PB-weighted mosaicking

**Next Step:** Proceed to Phase 2: Dry-Run Validation
