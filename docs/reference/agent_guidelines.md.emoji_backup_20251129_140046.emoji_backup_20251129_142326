# Documentation Guidelines for AI Agents

**Date:** 2025-11-16  
**Purpose:** Standardized guidelines and templates for AI agents to create,
update, and maintain documentation  
**Status:** ✅ Current

---

## 🎯 Purpose

This document provides AI agents with standardized templates, formats, and
guidelines for creating and maintaining documentation in a consistent,
searchable, and maintainable format.

**For formatting rules, see:** [DOCUMENTATION_QUICK_REFERENCE.md]()

---

## 📋 Standard Document Template

### Basic Template

```markdown
# Document Title

**Date:** YYYY-MM-DD **Type:** [Implementation Guide | Troubleshooting |
Analysis | Status Report | Reference] **Status:** [✅ Current | ✅ Complete | 🔄
In Progress | 📋 Planned] **Related:** [Optional: Links to related documents or
features]

---

## Overview

Brief description of what this document covers (2-3 sentences).

## Main Content Sections

### Section 1

Content here...

### Section 2

Content here...

## References

- Link to related documentation
- Link to code files
- External resources

---

**Last Updated:** YYYY-MM-DD **Maintained By:** [Optional: Agent/Person
responsible]
```

---

## 📝 Document Type Guidelines

### 1. Implementation Guide

**Use When:** Documenting step-by-step feature implementation

**Required Sections:**

- Overview
- Prerequisites
- Implementation Steps
- Testing
- References

**Example:**

```markdown
# Feature Implementation: [Feature Name]

**Date:** 2025-11-16 **Type:** Implementation Guide **Status:** ✅ Complete
**Related:** [Component Name] | [API Endpoint]

## Overview

Brief description of what was implemented...

## Prerequisites

- Requirements
- Dependencies
- Setup needed

## Implementation Steps

### Step 1: [Action]

Description...

### Step 2: [Action]

Description...

## Testing

How to test the implementation...

## References

- Related components: `frontend/src/components/<ComponentName>``
- Related hooks: `frontend/src/hooks/<hookName>``
- Related documentation: [Document Link]
```

---

### 2. Troubleshooting Guide

**Use When:** Documenting issue resolution or debugging steps

**Required Sections:**

- Issue Description
- Root Cause
- Solution
- Prevention
- Related Issues

**Example:**

```markdown
# Issue: [Issue Name]

**Date:** 2025-11-16 **Type:** Troubleshooting **Status:** ✅ Complete
**Related:** [Related Component] | [Related Issue]

## Issue Description

What was the problem? Error messages, symptoms...

## Root Cause

Why did this happen? Technical explanation...

## Solution

Step-by-step fix...

## Prevention

How to avoid this in the future...

## Related Issues

Links to similar issues or related documentation...
```

---

### 3. Analysis Document

**Use When:** Research findings, architectural decisions, or feature analysis

**Required Sections:**

- Summary
- Findings
- Recommendations
- Alternatives Considered
- References

**Example:**

```markdown
# Analysis: [Topic]

**Date:** 2025-11-16 **Type:** Analysis **Status:** ✅ Complete

## Summary

Executive summary (2-3 sentences)...

## Findings

### Finding 1

Details...

### Finding 2

Details...

## Recommendations

What should be done based on findings...

## Alternatives Considered

Other options explored...

## References

- Code references
- External resources
- Related documentation
```

---

### 4. Status Report

**Use When:** Progress updates, audit results, or completion summaries

**Required Sections:**

- Overview
- Status Summary
- Details
- Next Steps (if applicable)
- Statistics

**Example:**

```markdown
# Status Report: [Topic]

**Date:** 2025-11-16 **Type:** Status Report **Status:** ✅ Complete

## Overview

What this report covers...

## Status Summary

- ✅ Completed items
- 🔄 In progress items
- 📋 Planned items

## Details

Detailed breakdown...

## Next Steps

What comes next (if applicable)...

## Statistics

Quantitative summary...
```

---

## 🔄 Updating Documentation

### When to Update a Document

1. **Significant Changes**: Add new sections, change approach
2. **Status Changes**: Feature complete, status update
3. **Accuracy Fixes**: Correct outdated information
4. **Regular Maintenance**: Quarterly review recommended

### Update Process

1. **Update Content**: Make necessary changes
2. **Update Date**: Change `**Date:**` field if significant
3. **Update Status**: Change if needed (Current → Complete, etc.)
4. **Update INDEX.md**: Update entry in INDEX.md
5. **Update Last Updated**: At end of document

### Example Update

```markdown
# Existing Document

**Date:** 2025-11-14 ← Update if significant changes **Status:** 🔄 In Progress
← Change to ✅ Complete when done

[Content updates here...]

---

**Last Updated:** 2025-11-16 ← Always update this
```

---

## 📂 Adding New Documentation

### Step-by-Step Process

