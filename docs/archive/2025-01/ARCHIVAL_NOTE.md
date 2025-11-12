# Dashboard Documentation Archival Note

**Date:** 2025-11-12  
**Reason:** Documentation consolidation and accuracy update

## Archived Documents

### 1. `dashboard_api.md` → `dashboard_api.md.archived`

**Original Location:** `docs/reference/dashboard_api.md`  
**Archived:** 2025-11-12  
**Reason:** Superseded by `dashboard_backend_api.md`

**Issues:**
- Base URL incorrect (`8010` vs `8000`)
- Missing 80+ implemented endpoints
- Less comprehensive than consolidated version
- Outdated endpoint documentation

**Replacement:** `docs/reference/dashboard_backend_api.md` (comprehensive, up-to-date)

---

### 2. `dashboard_tbd_status.md` → `dashboard_tbd_status.md.archived`

**Original Location:** `internal/docs/dev/status/2025-01/dashboard_tbd_status.md`  
**Archived:** 2025-11-12  
**Reason:** Significantly outdated - many "TBD" items are now complete

**Major Inaccuracies:**
- Sky View Page marked as "Partially Complete" → **Now fully implemented**
- Mosaic Gallery marked as "Uses Mock Data" → **Now uses real database**
- Source Monitoring marked as "Uses Mock Data" → **Now uses real database**
- Missing Observing Page (fully implemented)
- Missing Health Page (fully implemented)
- ESE candidates marked as mock → **Now uses real detection pipeline**

**Replacement:** 
- `docs/reference/dashboard_implementation_status.md` (current status)
- `docs/reference/dashboard_pages_and_features.md` (detailed feature documentation)

---

## Current Documentation Structure

### Primary References

1. **`docs/reference/dashboard_backend_api.md`**
   - Comprehensive API reference
   - All endpoints documented
   - Single source of truth for API documentation

2. **`docs/reference/dashboard_implementation_status.md`**
   - Current implementation status
   - Status indicators (✅ Implemented, 🔄 Partial, 📋 Planned)
   - Updated regularly

3. **`docs/reference/dashboard_pages_and_features.md`**
   - Detailed page documentation
   - Feature lists with status indicators
   - User workflows

### Supporting Documentation

- `docs/concepts/dashboard_architecture.md` - System architecture
- `docs/concepts/dashboard_frontend_architecture.md` - Frontend details
- `docs/concepts/dashboard_data_models.md` - Database schemas
- `docs/how-to/dashboard_development_workflow.md` - Development guide

---

## Migration Summary

**Before:** 3 overlapping, partially outdated API documentation files  
**After:** 1 comprehensive, up-to-date API reference + status tracking

**Benefits:**
- Single source of truth
- Reduced confusion
- Easier maintenance
- Accurate status tracking

---

## Accessing Archived Documents

Archived documents are preserved for historical reference:
- Location: `docs/archive/2025-01/`
- Format: Original filename + `.archived` extension
- Purpose: Historical reference only (do not use for current development)

