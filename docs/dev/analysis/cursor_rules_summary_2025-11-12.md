# Cursor Rules Summary
**Date:** 2025-11-12  
**Purpose:** Comprehensive catalog of all Cursor rules in `.cursor/rules/`

---

## Overview

**Total Rules:** 15 files (including Graphiti subdirectory)  
**Always Apply:** 8 rules  
**Conditional Apply:** 7 rules  
**Duplicate:** 1 file (`data-provenance-verification.md` vs `.mdc`)

---

## Main Rules Directory

### 1. `codacy.mdc` (4.5KB, 81 lines)
**Type:** Conditional (`alwaysApply: false`)  
**Purpose:** Codacy code quality and security analysis integration

**Key Requirements:**
- Run `codacy_cli_analyze` after ANY file edit
- Use provider: `gh`, organization: `dsa110`, repository: `dsa110-contimg`
- Run Trivy security checks after dependency changes
- Handle 404 errors by offering repository setup

**Critical Actions:**
- IMMEDIATELY analyze edited files
- Propose fixes for any issues found
- Never wait for user to ask for analysis

---

### 2. `coding-best-practices.mdc` (6.7KB, 293 lines)
**Type:** Conditional (`alwaysApply: false`)  
**Purpose:** Common pitfalls to avoid when writing code

**8 Key Areas:**
1. **API Signature Mismatches** - Always inspect signatures first
2. **Environment Variables** - Variables in `.bashrc` not auto-exported
3. **Async/Await Handling** - Check if function is async before calling
4. **Type Mismatches** - Use enums not strings, verify types
5. **Syntax Errors** - Avoid backslashes in f-strings
6. **Missing Dependencies** - Verify imports work, check Python environment
7. **Configuration Mismatches** - Verify dimensions, group IDs, API keys
8. **Documentation Gaps** - Inspect actual code/signatures

**Workflow:** Inspect → Verify → Check → Test → Read errors

---

### 3. `output-suppression.mdc` (3.2KB, 81 lines)
**Type:** Always Apply (`alwaysApply: true`)  
**Purpose:** NEVER suppress command output

**7 Rules:**
1. Never use `2>/dev/null`, `>/dev/null`, `&>/dev/null`
2. Never filter output with `grep -v` unless requested
3. Never truncate with `head`/`tail` unless requested
4. Preserve all output streams (stdout and stderr)
5. ALWAYS use unbuffered output (`stdbuf -oL -eL`, `python -u`)
6. ALWAYS log simultaneously (`tee`)
7. Preserve full complexity (no simplification)

**Rationale:** Users need complete information to diagnose issues

---

### 4. `frontend-focus.mdc` (831B, 31 lines)
**Type:** Always Apply (`alwaysApply: true`)  
**Purpose:** Frontend development guidelines

**Key Rules:**
- Frontend code: `frontend/src/`
- Backend is READ-ONLY (reference only)
- Tests: `frontend/src/**/__tests__/`
- DO reference backend for API contracts
- DON'T modify backend when working on frontend
- DO generate TypeScript types from Python schemas

---

### 5. `radio-conventions.mdc` (733B, 34 lines)
**Type:** Conditional (`alwaysApply: false`)  
**Purpose:** Radio astronomy calculations and conventions

**Key Rules:**
- **MJD Calculations:** NEVER create custom conversion, use existing utilities
- **Calibration Types:** Valid CASA types only (K, BA, BP, GA, GP, 2G)
- **Source Naming:** NVSS convention `NVSS Jhhmmss.s+ddmmss`
- DON'T create fake source IDs for examples

---

### 6. `dashboard-existing-architecture.mdc` (2.7KB, 72 lines)
**Type:** Always Apply (`alwaysApply: true`)  
**Purpose:** DSA-110 Dashboard architecture constraints

**CRITICAL:** This is an EXISTING codebase
- React 18 + TypeScript + Material-UI v6 (DO NOT CHANGE)
- DO NOT suggest Blueprint UI, Plotly, or other libraries
- DO NOT redesign architecture
- CHECK package.json before suggesting dependencies

