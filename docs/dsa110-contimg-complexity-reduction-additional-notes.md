# DSA-110 Contimg: Unified Complexity Reduction & Refactoring Guide

_A comprehensive, pragmatic roadmap for dramatically reducing complexity, technical debt, and onboarding friction in the dsa110-contimg codebase. The advice here synthesizes deep architectural analysis, best practices, and proven migration strategies: follow it systematically for maximal developer impact._

---

## ⚠️ Critical Caveats & Success Essentials

### Before You Start

**Required Prerequisites:**

- [ ] **Get buy-in** from at least two team members; major refactors need consensus and awareness
- [ ] **Schedule dedicated refactoring time**—do not squeeze this in around regular feature work
- [ ] **Set up staging environment** that faithfully mirrors production for all risky migrations
- [ ] **Announce refactoring plans** to all stakeholders with clear timeline
- [ ] **Back up all data and code**—before any bulk deletions, config changes, or DB migration
- [ ] **Implement monitoring** to catch regressions (test coverage, performance metrics, API error rates)

### Stakeholder Coordination

**Check dependencies before proceeding:**

- Database, API, and infrastructure changes may require input from ops, DBAs, frontend devs, or external consumers
- Deprecation policies: If APIs or pipelines have downstream users, communicate changes and allow gradual migration
- Documentation updates will break existing bookmarks/links—provide migration notice and redirects

### Risk Management

**Safety nets for major changes:**

- **Run legacy and new systems in parallel** where possible for a canary period (especially ABSURD migration)
- **Have rollback plan** for every major migration (database unification needs dry runs + automated backups)
- **Review every bulk deletion** with at least one peer before executing
- **ABSURD maturity check:** Verify the framework is battle-tested before full migration; start with non-critical workflows

### Performance & Testing Cautions

- **Benchmark before/after**—measure actual performance, don't just assume improvements
- **Contract tests are slow**—run core tests in CI, heavy integration tests nightly
- **Ship quick wins first**—easy deletions and config consolidation before risky migrations
- **The "15-line database" is conceptual**—production needs ~50 lines for error handling, transactions, timeouts

### When NOT to Simplify

❌ **Stop if:**

- Others are refactoring major sections (merge conflict hell)
- System is in code freeze or under mission-critical deadlines
- You don't know why code exists (ask first!)
- Deletion would break external dependencies without proper deprecation

### Success Metrics

How will we know the refactoring succeeded?

- ✅ **Onboarding time:** ≥50% reduction
- ✅ **Test suite time:** Maintain or improve (not slower)
- ✅ **Bugs introduced:** Minimize via contract tests + parallel execution
- ✅ **Team satisfaction:** Survey before/after on pain points

---

## Table of Contents

