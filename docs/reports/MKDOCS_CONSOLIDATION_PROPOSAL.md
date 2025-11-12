# MkDocs Navigation Consolidation Proposal

**Date:** 2025-11-12  
**Status:** Proposal for review

---

## Current State Analysis

### Navigation Statistics
- **Total top-level sections:** 6 (Home, Concepts, Tutorials, How-To Guides, Reference, Operations, Contributing)
- **How-To Guides:** 27 entries (longest section)
- **Concepts:** 14 entries
- **Reference:** 12 entries
- **Operations:** 6 entries

### Issues Identified

1. **How-To Guides is too long** (27 entries) - Hard to scan, many related topics scattered
2. **Multiple "Quickstart" entries** - Confusing naming
3. **Pipeline documentation** - 4 separate entries could be grouped
4. **Dashboard entries** - Multiple related entries scattered
5. **Mosaic entries** - Duplicate/overlapping content
6. **Conversion entries** - Multiple related guides

---

## Consolidation Opportunities

### 1. ✅ Group Pipeline Documentation (High Impact, Low Risk)

**Current:**
```yaml
- Pipeline Overview: concepts/pipeline_overview.md
- Pipeline Stage Architecture: concepts/pipeline_stage_architecture.md
- Pipeline Workflow Visualization: concepts/pipeline_workflow_visualization.md
- Pipeline Production Features: concepts/pipeline_production_features.md
```

**Proposed:**
```yaml
- Pipeline:
  - Overview: concepts/pipeline_overview.md
  - Stage Architecture: concepts/pipeline_stage_architecture.md
  - Workflow Visualization: concepts/pipeline_workflow_visualization.md
  - Production Features: concepts/pipeline_production_features.md
```

**Benefit:** Reduces Concepts section from 14 to 11 top-level entries, groups related content

---

### 2. ✅ Group Dashboard Guides (Medium Impact, Low Risk)

**Current:**
```yaml
- Dashboard Development: how-to/dashboard-development.md
- Dashboard Quickstart: how-to/dashboard-quickstart.md
- Quickstart Dashboard: how-to/quickstart_dashboard.md
```

**Proposed:**
```yaml
- Dashboard:
  - Quickstart: how-to/dashboard-quickstart.md  # Keep most comprehensive one
  - Development: how-to/dashboard-development.md
  # Remove duplicate: quickstart_dashboard.md (if content overlaps)
```

**Benefit:** Reduces How-To Guides by 1-2 entries, groups related content

**Note:** Need to verify if `quickstart_dashboard.md` and `dashboard-quickstart.md` have different content.

---

### 3. ✅ Group Mosaic Guides (Low Impact, Low Risk)

**Current:**
```yaml
- Mosaic Quickstart: how-to/mosaic_quickstart.md
- Mosaic: how-to/mosaic.md
```

**Proposed:**
```yaml
- Mosaic:
  - Quickstart: how-to/mosaic_quickstart.md
  - Complete Guide: how-to/mosaic.md
```

**Benefit:** Groups related content, clearer hierarchy

---

### 4. ✅ Group Conversion Guides (Medium Impact, Medium Risk)

**Current:**
```yaml
- UVH5 to MS Conversion: how-to/uvh5_to_ms_conversion.md
- Streaming Converter Guide: how-to/streaming_converter_guide.md
```

**Proposed:**
```yaml
- Conversion:
  - UVH5 to MS: how-to/uvh5_to_ms_conversion.md
  - Streaming Converter: how-to/streaming_converter_guide.md
```

**Benefit:** Groups related conversion topics

---

### 5. ✅ Group Quickstart Entries (High Impact, Medium Risk)

**Current:**
```yaml
- Quickstart: how-to/quickstart.md
- Quickstart Dashboard: how-to/quickstart_dashboard.md
- Dashboard Quickstart: how-to/dashboard-quickstart.md
- Control Panel Quickstart: how-to/control-panel-quickstart.md
- Linear Setup Quickstart: how-to/LINEAR_SETUP_QUICKSTART.md
```