**Tech Stack:**
- React 18 (functional components + hooks)
- TypeScript (strict mode)
- Material-UI v6
- React Router v6
- React Query
- Axios
- WebSocket client

**Existing Pages:**
- ✅ Dashboard, Control, Streaming, QA, Data Browser (fully implemented)
- 🔄 Sky View, Sources (partial)
- 📋 Observing, Health (not implemented)

**Database Tables:** Already exist in SQLite (DO NOT create schemas)

---

### 7. `documentation-location.mdc` (2.5KB, 97 lines)
**Type:** Always Apply (`alwaysApply: true`)  
**Purpose:** Where to put documentation files

**Decision Tree:**
- End users → `docs/how-to/`, `docs/concepts/`, `docs/reference/`, `docs/tutorials/`
- Status updates → `internal/docs/dev/status/YYYY-MM/`
- Investigations → `internal/docs/dev/analysis/`
- Agent notes → `internal/docs/dev/notes/`
- Historical → `docs/archive/`

**File Naming:** ALWAYS lowercase with underscores

**Enforcement:**
- Move root files immediately to `docs/`
- Use migration script: `scripts/migrate_docs.sh`

---

### 8. `data-provenance-verification.mdc` (3.3KB, 85 lines)
**Type:** Always Apply (`alwaysApply: true`)  
**Purpose:** Verify data source before making claims

**CRITICAL:** Never assume test/synthetic data is real observational data

**Verification Checklist:**
1. **File Location:** Check full path (not just filename)
2. **FITS Header Metadata:** Must have `DATE-OBS` or `DATE` field
3. **File Naming:** `test_*` files are TEST DATA
4. **Code Context:** Check if generated by test code

**When in Doubt:**
- ASK explicitly
- VERIFY location, metadata, generation code
- QUALIFY with "appears to be", "likely", "verified as"
- DOCUMENT in comments/tests

**Note:** Duplicate file exists (`data-provenance-verification.md`) - should be consolidated

---

### 9. `critical-requirements.mdc` (1.6KB, 42 lines)
**Type:** Always Apply (`alwaysApply: true`)  
**Purpose:** Codebase and documentation organizational layout

**CRITICAL:** Before creating files, check `docs/concepts/DIRECTORY_ARCHITECTURE.md`

**Key Principles:**
- Code: `/data/dsa110-contimg/`
- Data: `/stage/dsa110-contimg/` (SSD) or `/data/` (HDD)
- Docs: `/data/dsa110-contimg/docs/` structure
- State DBs: `/data/dsa110-contimg/state/`
- Temp staging: `/dev/shm/` (tmpfs)

**Before creating files:**
1. Check `DIRECTORY_ARCHITECTURE.md`
2. Check `DOCUMENTATION_QUICK_REFERENCE.md`
3. Follow naming conventions

---

### 10. `critical-requirements-short.mdc` (596B, 19 lines)
**Type:** Always Apply (`alwaysApply: true`)  
**Purpose:** Quick reference for codebase organization

**Key Paths:**
- Root: `/data/dsa110-contimg/`
- Data: `/stage/dsa110-contimg/`
- Docs: `/data/dsa110-contimg/docs/`
- State DBs: `/data/dsa110-contimg/state/`

**Details:** See `docs/concepts/DIRECTORY_ARCHITECTURE.md`  
**Full details:** `.cursor/rules/critical-requirements.mdc`

---

### 11. `codex.mdc` (20KB, 225 lines)
**Type:** Conditional (`alwaysApply: false`)  
**Purpose:** Codex execution plans (ExecPlans) for multi-hour problem solving

**Key Concepts:**
- ExecPlans are self-contained, living documents
- Must enable complete novice to implement end-to-end
- Must produce demonstrably working behavior
- Must define every term of art in plain language

**Required Sections:**
- Purpose / Big Picture
- Progress (with checkboxes and timestamps)
- Surprises & Discoveries
- Decision Log
- Outcomes & Retrospective
- Context and Orientation
- Plan of Work
- Concrete Steps
- Validation and Acceptance
- Idempotence and Recovery
- Artifacts and Notes
- Interfaces and Dependencies

