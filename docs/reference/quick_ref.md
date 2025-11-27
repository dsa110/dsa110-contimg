# Documentation Quick Reference Guide

**For:** AI Agents and Developers  
**Purpose:** Quick guide for creating and formatting frontend documentation  
**Date:** 2025-11-16  
**Status:** ✅ Current

---

## 📚 Quick Navigation

- **Master Index:** INDEX.md - All documentation organized by
  category
- **Agent Guidelines:** AGENT_GUIDELINES.md - Templates
  and procedures
- **Consolidation Strategy:**
  [CONSOLIDATION_STRATEGY.md](../design/strategies/CONSOLIDATION_STRATEGY.md) - Overview of
  documentation system

---

## 🎨 Markdown Formatting Framework: **Prettier**

### Configuration

**Prettier** is configured for markdown files with markdown-specific settings in
the root `.prettierrc`:

```json
{
  "files": "*.md",
  "options": {
    "proseWrap": "always",
    "printWidth": 80
  }
}
```

### Markdown Formatting Rules

- **Line width:** 80 characters (vs 100 for code)
- **Prose wrap:** `"always"` (wraps lines automatically)
- **End of line:** LF (`\n`)
- **Applied to:** all `.md` files in the repository

### Integration Points

1. **Pre-commit hooks:** Automatically formats markdown files on commit
2. **CI/CD:** `.github/workflows/prettier-check.yml` validates formatting
3. **Manual formatting:** Can be run with `npx prettier --write "docs/**/*.md"`

---

## 📁 Documentation Structure

### Frontend Documentation Location

**All frontend documentation should be in:**

- **`frontend/docs/`** - Main documentation directory
- **`frontend/docs/analysis/`** - Analysis reports and investigations
- **`frontend/docs/`** - Implementation guides, debugging, testing, status
  reports

### Organization by Category

See INDEX.md for complete categorization. Main categories:

1. **Getting Started & Overview** - Main README, codebase analysis
2. **Implementation Guides** - Feature implementation step-by-step
3. **Testing Documentation** - Testing strategies, setup, results
4. **Debugging & Troubleshooting** - Issue resolution, debugging guides
5. **Development Environment** - Server setup, environment config
6. **Analysis & Research** - Research findings, architectural decisions
7. **Audit & Status Reports** - Audit reports, status summaries

---

## 📝 File Naming Conventions

### ✅ DO:

- Use lowercase: `calibration_procedure.md`
- Use underscores: `time_handling_issues.md`
- Be descriptive but concise: `sky_map_implementation.md`
- Keep it short: `quickstart.md` not `quick_start_guide_for_new_users.md`

### ❌ DON'T:

- Use UPPERCASE: `CALIBRATION_PROCEDURE.md`
- Use spaces: `calibration procedure.md`
- Use dates in filenames: `2025-01-15_status.md` (use Date field instead)
- Use special characters: `calibration@procedure.md`
- Use hyphens for multi-word names: prefer `sky_map.md` over `sky-map.md`

### Examples

✅ **Good:**

- `debugging_guide.md`
- `test_strategy.md`
- `node_version_requirement.md`

❌ **Bad:**

- `DEBUGGING_GUIDE.md` (UPPERCASE)
- `test-strategy.md` (hyphens)
- `test strategy.md` (spaces)
- `2025-11-16_status.md` (date in filename)

---

## 📋 Document Structure Templates

### Template 1: Simple Markdown (Default)

**Use for:** Most documentation, especially implementation guides, debugging
guides, and tutorials

```markdown
# Document Title

**Date:** YYYY-MM-DD  
**Type:** [Implementation Guide | Troubleshooting | Analysis | Status Report |
Reference]  
**Status:** [✅ Current | ✅ Complete | 🔄 In Progress | 📋 Planned]  
**Related:** [Optional: Links to related documents or features]

---

## Overview

Brief description of what this document covers (2-3 sentences).

## Main Content

### Section 1

Content here.

### Section 2

Content here.

## References

- Link to related documentation
- Link to code files
- External resources

---

**Last Updated:** YYYY-MM-DD  
**Maintained By:** [Optional: Agent/Person responsible]
```

