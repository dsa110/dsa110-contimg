# Documentation Audit Report

**Date:** November 26, 2025  
**Status:** ✅ IMPLEMENTED - Changes Applied

---

## Changes Applied Summary

The following cleanup actions have been completed:

### ✅ Completed Actions

1. **Fixed CODE_MAP.md broken links** - All `concepts/` →
   `architecture/pipeline/`, `how-to/` → `guides/`

2. **Consolidated dashboard documentation** - 20+ historical files archived to
   `docs/archive/dashboard-historical/`

3. **Consolidated port documentation** - 11 redundant port files archived to
   `docs/archive/operations/`, `ports.md` is now authoritative

4. **Merged absurd guides** - Added deprecation notices pointing to canonical
   `docs/operations/absurd_operations.md`

5. **Updated root README.md** - Replaced embedded database schemas with links to
   `docs/reference/DATABASE_REFERENCE_INDEX.md`

6. **Fixed port 3000 vs 5173 references** - Corrected port references in:

   - `control-panel-cheatsheet.md`
   - `control-panel.md`
   - `dashboard_development_workflow.md`
   - `image_filters_manual_testing_guide.md`

7. **Archived completed analysis docs** - 4 completed implementation records
   moved to `docs/archive/analysis-completed/`

### Archive Directories Created

- `docs/archive/operations/` - Port documentation history (11 files)
- `docs/archive/dashboard-historical/` - Historical dashboard docs (20+ files)
- `docs/archive/workflow-historical/` - Completed workflow docs (4 files)
- `docs/archive/analysis-completed/` - Completed analysis records (4 files)

Each archive directory has a README explaining what was archived and why.

---

## Original Audit Findings (for reference)

## Executive Summary

The DSA-110 Continuum Imaging Pipeline has **833 markdown files** in `docs/`
alone, with additional documentation in `backend/docs/` (29 files),
`frontend/docs/` (5 files), and `ops/` (25 files). This audit identifies:

- **Significant redundancy** across multiple documentation locations
- **Broken internal links** referencing non-existent directories
- **Stale/outdated content** mixed with current documentation
- **Inconsistent organization** making discovery difficult

---

## 1. Critical Issues

### 1.1 Broken Link Patterns

The following link patterns reference **non-existent directories**:

| Referenced Path        | Actual Location                             | Files Affected                  |
| ---------------------- | ------------------------------------------- | ------------------------------- |
| `concepts/`            | `architecture/` or `architecture/pipeline/` | CODE_MAP.md, 20+ archived files |
| `how-to/`              | `guides/`                                   | CODE_MAP.md, 15+ archived files |
| `../how-to/workflow/`  | `../guides/workflow/`                       | CODE_MAP.md                     |
| `../how-to/dashboard/` | `../guides/dashboard/`                      | CODE_MAP.md                     |

**Impact:** Users following these links encounter 404 errors.

### 1.2 Contradictory Information

| Topic          | Conflict                                                                                           |
| -------------- | -------------------------------------------------------------------------------------------------- |
| Dashboard Port | `ports.md` says 5173/3210, `port-management.md` says 3000, `control-panel-quickstart.md` says 3000 |
| Frontend Start | `npm run dev` vs `npm start` (different docs disagree)                                             |

---

## 2. Redundant Documentation

### 2.1 Dashboard Quick Start Guides (5+ versions)

All cover essentially the same content with slight variations:

| File                                           | Lines | Notes                                                                     |
| ---------------------------------------------- | ----- | ------------------------------------------------------------------------- |
| `guides/dashboard/dashboard-quickstart.md`     | 451   | Says "Moved, see docs/how-to/dashboard.md" but then contains full content |
| `guides/dashboard/quickstart_dashboard.md`     | 60    | TL;DR version                                                             |
| `guides/dashboard/control-panel-quickstart.md` | 313   | Control panel focused                                                     |
| `guides/dashboard/dashboard.md`                | ?     | General dashboard                                                         |
| `archive/carta_quick_start.md`                 | ?     | CARTA-focused quick start                                                 |

**Recommendation:** Consolidate into single `guides/dashboard/quickstart.md`.

### 2.2 Absurd Workflow Documentation (10+ versions)