**Codex CLI:** Documents commands, arguments, and options

---

### 12. `data-provenance-verification.md` (3.3KB, 82 lines)
**Type:** Duplicate  
**Purpose:** Same as `.mdc` version

**Note:** This appears to be a duplicate of `data-provenance-verification.mdc`. Should be removed or consolidated.

---

### 13. `dsa110-agent-workflow.mdc` (2.4KB, 32 lines)
**Type:** Always Apply (`alwaysApply: true`)  
**Purpose:** Combined-Memory Learning Loop workflow

**Mandatory 3-Step Workflow:**

**Step A: Knowledge Retrieval (Consult the Graph)**
1. Query Graphiti first (`search_memory_facts` or `search_nodes`)
2. Formulate relevant query
3. Incorporate findings into plan

**Step B: Analysis and Development (Use the Tools)**
1. Utilize Serena and other tools
2. Execute the task

**Step C: Knowledge Synthesis and Ingestion (Feed the Graph)**
1. Summarize new knowledge
2. Structure as JSON payload
3. Ingest into Graphiti (`add_memory` with `source='json'`)
4. Verify ingestion (optional)

**Rationale:** Ensures continuous learning and knowledge retention

---

## Graphiti Subdirectory Rules

### 14. `graphiti/graphiti-dsa110-contimg-schema.mdc` (14KB, 262 lines)
**Type:** Conditional (`alwaysApply: false`)  
**Purpose:** Project-specific knowledge graph schema

**Defined Entities:**
- Project, Module, File, FileType, Documentation, Script
- DataSample, Configuration, Test
- Dataset, Run, Artifact
- Paper, Procedure, Preference

**Defined Relationships:**
- `CONTAINS_MODULE`, `CONTAINS_FILE`, `REFERENCES_FILE`
- `USES_CONFIGURATION`, `PROCESSES_DATA_SAMPLE`
- `DOCUMENTS`, `HAS_TYPE`, `GENERATES_FILE`
- `CONSUMES`, `PRODUCES`, `EXECUTES`

**Extraction Rules:** Detailed guidelines for each entity and relationship

---

### 15. `graphiti/graphiti-micro-memory-guard.mdc` (626B, 14 lines)
**Type:** Always Apply (`alwaysApply: true`)  
**Purpose:** Minimal always-on memory guard

**Rule:** If and only if task involves long-term context:
- Search existing memory/graph first
- Save new facts at the end
- Otherwise, ignore and proceed normally

**When Applicable:**
- Preferences, procedures, requirements
- Data lineage, run metadata
- Knowledge graph updates

**Tool Preferences:**
- `search_nodes` for Preferences/Procedures/Requirements
- `search_facts` for lineage (CONSUMES/PRODUCES/INFORMED_BY/DEPENDS_ON)
- `add_episode` for task-level events

---

### 16. `graphiti/graphiti-mcp-core-rules.mdc` (9.9KB, 122 lines)
**Type:** Always Apply (`alwaysApply: true`)  
**Purpose:** Core Graphiti MCP tools guide

**Three Rule Types:**
1. Core rules (this file) - General tool usage
2. Project-specific schema - Unique entities/relationships
3. Schema maintenance - Update process

**Key Principles:**
- Entity extraction: Structured patterns, maintain integrity
- Agent memory: Search first, save new info, respect preferences
- Best practices: Search before suggesting, use JSON for structured data
- Codebase organization: Flat structures, semantic naming

**Tool Usage:**
- Search before starting tasks
- Capture requirements immediately
- Document procedures clearly
- Record factual relationships

---

### 17. `graphiti/graphiti-knowledge-graph-maintenance.mdc` (4.8KB, 66 lines)
**Type:** Always Apply (`alwaysApply: true`)  
**Purpose:** Rules for maintaining project-specific schema

