# Documentation Audit Summary

**Date:** 2025-11-12  
**Status:** Complete

## Overview

Performed comprehensive audit of mkdocs documentation to ensure 100% consistency with current pipeline state. Outdated, obsolete, and irrelevant documentation has been moved to `archive/legacy/`.

## Files Archived

### Migration Documentation (Historical Status Reports)
Moved to `archive/legacy/docs/migration/`:
- `LEGACY_CLEANUP_COMPLETE.md`
- `LEGACY_CLEANUP_PLAN.md`
- `LEGACY_DEPRECATION_PLAN.md`
- `MIGRATION_PHASE1_COMPLETE.md`
- `MIGRATION_PHASE2_COMPLETE.md`

**Reason:** These document completed migration work and are no longer relevant to current users.

### Cursor Chat Files (Development History)
Moved to `archive/legacy/docs/cursor-chats/`:
- `cursor_chat_design_calibration_procedure_251106b.md`
- `cursor_chat_optimized_refactor_251106a.md`
- `cursor_chat_prepare_streaming_251106c.md`
- `cursor_chat_setup_dashboard_251106d.md`

**Reason:** These are historical development conversations, not user-facing documentation.

### Testing Documentation
Moved to `archive/legacy/docs/`:
- `how-to/TEST_NEW_PIPELINE.md` - The new pipeline is now the default, so this guide is obsolete.

## Documentation Updates

### Updated References

1. **Pipeline Framework** (`docs/reference/env.md`):
   - Removed references to `USE_NEW_PIPELINE` environment variable
   - Updated to reflect that new pipeline framework is now the default and only option
   - Legacy subprocess-based execution has been removed

2. **Architecture Documentation** (`docs/concepts/architecture.md`):
   - Updated `direct-subband` → `parallel-subband` (correct production writer name)
   - Note: `direct-subband` is an alias for `parallel-subband` (backward compatibility)

3. **Pipeline Overview** (`docs/concepts/pipeline_overview.md`):
   - Updated imaging backend references: `tclean` → `WSClean` (default backend)
   - Added note that WSClean is default (2-5x faster), tclean available via `--backend tclean`
   - Added clarification that `direct-subband` is an alias for `parallel-subband`

4. **Pipeline Workflow Visualization** (`docs/concepts/pipeline_workflow_visualization.md`):
   - Updated all `tclean` references to `WSClean` (default backend)
   - Added note about tclean availability as alternative backend

5. **Developer Guide** (`docs/reference/developer_guide.md`):
   - Removed references to legacy pipeline mode and `USE_NEW_PIPELINE`
   - Updated to reflect that new pipeline framework is the only execution mode
   - Legacy code has been archived

6. **Pipeline Deep Understanding** (`docs/analysis/PIPELINE_DEEP_UNDERSTANDING.md`):
   - Updated to reflect that new pipeline is default and only option
   - Legacy code archived to `archive/legacy/api/job_runner_legacy.py`

7. **Testing Index** (`docs/how-to/TESTING_INDEX.md`):
   - Removed reference to `TEST_NEW_PIPELINE.md` (archived)
   - Updated to reflect that pipeline framework is now default

## Key Corrections

### Writer Terminology
- **Correct**: `parallel-subband` is the production writer
- **Note**: `direct-subband` is an alias (backward compatibility)
- **Testing**: `pyuvdata` writer available for ≤2 subbands only

### Imaging Backend
- **Default**: WSClean (2-5x faster than tclean)
- **Alternative**: tclean available via `--backend tclean`
- All documentation updated to reflect WSClean as default

### Pipeline Framework
- **Current State**: New pipeline framework is the default and only execution mode
- **Legacy Code**: Archived to `archive/legacy/api/job_runner_legacy.py`
- **Environment Variables**: `USE_NEW_PIPELINE` and `USE_LEGACY_PIPELINE` no longer relevant

## Verification

All documentation now accurately reflects:
- ✅ Current pipeline architecture (stage-based orchestrator)
- ✅ Default imaging backend (WSClean)
- ✅ Production writer (`parallel-subband`)
- ✅ Pipeline framework status (new framework is default)
- ✅ Removed references to deprecated patterns

## Files Not Changed

The following files were reviewed but found to be current:
- CLI reference documentation (`docs/reference/cli.md`)
- How-to guides (verified against current implementation)
- Concepts documentation (updated where needed)
- Tutorials (verified accuracy)

## Next Steps

1. ✅ Documentation audit complete
2. ✅ Outdated content archived
3. ✅ References updated
4. ⏳ Monitor for any remaining inconsistencies
5. ⏳ Regular audits recommended quarterly

## Archive Location

All archived documentation is preserved in:
- `archive/legacy/docs/migration/` - Migration status reports
- `archive/legacy/docs/cursor-chats/` - Development history
- `archive/legacy/docs/` - Other obsolete documentation

**Note:** Archived files are preserved for historical reference but are not included in mkdocs navigation.

