# DSA-110 Directory Reorganization Proposal

**Date:** November 26, 2025  
**Goal:** Simplify `/data/dsa110-contimg/` for frontend dashboard and pipeline development

---

## Executive Summary

The current directory contains **scattered state/logs directories**, **fragmented AI tool configs**, **documentation sprawl**, and **orphaned root files**. This proposal consolidates these into a cleaner structure while preserving all content.

---

## Proposed Changes

### 1. Consolidate AI Agent Configurations → `.ai/`

**Current State:**
- `.cursor/` - Cursor rules and commands
- `.github/copilot-instructions.md` - GitHub Copilot
- `.github/chatmodes/` - GitHub chat modes  
- `.github/instructions/` - More instructions
- `.serena/` - Serena AI memories
- `.codex/` - Codex config
- `.gemini/` - Gemini config

**Proposed:**
```
.ai/
├── cursor/          # Move from .cursor/
├── copilot/         # Move .github/copilot-instructions.md, chatmodes/, instructions/
├── serena/          # Move from .serena/
├── codex/           # Move from .codex/
└── gemini/          # Move from .gemini/
```

> **Note:** Keep `.github/copilot-instructions.md` as a symlink for VS Code compatibility.

---

### 2. Consolidate Documentation → `docs/`

**Current Issues:**
- `docs/dev-notes/` and `docs/development/` have overlapping purposes
- `docs/logs/` contains dev progress logs (not runtime logs)
- `docs/archive/analysis/` is a 32 KB nested duplicate
- Excessive subdirectory depth

**Proposed Structure:**
```
docs/
├── README.md
├── SYSTEM_CONTEXT.md
├── CODE_MAP.md
├── architecture/         # From concepts/
├── guides/               # Merge: how-to/ + tutorials/
│   ├── getting-started/
│   ├── dashboard/
│   ├── data-processing/
│   ├── workflow/
│   └── operations/
├── reference/            # API and CLI docs (keep as-is)
├── design/               # Keep as-is
├── operations/           # Keep as-is
├── testing/              # Keep as-is
├── troubleshooting/      # Keep as-is
├── changelog/            # Keep as-is
├── archive/              # Historical docs (keep but consolidate)
│   ├── 2025-01/
│   ├── analysis/
│   └── progress-logs/    # Move from docs/logs/
├── simulations/          # Keep as-is
├── notebooks/            # Keep as-is
└── examples/             # Keep as-is
```

**Removals (merge into parent):**
- `docs/dev-notes/` → merge into `docs/guides/development/`
- `docs/development/` → merge into `docs/guides/development/`
- `docs/indices/` → if empty, remove
- `docs/javascripts/` → if only for mkdocs, note in README
- `docs/contributing/` → merge into `docs/guides/development/`
- `docs/implementation/` → merge into `docs/architecture/`
- `docs/known-issues/` → merge into `docs/troubleshooting/`
- `docs/concepts/` → rename to `docs/architecture/`

---

### 3. Clean Up Scattered State Directories

**Current State:**
- `/state/` (6.8 GB) - Main runtime state ✅ Keep
- `backend/state/` - Should not exist separately
- `frontend/state/` - Pointing data, specific use case
- `docs/state/` - Docs about state management
- `.local/state_src_orphaned/` - Already marked orphaned

**Proposed:**
- Keep `/state/` as the canonical runtime state location
- `frontend/state/pointing/` → Move to `/state/frontend/pointing/` OR keep in frontend if frontend-specific
- `backend/state/` → Merge into `/state/` or remove if empty
- `docs/state/` → Rename to `docs/reference/state-management/`
- `.local/state_src_orphaned/` → Keep in `.local/archive/` for reference

---

### 4. Clean Up Scattered Logs

**Current:**
- `/logs/` - Runtime logs (keep)
- `/state/logs/` - Pipeline execution logs (keep, symlink from /logs?)
- `/docs/logs/` - Development progress logs (NOT runtime logs)
- `.local/logs/` - Archive logs
- `.codacy/logs/` - Codacy-specific

**Proposed:**
- Keep `/logs/` for runtime
- Keep `/state/logs/` for pipeline logs (or symlink)
- `docs/logs/` → Move to `docs/archive/progress-logs/`
- `.local/logs/` → Keep in `.local/archive/`

---

### 5. Consolidate Root-Level Items