### Template 2: YAML Frontmatter (For Structured Docs)

**Use for:** Status reports, analysis reports, detailed implementation summaries

**Why:** Makes it easier for AI agents to parse, filter, and search
documentation.

```markdown
---
date: YYYY-MM-DD
title: Document Title
type: [implementation-guide|troubleshooting|analysis|status-report|reference]
status: [current|complete|in-progress|planned]
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

- [Related Document 1](./path/to/doc1.md)
- [Related Document 2](./path/to/doc2.md)
```

**When to use frontmatter:**

- ✅ Status reports
- ✅ Analysis reports
- ✅ Detailed implementation summaries
- ✅ Architecture decisions

**When to use simple format:**

- ✅ Basic how-to guides
- ✅ Quick reference snippets
- ✅ Debugging guides
- ✅ Implementation step-by-steps

---

## 🎯 Document Type Guidelines

### Implementation Guide

**Use When:** Documenting step-by-step feature implementation

**Required Sections:**

- Overview
- Prerequisites
- Implementation Steps
- Testing
- References

**Template:** See
AGENT_GUIDELINES.md

### Troubleshooting Guide

**Use When:** Documenting issue resolution or debugging steps

**Required Sections:**

- Issue Description
- Root Cause
- Solution
- Prevention
- Related Issues

**Template:** See
AGENT_GUIDELINES.md

### Analysis Document

**Use When:** Research findings, architectural decisions, or feature analysis

**Required Sections:**

- Summary
- Findings
- Recommendations
- Alternatives Considered
- References

**Template:** See
AGENT_GUIDELINES.md

### Status Report

**Use When:** Progress updates, audit results, or completion summaries

**Required Sections:**

- Overview
- Status Summary
- Details
- Next Steps (if applicable)
- Statistics

**Template:** See
AGENT_GUIDELINES.md

---

## 🔄 Adding New Documentation

### Step-by-Step Process

1. **Determine Category**
   - Check INDEX.md for appropriate category
   - Choose document type (Implementation, Troubleshooting, etc.)

2. **Create Document**
   - Use appropriate template from AGENT_GUIDELINES.md
   - Name file descriptively using lowercase with underscores
   - Place in `docs/` or `docs/analysis/` as appropriate

3. **Write Content**
   - Follow template structure
   - Include all required sections for document type
   - Add code examples, links, references
   - Keep lines to 80 characters (Prettier will wrap)

4. **Format with Prettier**

   ```bash
   # Format the new document
   npx prettier --write "docs/YOUR_DOCUMENT.md"
   ```

5. **Update INDEX.md**
   - Add entry to appropriate category section
   - Include Date, Description, and Status
   - Link to the document using relative path

6. **Verify**
   - Check links work
   - Verify date format: `YYYY-MM-DD`
   - Confirm status is accurate
   - Ensure document is in correct location
   - Run Prettier to verify formatting

---

## 🔧 Formatting with Prettier

### Manual Formatting

```bash
# Format all markdown files in docs/
cd frontend
npx prettier --write "docs/**/*.md"

# Format a specific file
npx prettier --write "docs/YOUR_DOCUMENT.md"

# Check formatting without changing files
npx prettier --check "docs/**/*.md"
```

### Pre-commit Hook

Prettier automatically formats markdown files on commit. If formatting fails:

```bash
# Fix formatting
npx prettier --write "docs/**/*.md"

# Re-stage files
git add docs/**/*.md
```

### CI/CD Validation

The `.github/workflows/prettier-check.yml` workflow validates formatting in pull
requests. If CI fails:

1. Format files locally: `npx prettier --write "docs/**/*.md"`
2. Commit the formatted files
3. Push to trigger re-check

---

## ✅ Quality Checklist

Before finalizing a document, verify:

- [ ] Standard header format used (Date, Type, Status)
- [ ] All required sections for document type included
- [ ] Links are working (relative paths correct)
- [ ] Code examples are accurate and tested
- [ ] Document is added to INDEX.md
- [ ] Status is accurate
- [ ] Date is current (YYYY-MM-DD format)
- [ ] Content is clear and complete
- [ ] References are included
- [ ] Last Updated date is set
- [ ] **Prettier formatting applied (80 char line width)**
- [ ] **File naming follows conventions (lowercase_with_underscores)**

---

## 📊 Status Values

### When to Use Each Status

- **✅ Current:** Document is actively maintained and accurate
  - Use for: Living documentation, actively used guides
  - Update regularly to keep date recent

- **✅ Complete:** Work is finished, document is final
  - Use for: Completed implementations, resolved issues
  - No further updates expected

- **🔄 In Progress:** Work is ongoing
  - Use for: Features under development, ongoing analysis
  - Update regularly as work progresses

- **📋 Planned:** Documented but not yet implemented
  - Use for: Planned features, future work
  - Update when work begins (→ In Progress)

- **⚠️ Deprecated:** Documented approach is outdated
  - Use for: Old approaches being replaced
  - Should link to replacement document

---

## 🔗 Linking Best Practices

### Internal Links

```markdown
# Relative paths within docs/

[Link Text](./FILENAME.md) [Link Text](./analysis/FILENAME.md)

# Links to INDEX.md categories

See [Implementation Guides](./INDEX.md#2-implementation-guides)

# Links to specific sections

See [Testing Documentation](./INDEX.md#3-testing-documentation)
```

### Code References

```markdown
# File references (use code reference format)

See `src/components/ComponentName.tsx`

# Function/class references

See `useHookName()` in `src/hooks/`

# Full paths for clarity

Implementation: `src/components/Feature/FeatureComponent.tsx`
```

### External Links

```markdown
# Documentation

[React Docs](https://react.dev)

# GitHub issues/PRs

[Issue #123](https://github.com/...)
```

---

## 📚 Quick Reference

### File Naming Convention

```
lowercase_with_underscores.md
Examples:
- sky_map_implementation.md
- node_version_requirement.md
- health_check_fix.md
- testing_strategy.md
```

### Directory Structure

```
frontend/docs/
├── INDEX.md                    # Master index (always update)
├── AGENT_GUIDELINES.md         # Templates and guidelines
├── DOCUMENTATION_QUICK_REFERENCE.md  # This file
├── README.md                   # Main project README
├── *.md                        # Category documents
└── analysis/
    └── *.md                    # Analysis documents
```

### Update INDEX.md Format

```markdown
| [Document Name](./FILENAME.md) | YYYY-MM-DD | Brief description | ✅ Current |
```

---

## 🚀 Quick Start for AI Agents

### Creating New Documentation (6 Steps)

1. **Choose template** from AGENT_GUIDELINES.md based
   on document type
2. **Create file** with descriptive name (lowercase_with_underscores.md)
3. **Fill template** with content (keep to 80 char lines)
4. **Format with Prettier**: `npx prettier --write "docs/YOUR_DOC.md"`
5. **Add to INDEX.md** in appropriate category
6. **Verify** checklist items

### Updating Existing Documentation (4 Steps)

1. **Update content** and date if significant
2. **Update status** if changed
3. **Format with Prettier**: `npx prettier --write "docs/YOUR_DOC.md"`
4. **Update INDEX.md** entry if needed

---

## 📝 Summary

- **Framework:** Prettier (not markdownlint)
- **Line width:** 80 characters for markdown
- **Auto-formatting:** Enabled via pre-commit hooks
- **CI validation:** Checks formatting in pull requests
- **Style guide:** Templates in AGENT_GUIDELINES.md
- **File naming:** lowercase_with_underscores.md
- **Master index:** INDEX.md

Prettier enforces consistent markdown formatting across the documentation.

---

## ❓ Questions or Issues?

- Check INDEX.md for document location
- Review AGENT_GUIDELINES.md for templates
- Review existing documents for format examples
- Follow templates in this guide
- Maintain consistency with existing documentation

---

**Last Updated:** 2025-11-16  
**Status:** ✅ Current  
**For:** AI Agents and Contributors
