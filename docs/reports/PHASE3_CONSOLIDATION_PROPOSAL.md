# Phase 3 Consolidation Proposal

**Date:** 2025-11-12  
**Status:** Proposal for review

---

## Overview

Phase 3 focuses on further topic-based grouping of How-To Guides. These consolidations are lower risk than Phase 2 since they group clearly related content.

---

## Proposed Consolidations

### 1. ✅ Group Mosaic Guides

**Current:**
- `mosaic_quickstart.md` is in Quickstarts section
- `mosaic.md` is standalone in How-To Guides

**Proposed:**
```yaml
- Mosaic:
  - Quickstart: how-to/mosaic_quickstart.md
  - Complete Guide: how-to/mosaic.md
```

**Rationale:** Both are mosaic-related, logical to group together  
**Impact:** Reduces How-To Guides by 1 entry

---

### 2. ✅ Group Testing Guides

**Current:**
```yaml
- Fast Testing: how-to/FAST_TESTING.md
- Pipeline Testing Guide: how-to/PIPELINE_TESTING_GUIDE.md
- Test Flag Subcommand: how-to/TEST_FLAG_SUBCOMMAND.md
```

**Proposed:**
```yaml
- Testing:
  - Fast Testing: how-to/FAST_TESTING.md
  - Pipeline Guide: how-to/PIPELINE_TESTING_GUIDE.md
  - Flag Subcommand: how-to/TEST_FLAG_SUBCOMMAND.md
```

**Rationale:** All testing-related, logical grouping  
**Impact:** Reduces How-To Guides by 2 entries

---

### 3. ✅ Group Calibration Guides

**Current:**
```yaml
- Calibration Detailed Procedure: how-to/CALIBRATION_DETAILED_PROCEDURE.md
- Find Calibrator Transit Data: how-to/FIND_CALIBRATOR_TRANSIT_DATA.md
```

**Proposed:**
```yaml
- Calibration:
  - Detailed Procedure: how-to/CALIBRATION_DETAILED_PROCEDURE.md
  - Find Calibrator Transit: how-to/FIND_CALIBRATOR_TRANSIT_DATA.md
```

**Rationale:** Both calibration-related, logical grouping  
**Impact:** Reduces How-To Guides by 1 entry

---

### 4. ✅ Group QA Guides

**Current:**
```yaml
- Quality Assurance Setup: how-to/QUALITY_ASSURANCE_SETUP.md
- Quick Look: how-to/quicklook.md
```

**Proposed:**
```yaml
- Quality Assurance:
  - Setup: how-to/QUALITY_ASSURANCE_SETUP.md
  - Quick Look: how-to/quicklook.md
```

**Rationale:** Both QA-related, logical grouping  
**Impact:** Reduces How-To Guides by 1 entry

---

## Expected Impact

### Navigation Reduction
- **Before Phase 3:** ~42 top-level navigation items (after Phase 2)
- **After Phase 3:** ~35 top-level navigation items
- **Phase 3 Reduction:** ~7 entries (17% reduction)

### Cumulative Impact (All Phases)
- **Original:** 59 top-level navigation items
- **After Phase 3:** ~35 top-level navigation items
- **Total Reduction:** ~24 entries (41% reduction)

### Section-Specific Impact
- **How-To Guides:** ~20 → ~13 top-level entries (-7)

---

## Risk Assessment

**Low Risk:**
- Clear topic-based groupings
- No content overlap concerns
- Logical organization improvements

**Considerations:**
- Mosaic Quickstart currently in Quickstarts - need to move it
- All groupings are clearly related topics

---

## Implementation Plan

1. Group Mosaic guides (move Quickstart out of Quickstarts)
2. Group Testing guides
3. Group Calibration guides
4. Group QA guides

**Estimated effort:** Low (similar to Phase 2)

---

## Recommendation

**Proceed with Phase 3** - These are logical, low-risk consolidations that will further improve navigation organization. The groupings are clear and don't require content review.

---

## Status

Ready for implementation upon approval.

