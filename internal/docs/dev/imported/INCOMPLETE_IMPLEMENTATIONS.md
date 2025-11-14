# Incomplete Implementations Status

## Summary

This document tracks partially complete or incomplete implementations in the DSA-110 continuum imaging pipeline.

## ✅ Completed (But Marked Incomplete in TODO.md)

### Enhanced Variability Metrics

**Status**: ✅ **COMPLETE** (incorrectly marked as incomplete in TODO.md)

**Implementation**:
- ✅ `calculate_vs_metric()` implemented in `src/dsa110_contimg/photometry/variability.py`
- ✅ `calculate_m_metric()` implemented in `src/dsa110_contimg/photometry/variability.py`
- ✅ Two-epoch metrics added to `Source.calc_variability_metrics()` in `src/dsa110_contimg/photometry/source.py`
- ✅ Returns `vs_mean` and `m_mean` in metrics dictionary
- ✅ Unit tests exist in `tests/unit/test_source_class.py`

**Action Required**: Update TODO.md to mark as complete.

### API Integration (Partial)

**Status**: ✅ **MOSTLY COMPLETE** (3 of 4 endpoints implemented)

**Implemented Endpoints**:
- ✅ `GET /api/sources/{source_id}/variability` - Returns variability metrics
- ✅ `GET /api/sources/{source_id}/lightcurve` - Returns light curve data
- ✅ `GET /api/sources/{source_id}/postage_stamps` - Returns postage stamp cutouts

**Missing Endpoint**:
- ❌ `GET /api/sources/{source_id}/external_catalogs` - Not implemented (depends on External Catalog Module)

**Location**: `src/dsa110_contimg/api/routes.py`

## ❌ Incomplete Implementations

### 1. External Catalog Module

**Status**: ❌ **NOT IMPLEMENTED**

**Required**:
- Create `src/dsa110_contimg/catalog/external.py`
- Implement `simbad_search()` for object identification
- Implement `ned_search()` for extragalactic database queries
- Implement `gaia_search()` for astrometry
- Add `Source.crossmatch_external()` method
- Integration tests

**Dependencies**: 
- `astroquery` package (not in requirements yet)
- External API access (SIMBAD, NED, Gaia)

**Priority**: Medium (useful for source identification, not critical for core pipeline)

**Location**: Should be `src/dsa110_contimg/catalog/external.py`

### 2. API Endpoint: External Catalogs

**Status**: ❌ **NOT IMPLEMENTED** (depends on External Catalog Module)

**Required**:
- `GET /api/sources/{source_id}/external_catalogs` endpoint
- Returns SIMBAD, NED, and Gaia matches for a source

**Location**: `src/dsa110_contimg/api/routes.py`

**Priority**: Medium (depends on External Catalog Module)

### 3. ESE Detection Workflow Integration

**Status**: ⚠️ **PARTIALLY COMPLETE**

**Completed**:
- ✅ Source class with variability metrics
- ✅ Light curve plotting functionality
- ✅ Postage stamp visualization

**Missing**:
- ❌ Integration of light curve plotting into ESE candidate analysis workflow
- ❌ Integration of postage stamps into ESE candidate review workflow
- ❌ Documentation updates for ESE workflow

**Location**: ESE detection workflow (needs to be identified)

**Priority**: Medium (enhances existing ESE detection, doesn't add new detection capability)

### 4. API TODOs

**Status**: ⚠️ **MINOR TODOs**

**Location**: `src/dsa110_contimg/api/routes.py`

**TODOs**:
1. Line 2570: `new_source = False  # TODO: Implement new source detection`
   - Context: Source detail endpoint
   - Priority: Low (nice-to-have feature)

2. Line 2573: `ese_probability = None  # TODO: Implement ESE probability calculation`
   - Context: Source detail endpoint
   - Priority: Medium (useful for ESE analysis)

3. Line 4475: `# TODO: Store results in database for future retrieval`
   - Context: Validation report endpoint
   - Priority: Low (caching optimization)

**Priority**: Low to Medium

### 5. Documentation

**Status**: ⚠️ **PARTIALLY COMPLETE**

**Missing**:
- ❌ Documentation and examples for postage stamps API endpoint
- ❌ Documentation updates for ESE workflow integration

**Location**: `docs/how-to/` or `docs/examples/`

**Priority**: Low (functionality works, just needs docs)

## 🔧 Abstract Base Classes (Expected)

These are **intentionally incomplete** - they are abstract base classes:

### 1. `ConversionStrategy` Base Class

**Status**: ✅ **INTENTIONAL** (abstract base class)

**Location**: `src/dsa110_contimg/conversion/strategies/base.py`

**Note**: `raise NotImplementedError` is expected - subclasses must implement.

### 2. `VisualizationFile` Base Class

**Status**: ✅ **INTENTIONAL** (abstract base class)

**Location**: `src/dsa110_contimg/qa/visualization/file.py`

**Note**: `raise NotImplementedError("Subclasses must implement show()")` is expected.

### 3. `AlertChannel` Base Class

**Status**: ✅ **INTENTIONAL** (abstract base class)

**Location**: `src/dsa110_contimg/utils/alerting.py`

**Note**: `raise NotImplementedError` is expected - subclasses must implement.

## 📋 Summary Table

| Feature | Status | Priority | Dependencies |
|---------|--------|----------|--------------|
| Enhanced Variability Metrics | ✅ Complete | N/A | None (update TODO.md) |
| API: Variability/Lightcurve/Postage Stamps | ✅ Complete | N/A | None |
| External Catalog Module | ❌ Not Started | Medium | astroquery |
| API: External Catalogs | ❌ Not Started | Medium | External Catalog Module |
| ESE Workflow Integration | ⚠️ Partial | Medium | None |
| API TODOs | ⚠️ Minor | Low-Medium | None |
| Documentation | ⚠️ Partial | Low | None |

## Recommended Actions

### Immediate (Update Documentation)
1. ✅ Mark "Enhanced Variability Metrics" as complete in TODO.md
2. ✅ Mark API endpoints (variability, lightcurve, postage_stamps) as complete in TODO.md

### Short Term (Medium Priority)
1. Implement External Catalog Module (`src/dsa110_contimg/catalog/external.py`)
   - Add `astroquery` to requirements
   - Implement SIMBAD, NED, Gaia search functions
   - Add `Source.crossmatch_external()` method
   - Add API endpoint for external catalogs

2. Complete ESE Detection Workflow Integration
   - Integrate light curve plotting into ESE candidate analysis
   - Integrate postage stamps into ESE review workflow
   - Update documentation

### Long Term (Low Priority)
1. Implement API TODOs
   - New source detection flag
   - ESE probability calculation
   - Database caching for validation reports

2. Complete Documentation
   - Postage stamps API examples
   - ESE workflow integration guide

## Notes

- Abstract base classes with `NotImplementedError` are **intentional** and should not be "completed"
- Most incomplete items are enhancements, not critical functionality
- Core pipeline functionality (cross-matching, variability metrics, postage stamps) is complete
- External catalog integration is the main missing feature for full VAST Tools parity