**Proposed:**
```yaml
- Quickstarts:
  - General: how-to/quickstart.md
  - Dashboard: how-to/dashboard-quickstart.md
  - Control Panel: how-to/control-panel-quickstart.md
  - Linear Setup: how-to/LINEAR_SETUP_QUICKSTART.md
```

**Benefit:** Groups all quickstart guides, reduces top-level clutter

---

### 6. ✅ Group Deployment Operations (Low Impact, Low Risk)

**Current:**
```yaml
- Deploy with Docker: operations/deploy-docker.md
- Deploy with systemd: operations/deploy-systemd.md
```

**Proposed:**
```yaml
- Deployment:
  - Docker: operations/deploy-docker.md
  - systemd: operations/deploy-systemd.md
```

**Benefit:** Groups related deployment methods

---

### 7. ✅ Group API Reference (Low Impact, Low Risk)

**Current:**
```yaml
- API Endpoints: reference/api-endpoints.md
- Dashboard API: reference/dashboard_api.md
- Backend Integration Snippets: reference/backend_integration_snippets.md
```

**Proposed:**
```yaml
- API:
  - Endpoints: reference/api-endpoints.md
  - Dashboard: reference/dashboard_api.md
  - Integration Snippets: reference/backend_integration_snippets.md
```

**Benefit:** Groups API-related documentation

---

## Proposed Consolidated Navigation Structure

### Concepts (11 entries, down from 14)
```yaml
- Concepts:
  - Overview: concepts/index.md
  - Architecture: concepts/architecture.md
  - Directory Architecture: concepts/DIRECTORY_ARCHITECTURE.md
  - Modules: concepts/modules.md
  - Control Panel: concepts/control-panel.md
  - AOFlagger: concepts/aoflagger.md
  - Frontend Design: concepts/frontend_design.md
  - Dashboard Mockups: concepts/dashboard_mockups.md
  - Glossary: concepts/GLOSSARY.md
  - Pipeline:
    - Overview: concepts/pipeline_overview.md
    - Stage Architecture: concepts/pipeline_stage_architecture.md
    - Workflow Visualization: concepts/pipeline_workflow_visualization.md
    - Production Features: concepts/pipeline_production_features.md
  - Science:
    - Photometry Normalization: concepts/science/photometry_normalization.md
```

### How-To Guides (20-22 entries, down from 27)
```yaml
- How-To Guides:
  - Quickstarts:
    - General: how-to/quickstart.md
    - Dashboard: how-to/dashboard-quickstart.md
    - Control Panel: how-to/control-panel-quickstart.md
    - Linear Setup: how-to/LINEAR_SETUP_QUICKSTART.md
  - Dashboard:
    - Development: how-to/dashboard-development.md
  - Conversion:
    - UVH5 to MS: how-to/uvh5_to_ms_conversion.md
    - Streaming Converter: how-to/streaming_converter_guide.md
  - Mosaic:
    - Quickstart: how-to/mosaic_quickstart.md
    - Complete Guide: how-to/mosaic.md
  - Calibration:
    - Detailed Procedure: how-to/CALIBRATION_DETAILED_PROCEDURE.md
    - Find Calibrator Transit: how-to/FIND_CALIBRATOR_TRANSIT_DATA.md
  - Testing:
    - Fast Testing: how-to/FAST_TESTING.md
    - Pipeline Testing: how-to/PIPELINE_TESTING_GUIDE.md
    - Test Flag Subcommand: how-to/TEST_FLAG_SUBCOMMAND.md
  - Quality Assurance:
    - Setup: how-to/QUALITY_ASSURANCE_SETUP.md
    - Quick Look: how-to/quicklook.md
  - Other:
    - Build VP from h5: how-to/build-vp-from-h5.md
    - Image 0834 Transit 5min: how-to/IMAGE_0834_TRANSIT_5MIN.md
    - Reprocess: how-to/reprocess.md
    - Using Orchestrator CLI: how-to/USING_ORCHESTRATOR_CLI.md
    - Linear Integration: how-to/LINEAR_INTEGRATION.md
    - Frontend Initial Setup: how-to/frontend-initial-setup.md
    - AOFlagger Parameter Optimization: how-to/PARAMETER_OPTIMIZATION_GUIDE.md
    - Downsampling Guide: how-to/downsampling_guide.md
    - Troubleshooting: how-to/troubleshooting.md
```

