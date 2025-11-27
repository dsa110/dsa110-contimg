# Documentation Quick Reference Guide

**For:** AI Agents and Developers  
**Purpose:** Quick guide for where to put documentation

---

## Where Should I Put This Document?

### User-Facing Documentation

**`docs/how-to/`** - Task-oriented guides

- ✅ "How do I calibrate an MS file?"
- ✅ "How do I create a mosaic?"
- ✅ "How do I troubleshoot X?"
- ❌ Status reports
- ❌ Investigation reports

**`docs/concepts/`** - Conceptual explanations

- ✅ "What is calibration?"
- ✅ "How does the pipeline work?"
- ✅ Architecture overviews
- ❌ Step-by-step procedures

**`docs/reference/`** - API, CLI, schema reference

- ✅ API endpoint documentation
- ✅ CLI command reference
- ✅ Database schema
- ✅ Configuration options
- ❌ Tutorials or how-to guides

**`docs/tutorials/`** - Step-by-step tutorials

- ✅ "Tutorial: Convert HDF5 to MS"
- ✅ "Tutorial: Calibrate and Image"
- ❌ Reference documentation

### Development Notes

**`internal/docs/dev/status/YYYY-MM/`** - Status reports (temporal)

- ✅ "Dashboard implementation status"
- ✅ "Testing summary for sprint X"
- ✅ "Endpoint verification results"
- ⚠️ Archive when complete (>1 month old)

**`internal/docs/dev/analysis/`** - Investigation reports

- ✅ "Time handling issues analysis"
- ✅ "RA calculation bug investigation"
- ✅ "Performance analysis"
- ⚠️ Move to `docs/dev/history/` when complete

**`internal/docs/dev/notes/`** - Development notes and brainstorming

- ✅ Architectural brainstorming
- ✅ Design considerations
- ✅ Implementation notes
- ⚠️ Extract insights to permanent docs periodically

**`internal/docs/dev/history/`** - Completed investigations

- ✅ Completed analysis reports
- ✅ Development history
- ✅ Changelog entries

### Archive

**`docs/archive/`** - Historical documentation

- ✅ Completed status reports (>1 year old)
- ✅ Superseded documentation
- ✅ Experimental features that didn't work out

---

## File Naming Rules

### ✅ DO:

- Use lowercase: `calibration_procedure.md`
- Use underscores: `time_handling_issues.md`
- Be descriptive: `find_calibrator_transit_data.md`
- Keep it short: `quickstart.md` not `quick_start_guide_for_new_users.md`

### ❌ DON'T:

- Use UPPERCASE: `CALIBRATION_PROCEDURE.md`
- Use spaces: `calibration procedure.md`
- Use dates in filenames: `2025-01-15_status.md` (use directory instead)
- Use special chars: `calibration@procedure.md`

---

## Document Structure Templates

### Template 1: Simple Markdown (Default)

**Use for:** Most documentation, especially how-to guides and tutorials

```markdown
# Document Title

**Date:** YYYY-MM-DD  
**Status:** draft | review | complete | archived  
**Related:** [link to related docs]

---

## Overview

Brief description of what this document covers.

## Main Content

### Section 1

Content here.

### Section 2

Content here.

## See Also

- [Related Document 1](path/to/doc1.md)
- [Related Document 2](path/to/doc2.md)

## References

- External links if applicable
```

### Template 2: YAML Frontmatter (For Structured Docs)

**Use for:** Status reports, analysis reports, concept docs, reference docs

**Why:** Makes it easier for AI agents to parse, filter, and search
documentation.

```markdown
---
date: YYYY-MM-DD
title: Document Title
type: [status-report|analysis|concept|reference|how-to|tutorial]
status: [draft|review|complete|archived]
tags: [tag1, tag2, tag3]
related: [path/to/doc1.md, path/to/doc2.md]
affected_areas: [area1, area2]
---

# Document Title

## Overview

Brief description of what this document covers.

## Main Content

### Section 1

Content here.

### Section 2

Content here.

## See Also

- [Related Document 1](path/to/doc1.md)
- [Related Document 2](path/to/doc2.md)
```

**When to use frontmatter:**

- ✅ Status reports (`internal/docs/dev/status/`)
- ✅ Analysis reports (`internal/docs/dev/analysis/`)
- ✅ Concept docs (`docs/concepts/`)
- ✅ Reference docs (`docs/reference/`)

**When to use simple format:**

- ✅ Basic how-to guides (`docs/how-to/`)
- ✅ Tutorials (`docs/tutorials/`)
- ✅ Quick reference snippets

**For more details:** See
DOCUMENTATION_FORMAT_RECOMMENDATION.md

---

## Quick Decision Tree

```
Is this documentation for end users?
├─ YES → Is it a step-by-step procedure?
│   ├─ YES → docs/how-to/
│   └─ NO → Is it a concept explanation?
│       ├─ YES → docs/concepts/
│       └─ NO → Is it API/CLI reference?
│           ├─ YES → docs/reference/
│           └─ NO → docs/tutorials/
│
└─ NO → Is this a status update?
    ├─ YES → internal/docs/dev/status/YYYY-MM/
    └─ NO → Is this an investigation?
        ├─ YES → internal/docs/dev/analysis/
        └─ NO → Is this agent notes?
            ├─ YES → internal/docs/dev/notes/
            └─ NO → Is this historical?
                └─ YES → docs/archive/
```

---

## Common Mistakes to Avoid

1. **Putting status reports in root** → Use `internal/docs/dev/status/`
2. **Creating duplicate docs** → Check if similar doc exists first
3. **Using UPPERCASE filenames** → Use lowercase_with_underscores
4. **Not linking related docs** → Add "See also" section
5. **Forgetting metadata** → Add date, status, related docs
6. **Mixing user docs with dev notes** → Keep them separate

---

## Examples

### ✅ Good: User-Facing How-To

**Location:** `docs/how-to/calibration/detailed_procedure.md` **Name:**
`detailed_procedure.md` (not `CALIBRATION_DETAILED_PROCEDURE.md`) **Content:**
Step-by-step instructions for users

### ✅ Good: Status Report

**Location:** `internal/docs/dev/status/2025-01/dashboard_implementation.md`
**Name:** `dashboard_implementation.md` (not `DASHBOARD_STATUS_2025-01-15.md`)
**Content:** Current status, next steps, blockers

### ✅ Good: Analysis Report

**Location:** `internal/docs/dev/analysis/time_handling_issues.md` **Name:**
`time_handling_issues.md` (not `TIME_HANDLING_ISSUES.md`) **Content:**
Investigation findings, root cause, fix

### ❌ Bad: Root Directory Status Report

**Location:** `/data/dsa110-contimg/DASHBOARD_STATUS.md` **Should be:**
`internal/docs/dev/status/2025-01/dashboard_status.md`

### ❌ Bad: UPPERCASE Filename

**Name:** `CALIBRATION_PROCEDURE.md` **Should be:** `calibration_procedure.md`

---

## Questions?

- Check `docs/DOCUMENTATION_CONSOLIDATION_STRATEGY.md` for full strategy
- Review
  DOCUMENTATION_FORMAT_RECOMMENDATION.md
  for format guidelines
- Review existing docs in target directory for examples
- When in doubt, ask before creating new docs