**Remove/Relocate:**
- `package.json` + `node_modules/` at root - Move to `.local/archive/` if truly unused
- `.gitlab-ci.yml.e2e` - Move to `.local/archive/` if legacy
- `.output-suppression-whitelist` - Move to `ops/config/`

**Keep at Root:**
- `README.md` ✅
- `Makefile` ✅
- `docker-compose.yml` ✅
- `mkdocs.yml` ✅
- Config files (`.pre-commit-config.yaml`, `.editorconfig`, etc.) ✅

---

### 6. Consolidate External Dependencies → `external/` or `vendor/`

**Current:**
- `external/` - aocommon, everybeam
- `bindings/` - everybeam_py

**Proposed:**
```
vendor/
├── aocommon/           # From external/
├── everybeam/          # From external/
└── everybeam_py/       # From bindings/
```

---

### 7. Simplify `.local/` Structure

**Current:**
- `.local/archive/` - Legacy code, references, scripts
- `.local/artifacts/` - Generated artifacts
- `.local/bin/` - Local binaries
- `.local/internal/` - Internal tools
- `.local/logs/` - Archive logs
- `.local/state_src_orphaned/` - Orphaned state

**Proposed (keep as-is, just document):**
```
.local/
├── archive/            # Historical reference code (gitignored)
├── artifacts/          # Generated QA outputs
├── bin/               # Local binaries
└── internal/          # Internal development tools
```

---

## Summary of Moves

| Current Location | New Location | Notes |
|-----------------|--------------|-------|
| `.cursor/` | `.ai/cursor/` | Consolidate AI tools |
| `.codex/` | `.ai/codex/` | Consolidate AI tools |
| `.gemini/` | `.ai/gemini/` | Consolidate AI tools |
| `.serena/` | `.ai/serena/` | Consolidate AI tools |
| `.github/chatmodes/` | `.ai/copilot/chatmodes/` | Keep `.github/copilot-instructions.md` symlink |
| `.github/instructions/` | `.ai/copilot/instructions/` | |
| `docs/concepts/` | `docs/architecture/` | Rename for clarity |
| `docs/how-to/` + `docs/tutorials/` | `docs/guides/` | Merge similar |
| `docs/logs/` | `docs/archive/progress-logs/` | These are dev logs, not runtime |
| `docs/dev-notes/` + `docs/development/` | `docs/guides/development/` | Merge duplicates |
| `docs/implementation/` | `docs/architecture/implementation/` | Consolidate |
| `docs/contributing/` | `docs/guides/contributing/` | |
| `docs/known-issues/` | `docs/troubleshooting/known-issues/` | |
| `external/` + `bindings/` | `vendor/` | Consolidate external deps |
| Root `package.json` + `node_modules/` | `.local/archive/root-npm/` | If unused |

---

## Empty Directories to Remove

Based on `find -type d -empty`:
```
.local/archive/codeql/*/strings
.local/archive/legacy/*/logs/casa
.local/archive/legacy/*/tests/fixtures/sample_ms
.local/artifacts/*/alerts
.local/artifacts/*/archive
.local/artifacts/*/current
products/caltables/
products/catalogs/
products/images/
products/metadata/
products/mosaics/
products/ms/
products/qa/
```

---

## Implementation Priority

1. **High Priority (Immediate clarity):**
   - Consolidate AI configs → `.ai/`
   - Rename `docs/concepts/` → `docs/architecture/`
   - Merge `docs/logs/` → `docs/archive/progress-logs/`

2. **Medium Priority (Reduce confusion):**
   - Merge `docs/how-to/` + `docs/tutorials/` → `docs/guides/`
   - Consolidate `external/` + `bindings/` → `vendor/`
   - Clean up root npm files

3. **Low Priority (Nice to have):**
   - Remove empty directories
   - Deep documentation consolidation

---

## Risks & Mitigations

1. **Broken Imports/Paths:**
   - Run grep for hardcoded paths before moving
   - Update `.github/copilot-instructions.md` after moves
   - Create symlinks for frequently-referenced paths

2. **Git History:**
   - Use `git mv` to preserve history
   - Make changes in a single commit per category

3. **CI/CD Breakage:**
   - Check `.github/workflows/` for path dependencies
   - Update `mkdocs.yml` nav after docs moves

---

## Next Steps

1. Review this proposal
2. Decide on priority levels
3. Run the reorganization script (creates backup first)
4. Update documentation references
5. Verify CI/CD still works