| Location                                             | Files     | Purpose                 |
| ---------------------------------------------------- | --------- | ----------------------- |
| `docs/guides/ABSURD_QUICKSTART.md`                   | 813 lines | Full quickstart         |
| `docs/operations/absurd_operations.md`               | 544 lines | Operations guide        |
| `docs/guides/workflow/absurd_*.md`                   | 7 files   | Various workflow guides |
| `docs/architecture/pipeline/absurd_*.md`             | 3 files   | Architecture docs       |
| `backend/docs/operations/absurd_operations_guide.md` | 478 lines | Duplicate ops guide     |
| `docs/archive/.../absurd_*.md`                       | 8 files   | Historical status       |

**Overlap:** `docs/operations/absurd_operations.md` and
`backend/docs/operations/absurd_operations_guide.md` cover nearly identical
content.

**Recommendation:**

- Single authoritative guide: `docs/guides/workflow/absurd.md`
- Reference doc: `docs/reference/absurd-api.md`
- Archive all `*_status.md`, `*_complete.md`, `*_phase*.md` files

### 2.3 Port Configuration Documentation (10+ files)

| File                                             | Lines   | Content                               |
| ------------------------------------------------ | ------- | ------------------------------------- |
| `operations/ports.md`                            | 180     | Port reference (claims authoritative) |
| `operations/PORT_ASSIGNMENTS_QUICK_REFERENCE.md` | 50      | Another quick reference               |
| `operations/port-management.md`                  | 297     | Service management                    |
| `operations/port_audit_report.md`                | ?       | Historical audit                      |
| `operations/port_duplicate_*.md`                 | 2 files | Issue tracking                        |
| `operations/port_safeguards_*.md`                | 2 files | Implementation notes                  |
| `operations/port_system_*.md`                    | 1 file  | System guide                          |
| `operations/port_unknown_*.md`                   | 2 files | Investigation                         |

**Recommendation:** Keep only:

- `operations/ports.md` - Authoritative reference
- Archive rest as `archive/operations/port_history/`

### 2.4 Database Schema Documentation (5+ locations)

| File                                    | Content                                 |
| --------------------------------------- | --------------------------------------- |
| `reference/database_schema.md`          | 606 lines - full schemas                |
| `reference/DATABASE_REFERENCE_INDEX.md` | 441 lines - index to individual DB docs |
| `reference/database_quick_reference.md` | Quick access patterns                   |
| `reference/database_*_sqlite3.md`       | 6 files - per-database docs             |
| `SYSTEM_CONTEXT.md`                     | Lines 27-70 - data model overview       |
| `README.md`                             | Lines 150-170 - database summary        |

**Recommendation:**

- `reference/database/` directory with:
  - `overview.md` (from SYSTEM_CONTEXT)
  - `products.md`, `ingest.md`, `hdf5.md`, etc.
- Remove database section from root README (link instead)

---

## 3. Stale/Outdated Content

### 3.1 Archive Directory Issues

The `docs/archive/` directory contains:

- **45+ status reports** (e.g., `COMPLETION_SUMMARY.md`, `FINAL_TEST_REPORT.md`)
- **12+ implementation logs** documenting completed work
- **Historical feature docs** (e.g., `PLOTLY_FIX.md`,
  `JS9_OPTIMIZATION_APPLIED.md`)

**Problem:** These are valuable for history but clutter search results and
confuse AI assistants.

**Recommendation:**

1. Add `ARCHIVAL_NOTE.md` at top of each archive subdirectory
2. Consider moving to `.local/archive/docs/` (gitignored history)
3. Keep only `archive/CHANGELOG.md` summarizing historical changes

### 3.2 Files Starting with "Moved" or Deprecated Notices

| File                                       | Issue                                  |
| ------------------------------------------ | -------------------------------------- |
| `guides/dashboard/dashboard-quickstart.md` | Says "Moved" but contains full content |
| `CODE_MAP.md` deprecation warnings         | References incorrect file paths        |

---

## 4. Structural Improvements

### 4.1 Current Structure (Problematic)

```
docs/
├── SYSTEM_CONTEXT.md          # Good - keep
├── CODE_MAP.md                # Broken links
├── index.md                   # Good - keep
├── architecture/              # Good category
│   ├── dashboard/             # Overlaps with guides/dashboard
│   └── pipeline/              # Good
├── guides/                    # Good category
│   ├── dashboard/             # 35 files! Too many
│   └── workflow/              # 10 absurd files
├── operations/                # Good category
│   └── (10+ port files)       # Redundant
├── reference/                 # Good category
│   └── (80+ files)            # Many redundant
├── archive/                   # Historical
│   └── (100+ files)           # Should be more organized
└── ... (more subdirs)
```