1. [Context & Philosophy](#context--philosophy)
2. [Critical Complexity Reductions](#critical-complexity-reductions)
3. [ABSURD Pipeline & Automation](#absurd-pipeline--automation)
4. [Consolidation and Standardization](#consolidation-and-standardization)
5. [Implementation Roadmap (Phase by Phase)](#implementation-roadmap-phase-by-phase)
6. [Contract Testing & Quality](#contract-testing--quality)
7. [Summary Table: Savings & Impact](#summary-table-savings--impact)
8. [Appendices: Implementation Playbook](#appendices-implementation-playbook)
9. [References](#references)

---

## Context & Philosophy

The dsa110-contimg repository evolved naturally as research software does: multiple generations of approaches, coexisting architectures, defensive abstractions, and "just-in-case" legacy code. The result: immense accidental complexity, brittle tests, and a hard-to-onboard codebase.

**Now that requirements are clearer, we can simplify systematically.**

**Guiding Principle:**

> "Favor deletion, simplification, and consolidation. Let architectural clarity, not optionality, drive maintainability."

---

## Critical Complexity Reductions

### 1. Over-Parameterization & "Flexibility" Disease

**Symptoms:**

- Functions (e.g., `convert_group`) with 10–15+ parameters, most with defaults, many unused in production
- Scattered `**kwargs` and config flags for "future proofing"

**Corrective Action:**

- Distill functions to _essential_ parameters (3–4 at most)
- Move rarely-changed knobs into a _single, typed config object_ (Pydantic Settings)
- Document settings in one place; enforce startup validation

**Before:**  
def convert_group(..., max_workers=4, use_subprocess=True, writer_type="direct", ..., \*\*kwargs):

**After:**  
def convert_group(subbands: List[Path], output_ms: Path, scratch_dir: Path = settings.scratch_dir): # All other config is settings.conversion.\*

- Global config (e.g., `settings.conversion.max_workers`) is type-checked and validated at startup
- Tests only cover meaningful configurations, not exponential permutations

**Impact:**

- Function signature: 13 params → 3 params
- Testing surface: ~8,000 combinations → ~10 combinations
- **Cognitive load: -75%**

---

### 2. Eliminate Dead Code, Unused Strategies, & "YAGNI" Patterns

**Symptoms:**

- Legacy writers (e.g., DaskWriter), strategy pattern indirection, unused conversion paths
- Multiple orchestration frameworks (ABSURD + CLI/cron systems)
- Half-implemented API version directories, feature flags, "experimental" toggles

**Corrective Action:**

- **Permanently delete** unused code after peer review
- Keep only the single proven/stable production path
- Git history preserves all else

**⚠️ Backup first! Always review deletions with a peer.**

**Key Commands:**
git rm backend/src/dsa110_contimg/conversion/strategies/dask_writer.py
git rm -rf legacy.frontend legacy.backend
git rm backend/docker-compose.postgresql.yml

# Check for dynamic imports first:

rg "importlib.import_module.\*dask_writer"

---

### 3. Database Over-Normalization & Abstraction Swamps

**Symptoms:**

- Multiple SQLite databases (products, calibration, queue, etc.), each with independent schema
- 6–8 abstraction layers to run a simple query (pooling, validators, serializers, etc.)
- Cross-DB JOINs happen in Python (N+1 queries, brittle)

**Corrective Action:**

- **Unify schemas:** One SQLite database (`pipeline.sqlite3`) with table namespaces
- **Collapse abstraction:** Replace 8-layers with explicit `Database` class (~15 lines core + ~50 for production robustness)
- Write single queries that leverage SQL JOINs

**Example Unified Query:**  
SELECT i.\*, m.ms_path, c.caltable_path
FROM images i
JOIN ms_index m ON i.ms_path = m.ms_path
LEFT JOIN calibration_applied c ON m.ms_path = c.ms_path
WHERE i.created_at > ?

**Migration Strategy:** Use one-time, backed-up script (see Appendix A). Dry run first!

**Impact:**

- Call stack: 8 layers → 1 layer
- Code: ~800 lines → ~65 lines (15 core + 50 production)
- **Performance: ~2× faster** (no abstraction overhead)

---

### 4. Module & Abstraction Flattening

**Symptoms:**

- Deep, unnecessary submodules: `conversion/streaming/streaming_converter.py`
- Overwrought class inheritance trees for jobs/pipelines
- Duplicated code across interfaces

**Corrective Action:**

- Collapse submodules unless they house ≥3 meaningfully different files
- Limit inheritance: maximum two levels (e.g., `Job` base + one specialized)
- Favor composition for injectables (e.g., CASA context) over subclassing

---

### 5. Configuration Sprawl & Type Hygiene

**Symptoms:**

- Config scattered among environment variables, YAML, hardcoded defaults, .env files, database columns
- Untyped, unvalidated conversions (e.g., `os.getenv(..., "2048")` then `int(...)`)
- **Boolean trap:** `os.getenv("USE_FAST_MODE", "False")` evaluates as truthy!

**Corrective Action:**

- Use single `config.py` with Pydantic `Settings` class—typed, validated, startup-checked
- Always prefer `Path` objects over strings, with adapters for CASA string APIs

**Type Adapter Pattern for CASA:**

# backend/src/dsa110_contimg/casa/adapter.py

from pathlib import Path
from typing import TypeVar, Callable, ParamSpec
from functools import wraps

P = ParamSpec('P')
R = TypeVar('R')

def casa_paths(*path_params: str):
"""Decorator: Converts Path → str for CASA parameters"""
def decorator(func: Callable[P, R]) -> Callable[P, R]:
@wraps(func)
def wrapper(*args, **kwargs):
import inspect
sig = inspect.signature(func)
bound = sig.bind(\*args, **kwargs)

            for param_name in path_params:
                if param_name in bound.arguments:
                    value = bound.arguments[param_name]
                    if isinstance(value, Path):
                        bound.arguments[param_name] = str(value)

            return func(*bound.args, **bound.kwargs)
        return wrapper
    return decorator

# Usage:

@casa_paths('vis', 'imagename')
def tclean_wrapper(vis: Path, imagename: Path, **kwargs) -> Path:
"""Public API uses Path; decorator handles conversion"""
from casatasks import tclean
tclean(vis=vis, imagename=imagename, **kwargs) # Already strings
return Path(imagename)

**New Policy:**

1. **ALL public APIs use Path** (100% consistency)
2. **CASA adapters handle conversions** (centralized, not scattered)
3. **Type system enforces correctness** (mypy verifies at dev time)

**Note:** Handles 90% of cases; complex signatures may need manual handling.

---

### 6. Metrics & Logging Simplification

**Symptoms:**

- Metrics code scattered in every function (5-10 lines per function × 80 functions = 800 lines)
- Manual try/except blocks just for emitting metrics

**Corrective Action:**

- Use decorator (e.g., `@timed`) for automatic timing/logging
- Store only _essential_ events in database; routine logs via Python logger
- **Benchmark before/after** to verify improvements

**Impact:**

- Metric code: -85% lines
- Database writes: -90% (only critical events)
- Testing complexity: -75%

---

### 7. Testing Overhaul: From Mocks to Contracts

**Symptoms:**

- Mock-heavy unit tests asserting order of internal calls, not validating actual behavior
- Many integration gaps; real input/output rarely checked

**Corrective Action:**

- Prefer contract tests using synthetic but realistic data
- Focus on verifying observable outputs with real pipeline components
- **Balance:** Fast contract tests in CI, heavy integration tests nightly
- **Keep good unit tests:** Not all mocks are bad—retain fast tests for stateless logic

**Example contract test:**
def test_conversion_produces_valid_ms(tmp_path, synthetic_hdf5):
from dsa110_contimg.conversion import convert_group
from casacore import tables as ct

    ms_path = tmp_path / "output.ms"
    convert_group(synthetic_hdf5, ms_path)

    tb = ct.table(str(ms_path))
    assert "DATA" in tb.colnames()
    # ... check more invariants
    tb.close()

---

## ABSURD Pipeline & Automation

### Core Principles

**⚠️ Verify ABSURD framework maturity before full migration!**

- **Start with canary workflows** (non-critical pipelines first)
- **Run legacy and ABSURD in parallel** for at least one full cycle
- All mosaicking, imaging, calibrating, QA should be ABSURD jobs eventually
- Use job classes with clear dependencies and retry policies
- Aggregate state via unified database

### Job Architecture

**ABSURD pipeline structure:**
backend/src/dsa110_contimg/
├── pipeline/
│ ├── mosaic/
│ │ ├── jobs.py # MosaicPlanningJob, MosaicBuildJob, MosaicQAJob
│ │ ├── pipeline.py # Pipeline definitions
│ │ └── scheduler.py # Register with ABSURD
│ └── base.py # Job, Pipeline base classes

### Event-Driven Execution

**Event sources:**

- Cron triggers (daily/weekly scheduled)
- API requests (user-initiated)
- Detection algorithms (ESE candidate → auto-mosaic)
- Calibration updates (new cal → rebuild affected mosaics)

**Example: Nightly Mosaic Pipeline**
class NightlyMosaicPipeline(Pipeline):
pipeline_name = "nightly_mosaic"

    def __init__(self, config: PipelineConfig):
        super().__init__(config)

        # Job graph with dependencies
        self.add_job(MosaicPlanningJob, job_id='plan', params={...})
        self.add_job(MosaicBuildJob, job_id='build',
                    params={'plan_id': '${plan.plan_id}'},
                    dependencies=['plan'])
        self.add_job(MosaicQAJob, job_id='qa',
                    params={'mosaic_id': '${build.mosaic_id}'},
                    dependencies=['build'])

        # Retry policy
        self.set_retry_policy(max_retries=2, backoff='exponential')

        # Notifications on failure
        self.add_notification(on_failure='qa', channels=['email', 'slack'])

### Zero-Intervention Operations

**Automated daily workflow:**

1. ✅ 03:00 UTC: Nightly mosaic auto-triggered
2. ✅ Images queried from unified DB
3. ✅ Tier auto-selected (quicklook vs science)
4. ✅ Mosaic built with optimal parameters
5. ✅ QA runs automatically
6. ✅ Results registered in database
7. ✅ Dashboard updates in real-time
8. ✅ Notifications sent only on QA failure

**Key advantage:** No manual intervention, no cron files, no systemd units. Everything is code-defined, version-controlled, and testable.

---

## Consolidation and Standardization

**Documentation:**

- Archive or delete `legacy.frontend/backend/` after peer review
- Consolidate docs under flattened `/docs` structure (see Appendix C)
- Provide migration notice with redirects for broken links

**CI/CD:**

- Unify test and deployment configuration
- Communicate breaking changes to downstream consumers

---

## Implementation Roadmap (Phase by Phase)

### Timeline Expectations

**Aggressive timeline:** 3-4 months (dedicated full-time developer, no blockers)  
**Conservative timeline:** 6-12 months (part-time, production priorities, unexpected issues)

### **Phase 1: Safe Deletions (Weeks 1-2)**

**Goal:** Remove confirmed dead code with minimal risk

**Actions:**

- Delete unused writers (DaskWriter), PostgreSQL configs, feature flags
- Archive legacy frontends/backends
- Remove `/api/v1/` premature versioning

**Validation:**

- All tests still pass
- System functions identically

**Ship to production:** Yes—these are pure deletions with no behavior change

---

### **Phase 2: Consolidation (Weeks 3-6)**

**Goal:** Unify scattered systems

**Actions:**

- Migrate databases (5 → 1) using script from Appendix A
  - **Run dry-run first**
  - **Backup everything**
  - **Test queries exhaustively before deleting source DBs**
- Flatten module hierarchy
- Standardize configuration (Pydantic Settings)
- Refactor metrics/logging (decorators)

**Validation:**

- Run full integration test suite
- Compare queries: old vs. new database
- Verify config loads correctly at startup

**Ship to production:** After 1-week staging validation

---

### **Phase 3: ABSURD Automation (Weeks 7-10)**

**Goal:** Migrate orchestration to ABSURD

**⚠️ High risk—proceed carefully!**

**Actions:**

- Implement ABSURD jobs for all workflows
- **Run ABSURD and legacy in parallel** for 2 weeks minimum
- Monitor for discrepancies
- Only decommission legacy after zero-diff validation

**Validation:**

- Compare outputs: ABSURD vs. legacy (bit-for-bit identical)
- Performance benchmarks (should not regress)
- Error handling works (simulate failures)

**Ship to production:** Gradual rollout (10% → 50% → 100% traffic)

---

### **Phase 4: Testing & Polish (Weeks 11-12)**

**Goal:** Harden quality assurance

**Actions:**

- Replace mock-heavy tests with contract tests (see Appendix D)
- Consolidate documentation (see Appendix C)
- Update onboarding materials
- Announce refactoring completion to team

**Validation:**

- New developer onboarding time measured (should be ≥50% faster)
- Team satisfaction survey

---

## Contract Testing & Quality

**Principle:** Test actual behavior with real files, not mock call order.

**Strategy:**

- **CI:** Fast contract tests (< 5 min total)
- **Nightly:** Heavy integration tests with real data
- **Keep:** Fast unit tests for pure logic (not all mocks are bad!)

**See Appendix D for complete examples.**

---

## Summary Table: Savings & Impact

| Change Area            | Lines Removed | Files Removed | Concepts Removed     | Developer Benefit      |
| ---------------------- | ------------- | ------------- | -------------------- | ---------------------- |
| Dead code/strategies   | ~2,000        | 3             | 2 code paths         | Reduced confusion      |
| DB unification         | ~2,000        | 5             | 4 DBs, 8 layers      | Easier queries         |
| Module flattening      | ~200          | 15            | Deep nesting         | Top-level clarity      |
| Metrics simplification | ~800          | 0             | 480 test cases       | Easier testing         |
| Config standardization | ~600          | 8             | 8 config sources     | Type-safe validated    |
| Legacy cleanup         | ~5,000        | 100           | Two+ UIs             | Obvious plan           |
| Docs consolidation     | ~100          | 10            | Redundant navigation | Fast onboarding        |
| Test overhaul          | ~2,000        | 0             | False confidence     | Higher confidence      |
| PostgreSQL experiments | ~400          | 3             | Experimental backend | Decision clarity       |
| Node.js in Python      | 75KB          | 4             | Two ecosystems       | Setup simplicity       |
| **TOTAL**              | **~13,100**   | **~148**      | **~20 concepts**     | **Much less friction** |

### Compound Complexity Effect

Each abstraction layer multiplies code size by ~1.2-1.5×:

Base function: 10 lines

- Parameter validation: 13 lines (×1.3)
- Strategy pattern: 19 lines (×1.5)
- Database abstraction: 27 lines (×1.4)
- Error handling: 35 lines (×1.3)
- Metrics: 42 lines (×1.2)
- Logging: 50 lines (×1.2)
  ────────────────────────────────────
  Result: 10 lines → 50 lines (5× bloat)

**Across 200 functions:**

- Expected: 2,000 lines
- Actual: 10,000 lines
- **Accidental complexity: 8,000 lines (80%)**

---

## Appendices: Implementation Playbook

### Appendix A: Database Migration Script

**Complete production-ready script with dry-run, backups, verification.**

See full implementation in original document—includes:

- Automated timestamped backups
- Schema creation for unified database
- Table-by-table migration with conflict handling
- Verification counts
- Rollback instructions

**Usage:**
python scripts/migrate_databases.py --dry-run # Preview
python scripts/migrate_databases.py # Execute

---

### Appendix B: Simplified Database Layer

**15-line core + 50 lines production robustness = 65 lines total**

# backend/src/dsa110_contimg/database.py

import sqlite3
from pathlib import Path
from typing import List, Dict, Any

class Database:
"""Simple SQLite wrapper with dict rows"""

    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute SELECT, return list of dicts"""
        cursor = self.conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def execute(self, sql: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE, return affected rows"""
        cursor = self.conn.execute(sql, params)
        self.conn.commit()
        return cursor.rowcount

    def close(self):
        self.conn.close()

**That's the core. Add ~50 lines for:**

- Connection error handling/retries
- Query timeouts
- Transaction context managers
- Concurrent access locks (if needed)

---

### Appendix C: Documentation Restructuring

**Before:** 27+ subdirectories, duplicated content  
**After:** 6 core files, single source of truth

**New structure:**
docs/
├── README.md # Navigation hub
├── quickstart.md # 5-minute setup
├── user-guide.md # Complete user docs
├── developer-guide.md # Complete dev docs
├── api-reference.md # Auto-generated
├── troubleshooting.md # All common issues
├── architecture-decisions/ # Historical ADRs
└── assets/ # Images

**Migration strategy:** Merge scattered content under appropriate headings in consolidated files.

---

### Appendix D: Contract Test Examples

**✅ What TO Do: Real File I/O Tests**

def test_conversion_creates_valid_casa_ms(synthetic_hdf5, tmp_path):
"""Verify output is valid CASA Measurement Set"""
output_ms = tmp_path / "converted.ms"

    # Actual conversion (no mocks!)
    result = convert_group(synthetic_hdf5, output_ms)

    # Verify CASA can open it
    tb = ct.table(str(output_ms))
    assert "DATA" in tb.colnames()
    tb.close()

**❌ What NOT to Do: Mock-Heavy Tests**

def test_convert_group_calls_functions(mocker): # Mock everything
mock_read = mocker.patch("...read_hdf5")
mock_write = mocker.patch("...write_ms")

    result = convert_group([Path("fake")])

    # Only tests mocks were called—NOT that conversion works!
    assert mock_read.called
    assert mock_write.called

**Why contracts win:** Test actual behavior, catch real bugs, survive refactoring.

---

### Appendix E: Common Pitfalls & Quick Fixes

**Pitfall 1: Over-Eager Refactoring**

- **Fix:** One phase at a time, merge after validation

**Pitfall 2: Forgetting Import Updates**

- **Fix:** Use automated refactoring tools, verify with mypy

**Pitfall 3: No Database Backup**

- **Fix:** Migration script includes automatic backups

**Pitfall 4: Deleting "Unused" Dynamic Code**

- **Fix:** Check for `importlib.import_module`, string-based imports

**Pitfall 5: Breaking Backward Compatibility**

- **Fix:** Deprecation warnings, gradual migration over 2-3 releases

---

## References

1. _Deep Dive: Hidden Complexity in dsa110-contimg_ (internal analysis)
2. _Complexity Reduction Opportunities in dsa110-contimg_ (internal)
3. _ABSURD-Governed Mosaicking: Automated Job Architecture_ (pipelines)

---

## The End Goal

**A codebase ~35–40% smaller, with:**

- Unified production path for every feature
- Vastly reduced "decision debt"
- Single, clear way to get any task done
- ≥50% faster developer onboarding
- Higher confidence through contract testing

**Tagline:** _Simplify systematically. The future developer will thank you._
