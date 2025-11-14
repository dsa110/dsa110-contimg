# Documentation Consolidation Strategy

**Date:** 2025-11-12  
**Status:** In Progress  
**Purpose:** Unify and organize 1,113 markdown documentation files into a
maintainable, discoverable structure

---

## Executive Summary

The codebase currently has **179 markdown files** scattered across root
directories, source code directories, and various subdirectories. While the
`docs/` directory has good structure, many files remain in root
(`/data/dsa110-contimg/*.md`), source directories (`src/dsa110_contimg/*.md`),
and other locations. This document proposes a systematic approach to
consolidate, organize, and maintain documentation based on industry best
practices.

---

## Current State Analysis

### File Distribution (as of audit)

- **Root directory:** 27 files (keep: `README.md`, `MEMORY.md`)
- **docs/ directory:** 668 files (298 keep, 353 archive, 17 consolidate)
- **archive/**: 293 files (legacy, already segregated)
- **internal/**: 49 files (dev notes/status)
- **frontend/**: 28 files (keep)
- **docker/**: 18 files (keep)
- **tests/**: 14 files (keep)
- **src/**: 7 files (module READMEs; keep)
- **ops/**: 2 files (keep)

### Issues Identified

1. **Root directory clutter:** Many status reports, investigation reports, and
   test results in root
2. **Duplicate information:** Same concepts documented in multiple places
3. **Temporal files:** Status reports, test results, and investigation reports
   that should be archived
4. **Inconsistent naming:** Mix of UPPERCASE, lowercase, and mixed-case
   filenames
5. **Missing entry points:** No clear navigation structure for finding
   information
6. **Agent notes mixed with user docs:** Development notes scattered with
   user-facing documentation

---

## Strategy: Three-Tier Documentation Architecture

Based on industry best practices, we propose a **three-tier architecture**:

### Tier 1: User-Facing Documentation (`docs/`)

**Purpose:** Documentation for users, developers, and operators  
**Structure:** Organized by purpose (how-to, concepts, reference, tutorials)

### Tier 2: Development Notes (`internal/docs/dev/`)

**Purpose:** Agent notes, investigation reports, status updates, development
history  
**Structure:** Organized by topic and date

### Tier 3: Archive (`docs/archive/`)

**Purpose:** Historical status reports, completed investigations, deprecated
information  
**Structure:** Organized by date and topic

---

## Proposed Directory Structure

```
docs/
├── README.md                          # Main entry point with navigation
├── index.md                           # MkDocs index (if using MkDocs)
│
├── concepts/                          # Conceptual documentation
│   ├── README.md                     # Entry point for concepts
│   ├── architecture.md
│   ├── pipeline_overview.md
│   ├── glossary.md
│   └── ...
│
├── how-to/                           # Task-oriented guides
│   ├── README.md                     # Entry point for how-to guides
│   ├── quickstart.md
│   ├── calibration/
│   │   ├── README.md
│   │   ├── detailed_procedure.md
│   │   └── find_transit_data.md
│   ├── imaging/
│   │   ├── README.md
│   │   └── mosaic.md
│   └── ...
│
├── reference/                        # API, CLI, schema reference
│   ├── README.md
│   ├── api-endpoints.md
│   ├── cli.md
│   ├── database_schema.md
│   └── ...
│
├── tutorials/                        # Step-by-step tutorials
│   ├── README.md
│   ├── hdf5_to_ms.md
│   ├── calibrate_apply.md
│   └── ...
│
├── operations/                       # Operations and deployment
│   ├── README.md
│   ├── deployment/
│   │   ├── docker.md
│   │   └── systemd.md
│   └── troubleshooting/
│       └── common_issues.md
│
├── (internal)/docs/dev/              # Development notes (not published)
│   ├── README.md                     # Entry point for dev notes
│   │
│   ├── analysis/                     # Investigation reports
│   │   ├── README.md
│   │   ├── time_handling_issues.md
│   │   ├── ra_calculation_issue.md
│   │   ├── unanticipated_issues.md
│   │   └── ...
│   │
│   ├── status/                      # Status reports (temporal)
│   │   ├── README.md
│   │   ├── 2025-01/
│   │   │   ├── dashboard_status.md
│   │   │   └── testing_summary.md
│   │   └── ...
│   │
│   ├── history/                     # Development history
│   │   ├── README.md
│   │   ├── cursor_chat_history.md
│   │   └── changelog/
│   │       └── ...
│   │
│   └── notes/                       # Agent notes and brainstorming
│       ├── README.md
│       ├── architectural_elegance.md
│       └── ...
│
└── archive/                          # Historical documentation
    ├── README.md
    ├── status_reports/              # Completed status reports
    ├── investigations/               # Completed investigations
    └── experimental/                 # Experimental features
```

---

## Consolidation Plan

### Phase 1: Root Directory Cleanup (Priority: High)

**Move to `internal/docs/dev/status/`:**

- `DASHBOARD_ENDPOINT_TEST_RESULTS.md`
- `DASHBOARD_REAL_DATA_IMPLEMENTATION.md`
- `DASHBOARD_TBD_STATUS.md`
- `ENDPOINT_TEST_SUMMARY.md`
- `ENDPOINT_VERIFICATION_COMPLETE.md`
- `SKYVIEW_IMAGE_DISPLAY_VERIFICATION.md`
- `SKYVIEW_SPRINT1_COMPLETE.md`
- `SKYVIEW_TEST_RESULTS.md`
- `SKYVIEW_TROUBLESHOOTING.md`
- `TESTING_SUMMARY.md`
- `TEST_RESULTS.md`
- `VALIDATION_DEMONSTRATION.md`

**Move to `internal/docs/dev/analysis/`:**

- `TIME_INVESTIGATION_REPORT.md`
- `TIME_VALIDATION_STRATEGY.md`
- `DUPLICATE_TIME_INVESTIGATION.md`
- `BUG_REPORT.md` (if still relevant)

**Move to `internal/docs/dev/notes/`:**

- `ARCHITECTURAL_ELEGANCE_BRAINSTORM.md`
- `ARCHITECTURE_OPTIMIZATION_RECOMMENDATIONS.md`
- `PYUVDATA_USAGE_ANALYSIS.md`

**Move to `docs/reference/`:**

- `DEVELOPER_GUIDE.md` → `docs/reference/developer_guide.md`

**Keep in root:**

- `README.md` (main project README)
- `MEMORY.md` (agent memory file - special case)
- `TODO.md` (if actively used)

**Archive:**

- `DOCKER_CONFIG_UPDATE.md` → `docs/archive/` (if completed)
- `DOCKER_CONFIG_VERIFICATION.md` → `docs/archive/` (if completed)

### Phase 2: Source Directory Cleanup (Priority: High)

**Move to `internal/docs/dev/analysis/`:**

- `src/dsa110_contimg/RA_CALCULATION_ISSUE.md`
- `src/dsa110_contimg/TIME_HANDLING_ISSUES.md`

**Keep in source directories:**

- Module-level `README.md` files (e.g.,
  `src/dsa110_contimg/calibration/README.md`)
  - These provide context for code navigation

### Phase 3: Docker Directory Cleanup (Priority: Medium)

**Move to `internal/docs/dev/status/experimental/`:**

- All `docker/cubical_experimental/*.md` status files
- Keep only `docker/cubical_experimental/README.md` in place

### Phase 4: Consolidate Duplicate Content (Priority: Medium)

**Review and merge (Progress):**

- QA Visualization: Kept Quick Start, Usage, and Design; archived seven
  dashboard/testing/status variants to `docs/archive/qa_visualization/`.
- Prettier: Created `docs/how-to/PRETTIER_TROUBLESHOOTING.md`; archived
  environment-specific and applied-fixes docs to `docs/archive/prettier/`;
  converted `PRETTIER_WARNINGS.md` to a redirect.
- Developer Handoff: Kept `DEVELOPER_HANDOFF_WARNINGS.md`; converted
  `DEVELOPER_HANDOVER_WARNINGS.md` to a redirect.

Remaining merges:

- Consolidate multiple calibration/testing procedure variants under a single
  canonical guide per topic.
- Collapse remaining quickstarts that duplicate handbook content.

### Phase 5: Archive Time-Bound Analysis/Reports (Completed)

- Moved `docs/analysis/` → `docs/archive/analysis/` (126 files)
- Moved `docs/reports/` → `docs/archive/reports/` (41 files)
- Moved `docs/dev/` → `internal/docs/dev/imported/` (182 files)

**Create single source of truth:**

- `docs/how-to/calibration/detailed_procedure.md` (merge all calibration docs)
- `docs/how-to/quickstart.md` (merge all quickstart variants)
- `docs/concepts/testing_strategy.md` (merge testing documents)

### Phase 5: Improve Navigation (Priority: High)

**Create entry point READMEs:**

- `docs/README.md` - Main documentation index
- `docs/concepts/README.md` - Concepts overview
- `docs/how-to/README.md` - How-to guides index
- `docs/reference/README.md` - Reference documentation index
- `internal/docs/dev/README.md` - Development notes index
- `docs/archive/README.md` - Archive index

**Add cross-references:**

- Link related documents
- Add "See also" sections
- Create topic-based navigation

---

## File Naming Conventions

### Standardize to lowercase with underscores:

- ✅ `calibration_detailed_procedure.md`
- ✅ `time_handling_issues.md`
- ✅ `dashboard_status.md`
- ❌ `CALIBRATION_DETAILED_PROCEDURE.md`
- ❌ `TIME_HANDLING_ISSUES.md`
- ❌ `Dashboard-Status.md`

### Naming Patterns:

- **Concepts:** `concept_name.md` (e.g., `pipeline_overview.md`)
- **How-to guides:** `task_name.md` (e.g., `calibrate_ms.md`)
- **Reference:** `component_name.md` (e.g., `api_endpoints.md`)
- **Status reports:** `YYYY-MM-DD_component_status.md` (e.g.,
  `2025-01-15_dashboard_status.md`)
- **Analysis:** `topic_analysis.md` (e.g., `time_handling_analysis.md`)

---

## Documentation Lifecycle Management

### Status Reports (Temporal)

1. **Create** in `internal/docs/dev/status/YYYY-MM/`
2. **Update** as needed during development
3. **Archive** to `docs/archive/status_reports/` when complete or superseded
4. **Link** from relevant permanent documentation

### Investigation Reports

1. **Create** in `internal/docs/dev/analysis/`
2. **Update** with findings
3. **Move** to `internal/docs/dev/history/` when investigation complete
4. **Extract** key findings to permanent documentation

### Notes

1. **Create** in `internal/docs/dev/notes/`
2. **Review** periodically for valuable insights
3. **Extract** insights to permanent documentation
4. **Archive** when no longer relevant

---

## Implementation Steps

### Step 1: Create New Directory Structure

```bash
mkdir -p internal/docs/dev/{analysis,status,history,notes}
mkdir -p docs/archive/{status_reports,investigations,experimental}
```

### Step 2: Move Files (Batch 1: Root Directory)

```bash
# Status reports
mv DASHBOARD_*.md internal/docs/dev/status/2025-01/
mv ENDPOINT_*.md internal/docs/dev/status/2025-01/
mv SKYVIEW_*.md internal/docs/dev/status/2025-01/
mv TEST*.md internal/docs/dev/status/2025-01/
mv VALIDATION_DEMONSTRATION.md internal/docs/dev/status/2025-01/

# Analysis reports
mv TIME_*.md internal/docs/dev/analysis/
mv DUPLICATE_TIME_INVESTIGATION.md internal/docs/dev/analysis/
mv BUG_REPORT.md internal/docs/dev/analysis/

# Notes
mv ARCHITECTURAL_*.md internal/docs/dev/notes/
mv ARCHITECTURE_OPTIMIZATION_RECOMMENDATIONS.md internal/docs/dev/notes/
mv PYUVDATA_USAGE_ANALYSIS.md internal/docs/dev/notes/

# Reference
mv DEVELOPER_GUIDE.md docs/reference/developer_guide.md
```

### Step 3: Move Files (Batch 2: Source Directories)

```bash
mv src/dsa110_contimg/RA_CALCULATION_ISSUE.md internal/docs/dev/analysis/
mv src/dsa110_contimg/TIME_HANDLING_ISSUES.md internal/docs/dev/analysis/
```

### Step 4: Create Entry Point READMEs

Create `README.md` files in each major directory with:

- Purpose statement
- List of documents
- Navigation links
- Last updated date

### Step 5: Update Cross-References

- Update links in moved files
- Update references in code comments
- Update references in other documentation

### Step 6: Rename Files (Standardize)

```bash
# Convert UPPERCASE to lowercase_with_underscores
# Use find + sed or manual renaming
```

---

## Maintenance Guidelines

### For Agents Writing Documentation

1. **Choose the right location:**
   - **User-facing docs:** `docs/how-to/`, `docs/concepts/`, `docs/reference/`
   - **Status updates:** `internal/docs/dev/status/YYYY-MM/`
   - **Investigation reports:** `internal/docs/dev/analysis/`
   - **Notes:** `internal/docs/dev/notes/`

2. **Use consistent naming:**
   - Lowercase with underscores
   - Descriptive names
   - Avoid dates in filenames (use directory structure instead)

3. **Add metadata:**
   - Date created/updated
   - Status (draft, review, complete, archived)
   - Related documents

4. **Link to related docs:**
   - Use relative links
   - Add "See also" sections
   - Cross-reference concepts

5. **Review periodically:**
   - Move completed status reports to archive
   - Extract insights from notes to permanent docs
   - Remove obsolete information

### For Maintainers

1. **Monthly review:**
   - Archive completed status reports
   - Consolidate duplicate content
   - Update entry point READMEs

2. **Quarterly audit:**
   - Review documentation structure
   - Identify gaps
   - Update navigation

3. **Annual cleanup:**
   - Archive old status reports (>1 year)
   - Remove obsolete documentation
   - Update main README

---

## Tools and Automation

### Recommended Tools

1. **MkDocs** or **Sphinx:**
   - Generate HTML documentation from markdown
   - Automatic navigation
   - Search functionality
   - Version control integration

2. **Documentation Linter:**
   - Check markdown syntax
   - Verify links
   - Check for broken references

3. **Link Checker:**
   - Verify all internal links work
   - Check external links periodically

4. **Search Index:**
   - Full-text search across documentation
   - Tag-based organization

### Automation Scripts

Create scripts for:

- Moving files to correct locations
- Renaming files (UPPERCASE → lowercase)
- Generating entry point READMEs
- Checking for broken links
- Archiving old status reports

---

## Success Metrics

### Immediate (After Consolidation)

- ✅ No markdown files in root directory (except README.md, MEMORY.md, TODO.md)
- ✅ All status reports in `internal/docs/dev/status/`
- ✅ All analysis reports in `internal/docs/dev/analysis/`
- ✅ Consistent file naming (lowercase_with_underscores)

### Short-term (3 months)

- ✅ Entry point READMEs in all major directories
- ✅ Cross-references between related documents
- ✅ No duplicate content
- ✅ Clear navigation structure

### Long-term (6+ months)

- ✅ Documentation site (MkDocs/Sphinx) deployed
- ✅ Search functionality working
- ✅ Regular maintenance schedule established
- ✅ Documentation quality metrics tracked

---

## Migration Checklist

- [ ] Create new directory structure
- [ ] Move root directory files
- [ ] Move source directory files
- [ ] Move docker experimental files
- [ ] Create entry point READMEs
- [ ] Update cross-references
- [ ] Rename files (standardize)
- [ ] Consolidate duplicate content
- [ ] Update main README.md
- [ ] Test all links
- [ ] Archive old status reports
- [ ] Document maintenance procedures

---

## References

Based on industry best practices from:

- Markdown Documentation Best Practices (IBM)
- Microsoft Engineering Playbook
- GitBook Documentation Structure Guide
- CommonMark Markdown Specification

---

## Next Steps

1. **Review this strategy** with team
2. **Approve directory structure** and naming conventions
3. **Create migration script** for automated file moves
4. **Execute Phase 1** (root directory cleanup)
5. **Iterate** based on feedback