### 4.2 Proposed Structure

```
docs/
├── README.md                  # Entry point (links to index)
├── index.md                   # Main documentation hub
├── SYSTEM_CONTEXT.md          # Technical architecture (keep)
├── CODE_MAP.md                # Fix links, simplify
│
├── getting-started/           # NEW: Consolidated quick starts
│   ├── quickstart.md          # 5-minute setup
│   ├── developer-setup.md     # Full dev environment
│   └── first-pipeline-run.md  # Run first observation
│
├── guides/                    # How-to guides (task-focused)
│   ├── dashboard.md           # Single dashboard guide
│   ├── absurd-workflow.md     # Single absurd guide
│   ├── calibration.md         # Calibration procedures
│   ├── imaging.md             # Imaging procedures
│   └── troubleshooting.md     # Common issues
│
├── reference/                 # API/config reference
│   ├── api.md                 # API reference
│   ├── cli.md                 # CLI reference
│   ├── configuration.md       # All config options
│   ├── ports.md               # Port assignments
│   └── database/              # Database schemas
│       ├── overview.md
│       └── (per-db files)
│
├── architecture/              # Design documents
│   ├── overview.md            # System architecture
│   ├── pipeline.md            # Pipeline design
│   ├── streaming.md           # Streaming architecture
│   └── frontend.md            # Frontend architecture
│
├── operations/                # Production operations
│   ├── deployment.md          # Deployment guide
│   ├── monitoring.md          # Monitoring & metrics
│   ├── maintenance.md         # Routine maintenance
│   └── runbooks/              # Operational procedures
│
└── archive/                   # Historical (reorganized)
    ├── ARCHIVAL_NOTE.md       # Explains archive policy
    ├── 2025-01/               # By month
    └── features/              # Completed feature docs
```

---

## 5. Recommended Actions

### Immediate (High Priority)

1. **Fix CODE_MAP.md broken links**

   - Replace `concepts/` → `architecture/pipeline/`
   - Replace `how-to/` → `guides/`

2. **Consolidate dashboard quick starts**

   - Create single `guides/dashboard.md`
   - Archive duplicates

3. **Consolidate port documentation**
   - Keep `operations/ports.md` as authoritative
   - Archive 9 other port-related files

### Short-term (Medium Priority)

4. **Consolidate absurd documentation**

   - Merge 3 operations guides into 1
   - Archive phase completion docs

5. **Update root README.md**

   - Remove embedded database schema details
   - Add link to reference docs

6. **Standardize frontend port references**
   - Audit all docs for port 3000 vs 5173
   - Update to reflect actual configuration

### Long-term (Lower Priority)

7. **Reorganize archive/**

   - Add index/README explaining what's archived
   - Consider moving to separate history repo

8. **Create documentation contribution guide**
   - Where to add new docs
   - How to avoid duplication
   - Link maintenance procedures

---

## 6. Metrics

| Metric                   | Current | Target |
| ------------------------ | ------- | ------ |
| Total MD files in docs/  | 833     | ~100   |
| Dashboard quick starts   | 5+      | 1      |
| Absurd operation guides  | 3+      | 1      |
| Port documentation files | 10+     | 1      |
| Broken internal links    | 20+     | 0      |

---

## Appendix: Files Recommended for Archival

### Port Documentation → `archive/operations/port_history/`

- `port_audit_report.md`
- `port_duplicate_detection_fix.md`
- `port_duplicate_vite_explanation.md`
- `port_organization_recommendations.md`
- `port_safeguards_analysis.md`
- `port_system_implementation_guide.md`
- `port_unknown_ports_resolution.md`
- `port_usage_unknown_ports.md`
- `PORT_ASSIGNMENTS_QUICK_REFERENCE.md`
- `frontend_dev_port_migration.md`

### Dashboard Quick Starts → `archive/guides/dashboard/`

- `quickstart_dashboard.md` (keep content in `dashboard-quickstart.md`)
- `control-panel-quickstart.md` (merge into main guide)

### Absurd Status Docs → `archive/absurd/`

- All `absurd_phase*_complete.md` files
- All `absurd_*_status.md` files
- `absurd_next_steps_completion.md`