**Key Rules:**
1. Project schema is single source of truth
2. Consult schema before defining new entities
3. Verify consistency before adding facts
4. Schema evolution process:
   - Identify need
   - Consult existing schema
   - Propose update with justification
   - Await outcome
   - Proceed based on outcome

**Justification Required:** Link to user request or conversation context

---

## Rule Categories

### Always Apply Rules (8)
1. `output-suppression.mdc` - Command output handling
2. `frontend-focus.mdc` - Frontend development
3. `dashboard-existing-architecture.mdc` - Dashboard constraints
4. `documentation-location.mdc` - Documentation placement
5. `data-provenance-verification.mdc` - Data verification
6. `critical-requirements.mdc` - Codebase organization
7. `critical-requirements-short.mdc` - Quick reference
8. `dsa110-agent-workflow.mdc` - Agent workflow
9. `graphiti/graphiti-micro-memory-guard.mdc` - Memory guard
10. `graphiti/graphiti-mcp-core-rules.mdc` - Core Graphiti rules
11. `graphiti/graphiti-knowledge-graph-maintenance.mdc` - Schema maintenance

### Conditional Rules (7)
1. `codacy.mdc` - Code quality analysis
2. `coding-best-practices.mdc` - Common pitfalls
3. `radio-conventions.mdc` - Radio astronomy conventions
4. `codex.mdc` - ExecPlan guidelines
5. `graphiti/graphiti-dsa110-contimg-schema.mdc` - Project schema

---

## Key Patterns

### Critical Requirements
- **Python Environment:** ALWAYS use `/opt/miniforge/envs/casa6/bin/python`
- **File Organization:** Check `DIRECTORY_ARCHITECTURE.md` before creating files
- **Documentation:** Use `docs/` structure, lowercase_with_underscores naming

### Code Quality
- **Codacy:** Run analysis after every file edit
- **Best Practices:** Inspect signatures, verify environment, check async/await
- **Output:** Never suppress, always use unbuffered output

### Frontend Development
- **Backend:** READ-ONLY reference only
- **Tech Stack:** React 18 + TypeScript + Material-UI v6 (DO NOT CHANGE)
- **Architecture:** Follow existing patterns

### Knowledge Graph
- **Workflow:** Search → Execute → Ingest
- **Schema:** Project schema is single source of truth
- **Memory:** Search first, save new facts

### Data Handling
- **Provenance:** Always verify real vs synthetic data
- **Radio Conventions:** Use existing utilities, valid CASA types only

---

## Recommendations

### Immediate Actions
1. **Remove Duplicate:** Delete `data-provenance-verification.md` (keep `.mdc` version)
2. **Consolidate:** Consider merging `critical-requirements.mdc` and `critical-requirements-short.mdc`
3. **Document:** Create index/quick reference for all rules

### Long-Term Improvements
1. **Rule Organization:** Group related rules into subdirectories
2. **Rule Dependencies:** Document which rules reference others
3. **Rule Testing:** Verify rules are being followed correctly
4. **Rule Updates:** Regular review cycle for rule effectiveness

---

## Rule Dependencies

**Referenced Documents:**
- `docs/concepts/DIRECTORY_ARCHITECTURE.md` (critical-requirements)
- `docs/DOCUMENTATION_QUICK_REFERENCE.md` (documentation-location)
- `scripts/migrate_docs.sh` (documentation-location)
- `docs/reference/mcp-tools.md` (mentioned in MEMORY.md)

**Cross-References:**
- Graphiti rules reference each other (core → schema → maintenance)
- Critical requirements reference documentation location
- Frontend focus references dashboard architecture

---

## Summary Statistics

- **Total Rules:** 17 files (15 unique + 1 duplicate + 1 subdirectory)
- **Always Apply:** 11 rules
- **Conditional:** 6 rules
- **Total Size:** ~70KB
- **Longest Rule:** `codex.mdc` (20KB)
- **Shortest Rule:** `critical-requirements-short.mdc` (596B)

---

**Last Updated:** 2025-11-12  
**Next Review:** 2025-12-12 (monthly cadence recommended)