### Reference (9 entries, down from 12)
```yaml
- Reference:
  - API:
    - Endpoints: reference/api-endpoints.md
    - Dashboard: reference/dashboard_api.md
    - Integration Snippets: reference/backend_integration_snippets.md
  - Calibration Overview: reference/calibration-overview.md
  - CLI: reference/cli.md
  - Control Panel Cheatsheet: reference/control-panel-cheatsheet.md
  - Database Schema: reference/database_schema.md
  - AOFlagger Configuration: reference/dsa110-default.lua
  - Environment Variables: reference/env.md
  - Critical Python Environment: reference/CRITICAL_PYTHON_ENVIRONMENT.md
  - Optimizations:
    - API: reference/optimizations/OPTIMIZATION_API.md
    - Profiling Guide: reference/optimizations/PROFILING_GUIDE.md
```

### Operations (5 entries, down from 6)
```yaml
- Operations:
  - Deployment:
    - Docker: operations/deploy-docker.md
    - systemd: operations/deploy-systemd.md
  - Port Management: operations/port-management.md
  - Refant Quick Reference: operations/refant_quick_reference.md
  - Service Restart Fix: operations/service_restart_fix.md
  - Systemd Migration: operations/systemd-migration.md
```

---

## Impact Summary

### Before Consolidation
- **Concepts:** 14 top-level entries
- **How-To Guides:** 27 top-level entries
- **Reference:** 12 top-level entries
- **Operations:** 6 top-level entries
- **Total:** 59 top-level navigation items

### After Consolidation
- **Concepts:** 11 top-level entries (3 grouped under Pipeline)
- **How-To Guides:** ~20-22 top-level entries (5-7 grouped)
- **Reference:** 9 top-level entries (3 grouped under API)
- **Operations:** 5 top-level entries (2 grouped under Deployment)
- **Total:** ~45-47 top-level navigation items

### Reduction
- **~12-14 fewer top-level entries** (20-24% reduction)
- **Better organization** - Related content grouped
- **No information loss** - All content still accessible
- **Improved discoverability** - Logical grouping helps users find related content

---

## Recommendations

### Phase 1: Safe Consolidations (Low Risk)
1. ✅ Group Pipeline documentation
2. ✅ Group Deployment operations
3. ✅ Group API reference

### Phase 2: Medium Consolidations (Medium Risk - Verify Content First)
1. ⚠️ Group Dashboard guides (verify no content overlap)
2. ⚠️ Group Quickstart entries
3. ⚠️ Group Conversion guides

### Phase 3: Advanced Consolidations (Higher Risk - Requires Content Review)
1. ⚠️ Group Mosaic guides (verify content difference)
2. ⚠️ Further group How-To Guides by topic

---

## Implementation Notes

1. **No content changes required** - Only navigation structure changes
2. **All files remain accessible** - Just organized better
3. **Backward compatible** - Direct links to files still work
4. **MkDocs handles nesting** - Material theme supports nested navigation well

---

## Conclusion

**Consolidation is feasible and beneficial** without information loss. The proposed structure:
- Reduces navigation clutter by ~20-24%
- Groups related content logically
- Improves discoverability
- Maintains all existing content

**Recommended approach:** Start with Phase 1 (safe consolidations), then evaluate user feedback before proceeding to Phase 2.