1. **Determine Category**
   - Check INDEX.md for appropriate category
   - Choose document type (Implementation, Troubleshooting, etc.)

2. **Create Document**
   - Use appropriate template from this guide
   - Name file descriptively: `FEATURE_NAME_TYPE.md` (e.g.,
     `SKYMAP_IMPLEMENTATION.md`)

3. **Write Content**
   - Follow template structure
   - Include all required sections for document type
   - Add code examples, links, references

4. **Update INDEX.md**
   - Add entry to appropriate category table
   - Include: Date, Description, Status
   - Link using relative path: `[Document Name](./FILENAME.md)`

5. **Verify**
   - Check links work
   - Verify date format: `YYYY-MM-DD`
   - Confirm status is accurate
   - Ensure document is in correct location

### Example: Adding New Implementation Guide

```bash
# 1. Create document
touch docs/NEW_FEATURE_IMPLEMENTATION.md

# 2. Write content using Implementation Guide template

# 3. Update INDEX.md - add to "Implementation Guides" section:

| [NEW_FEATURE_IMPLEMENTATION.md](./NEW_FEATURE_IMPLEMENTATION.md) | 2025-11-16 | New feature implementation details | ✅ Complete |

# 4. Update INDEX.md Last Updated date
```

---

## 🏷️ Status Values

### When to Use Each Status

- **✅ Current**: Document is actively maintained and accurate
  - Use for: Living documentation, actively used guides
  - Update regularly to keep date recent

- **✅ Complete**: Work is finished, document is final
  - Use for: Completed implementations, resolved issues
  - No further updates expected

- **🔄 In Progress**: Work is ongoing
  - Use for: Features under development, ongoing analysis
  - Update regularly as work progresses

- **📋 Planned**: Documented but not yet implemented
  - Use for: Planned features, future work
  - Update when work begins (→ In Progress)

- **⚠️ Deprecated**: Documented approach is outdated
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

See `frontend/src/components/<ComponentName>.tsx`

# Function/class references

See `useHookName()` in `frontend/src/hooks/`

# Full paths for clarity

Implementation: `frontend/src/components/<Feature>/<FeatureComponent>.tsx`
```

### External Links

```markdown
# Documentation

[React Docs](https://react.dev)

# GitHub issues/PRs

[Issue #123](https://github.com/...)
```

---

## 📊 Metadata Standards

### Required Metadata

Every document must have:

- **Date:** YYYY-MM-DD format
- **Type:** One of: Implementation Guide | Troubleshooting | Analysis | Status
  Report | Reference
- **Status:** One of: ✅ Current | ✅ Complete | 🔄 In Progress | 📋 Planned

### Optional Metadata

- **Related:** Links to related documents or features
- **Last Updated:** At end of document (update on changes)
- **Maintained By:** Agent/person responsible

### Metadata Format

```markdown
**Date:** 2025-11-16 **Type:** Implementation Guide **Status:** ✅ Complete
**Related:** [Component Name] | [Feature Name]
```

---

## 🔍 Search Optimization

### For AI Agents to Find Documents Easily

1. **Use Descriptive Titles**: Clear, specific titles
2. **Include Keywords**: Use terms that will be searched
3. **Add to INDEX.md**: All documents should be indexed
4. **Cross-Reference**: Link related documents
5. **Tag Content**: Use consistent terminology

### Example: Well-Optimized Document

```markdown
# Feature Implementation: Interactive Sky Map Component

**Date:** 2025-11-16 **Type:** Implementation Guide **Status:** ✅ Complete
**Related:** SkyView | SkyMap | SKYMAP_IMPLEMENTATION.md

## Overview

Implementation of interactive sky map using CARTA integration...

[Keywords: sky map, CARTA, interactive, visualization, implementation]
```

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

---

## 📚 Quick Reference

### File Naming Convention

**Format:** `lowercase_with_underscores.md`

**Examples:**

- `sky_map_implementation.md`
- `node_version_requirement.md`
- `health_check_fix.md`
- `testing_strategy.md`

**See:** [DOCUMENTATION_QUICK_REFERENCE.md]() for full naming rules

### Directory Structure

```
docs/
├── INDEX.md                    # Master index (always update)
├── AGENT_GUIDELINES.md         # This file
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

### Creating New Documentation (5 Steps)

1. **Choose template** from this guide based on document type
2. **Create file** with descriptive name
3. **Fill template** with content
4. **Add to INDEX.md** in appropriate category
5. **Verify** checklist items

### Updating Existing Documentation (3 Steps)

1. **Update content** and date if significant
2. **Update status** if changed
3. **Update INDEX.md** entry if needed

---

## 📞 Questions or Issues?

- Check INDEX.md for document location
- Review existing documents for format examples
- Follow templates in this guide
- Maintain consistency with existing documentation

---

**Last Updated:** 2025-11-16  
**Status:** ✅ Current  
**For:** AI Agents and Contributors
