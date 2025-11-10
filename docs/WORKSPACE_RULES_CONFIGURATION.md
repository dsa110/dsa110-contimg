# Workspace Rules Configuration

**Purpose:** Document what should be included in the "Always Applied Workspace Rules" section

**Last Updated:** 2025-01-XX

---

## Current Always Applied Workspace Rules

The workspace configuration should include:

1. **Internal Maintenance Rules** - Already included ✅
2. **MCP Core Rules** - Already included ✅
3. **Python Environment Requirements (casa6)** - Already included ✅
4. **Critical Instructions (MEMORY.md editing)** - Already included ✅

---

## Required Additions

### 1. Python Environment: casa6 Requirement

**Status:** Already in workspace rules as `PYTHON_ENVIRONMENT_REQUIREMENT` ✅

**Content:** The existing rule covers:
- Path: `/opt/miniforge/envs/casa6/bin/python`
- Python version: 3.11.13 (in `casa6` conda environment)
- Usage in Makefiles, shell scripts, and Python code
- Why it's critical (CASA dependencies, Python features)

**Reference:** `.cursor/rules/critical-requirements.mdc` (comprehensive version)

---

### 2. Organizational Layout Reference

**Status:** Needs to be added to workspace rules ⚠️

**Content to Add:**

```
## Codebase and Documentation Organizational Layout

**CRITICAL:** Before creating files or making changes, understand the organizational structure.

**Reference Document:** `docs/concepts/DIRECTORY_ARCHITECTURE.md`

This document describes:
- Directory structure for code, data, and documentation
- Naming conventions
- Data retention policies
- Storage organization (`/data/` vs `/scratch/`)
- Database locations
- File organization patterns

**Key Principles:**
- Code in `/data/dsa110-contimg/`
- Data in `/stage/dsa110-contimg/`
- Documentation in `docs/` structure (see documentation-location.mdc)
- State databases in `/data/dsa110-contimg/state/`
- Temporary staging in `/dev/shm/` (tmpfs)

**Before creating files:**
1. Check `docs/concepts/DIRECTORY_ARCHITECTURE.md` for organizational structure
2. Check `docs/DOCUMENTATION_QUICK_REFERENCE.md` for documentation location rules
3. Follow established naming conventions and directory patterns
```

**Reference:** `.cursor/rules/critical-requirements.mdc` (Section: "Codebase and Documentation Organizational Layout")

---

## Implementation

### Option 1: Add to Workspace Configuration (Recommended)

Add the organizational layout section to the workspace's "Always Applied Workspace Rules" configuration in Cursor settings.

### Option 2: Reference Rule File

The workspace configuration can reference `.cursor/rules/critical-requirements.mdc` which contains both requirements in a single file.

### Option 3: Agent Requestable Rule

Add `.cursor/rules/critical-requirements.mdc` to the `<agent_requestable_workspace_rules>` section so agents can explicitly request it.

---

## Verification

After adding to workspace configuration, verify:

1. ✅ Agents see casa6 requirement immediately
2. ✅ Agents see organizational layout reference immediately
3. ✅ Both requirements are in the `<always_applied_workspace_rules>` section

---

## Related Files

- `.cursor/rules/critical-requirements.mdc` - Comprehensive rule file with both requirements
- `docs/concepts/DIRECTORY_ARCHITECTURE.md` - Organizational layout document
- `docs/reference/CRITICAL_PYTHON_ENVIRONMENT.md` - Detailed casa6 requirements

---

**Note:** The `.cursor/rules/critical-requirements.mdc` file has been created and contains both requirements. This file can be referenced by the workspace configuration or explicitly requested by agents.
