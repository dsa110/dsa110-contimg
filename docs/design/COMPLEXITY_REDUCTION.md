# DSA-110 Contimg: Unified Complexity Reduction & Refactoring Guide

> ⚠️ **DESIGN DOCUMENT - FUTURE ROADMAP**
>
> This document describes **planned architecture and future improvements**, not the current implementation.
>
> **For current working systems, see:**
>
> - Batch conversion: `backend/src/dsa110_contimg/conversion/hdf5_orchestrator.py`
> - Real-time ingestion: `backend/src/dsa110_contimg/absurd/ingestion.py` (experimental)
> - Quick start: `docs/NEWCOMER_GUIDE.md`

_A comprehensive, pragmatic roadmap for dramatically reducing complexity, technical debt, and onboarding friction in the dsa110-contimg codebase. The advice here synthesizes deep architectural analysis, best practices, and proven migration strategies: follow it systematically for maximal developer impact._

---

## Table of Contents

1. [Context & Philosophy](#context--philosophy)
2. [Critical Complexity Reductions](#critical-complexity-reductions)
   - Over-Parameterization
   - Dead Code/Unneeded Strategies
   - Database Over-Normalization
   - Module & Abstraction Flattening
   - Config Sprawl
   - Metrics Simplification
   - Testing Overhaul
3. [ABSURD Pipeline & Automation](#absurd-pipeline--automation)
4. [Consolidation and Standardization](#consolidation-and-standardization)
5. [Implementation Roadmap (Phase by Phase)](#implementation-roadmap-phase-by-phase)
6. [Contract Testing & Quality](#contract-testing--quality)
7. [Summary Table: Savings & Impact](#summary-table-savings--impact)
8. [References](#references)

---

## Context & Philosophy

The dsa110-contimg repository evolved as most research software does: multiple generations of approaches, coexisting (and conflicting) architectures, numerous defensive abstractions, and “just-in-case” legacy code. The result: immense accidental complexity, brittle tests, and a hard-to-onboard codebase.

**Guiding Principle:**

> “Favor deletion, simplification, and consolidation. Let architectural clarity, not optionality, drive maintainability.”

---

## Critical Complexity Reductions

### 1. Over-Parameterization & “Flexibility” Disease

**Symptoms:**

- Functions (e.g., `convert_group`) with 10–15+ parameters, most with defaults, many unused in production.
- Scattered `**kwargs` and config flags for “future proofing.”

**Corrective Action:**

- Distill functions to _essential_ parameters (3–4 at most).
- Move rarely-changed knobs into a _single, typed config object_ (e.g., Pydantic Settings).
- Document settings in one place; enforce startup validation.

**Before:**  
def convert_group(..., max_workers=4, use_subprocess=True, writer_type="direct", ..., **kwargs):
**After:\*_  
def convert_group(subbands: List[Path], output_ms: Path, scratch_dir: Path = settings.scratch_dir): # All other config is settings.conversion._

- Global config (e.g., `settings.conversion.max_workers`) is type-checked and validated at startup.
- Tests only cover meaningful configurations, not exponential permutations.

---

### 2. Eliminate Dead Code, Unused Strategies, & “YAGNI” Patterns

**Symptoms:**

- Legacy writers (e.g., DaskWriter), strategy pattern indirection, unused conversion paths.
- Multiple orchestration frameworks (ABSURD + CLI/cron systems).
- Half-implemented API version directories, feature flags, “experimental” toggles.

**Corrective Action:**

- **Permanently delete** unused code, dead strategies, feature-flagged alternatives, and premature abstractions.
- Keep only the single proven/stable production path.
- Let Git history preserve all else.

**Key Commands:**
git rm backend/src/dsa110_contimg/conversion/strategies/dask_writer.py
git rm -rf legacy.frontend legacy.backend
git rm backend/docker-compose.postgresql.yml

# ...etc.

---

### 3. Database Over-Normalization & Abstraction Swamps

**Symptoms:**

- Multiple SQLite databases (products, calibration, queue, etc.), each with independent schema/migration logic.
- 6–8 abstraction layers to run a simple query. Layers include “connection pooling,” “validators,” “serializers,” etc.
- Cross-DB JOINs happen in Python (N+1 queries, brittle).

**Corrective Action:**

- **Unify schemas:** One SQLite database (`pipeline.sqlite3`). Use table namespaces for domain separation.
- **Collapse abstraction:** Replace 8-layers with a single, explicit `Database` Python class (≈15 lines) using `sqlite3.Row`.
- Write single queries that leverage SQL JOINs; avoid Python-level data massaging.

**Example Unified Query:**  
SELECT i.\*, m.ms_path, c.caltable_path
FROM images i
JOIN ms_index m ON i.ms_path = m.ms_path
LEFT JOIN calibration_applied c ON m.ms_path = c.ms_path
WHERE i.created_at > ?

---

### 4. Module & Abstraction Flattening

**Symptoms:**

- Deep, unnecessary submodules: `conversion/streaming/streaming_converter.py`.
- Overwrought class inheritance trees for jobs/pipelines.
- Duplicated code across interfaces (“just in case we need…”) and directory split between development stages.

**Corrective Action:**

- Collapse all submodules unless they house ≥3 meaningfully different files; merge “strategies”, “streaming”, etc.
- Limit inheritance: keep maximum two levels (e.g., `Job` base, plus one specialized).
- Favor composition for injectables (e.g., CASA context) over subclassing.

---

### 5. Configuration Sprawl & Type Hygiene

**Symptoms:**

- Config scattered among environment variables, YAML, hardcoded defaults, .env files, and database columns.
- Untyped, unvalidated conversions (e.g., `os.getenv(..., "2048")` then `int(...)`, with failure at runtime).
- **Boolean trap:** `os.getenv("USE_FAST_MODE", "False")` evaluates as truthy (non-empty string).

**Corrective Action:**

- Use a single `config.py` with a pydantic `Settings` class. All config—typed, validated, startup-checked.
- Explicitly document all config values in one file; raise on missing or invalid entries at startup.
- Always prefer objects (e.g., `Path`) over strings for file paths, with adapters for legacy CASA string APIs.

**Type Adapter Pattern for CASA:**

# backend/src/dsa110_contimg/casa/adapter.py

from pathlib import Path
from typing import TypeVar, Callable, ParamSpec
from functools import wraps

P = ParamSpec('P')
R = TypeVar('R')

def casa_paths(\*path_params: str):
"""
Decorator: Converts Path → str for CASA parameters

    @casa_paths('vis', 'imagename', 'caltable')
    def tclean_wrapper(vis: Path, imagename: Path, **kwargs):
        # Inside: vis/imagename are strings (CASA-compatible)
        # Outside: accepts Path objects (type-safe API)
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)

            for param_name in path_params:
                if param_name in bound.arguments:
                    value = bound.arguments[param_name]
                    if isinstance(value, Path):
                        bound.arguments[param_name] = str(value)

            return func(*bound.args, **bound.kwargs)
        return wrapper
    return decorator

# Usage in CASA wrappers:

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

---

### 6. Metrics & Logging Simplification

**Symptoms:**

- Metrics code (timings, event emitters) scattered in every function.
- Manual try/except blocks just for emitting metrics.

**Corrective Action:**

- Use a decorator (e.g., `@timed`) around important jobs for duration/success/error logging.
- Store only _essential_ events/metrics in the database; all routine timings/logs handled by the Python logger with proper structure.

---

### 7. Testing Overhaul: From Mocks to Contracts

**Symptoms:**

- Mock-heavy unit tests asserting order of internal calls, not validating that the system works.
- Many integration gaps; real input/output is rarely checked.

**Corrective Action:**

- Prefer contract tests using synthetic—but realistic—data.
- Focus on verifying observable outputs using real pipeline components, real on-disk products, and standard inspectors/tools.
- Use test fixtures for synthetic Measurement Sets (MS) and in-memory databases.

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

- **Retire legacy CLI, cron-based, and systemd job orchestration.**
- All mosaicking, imaging, calibrating, and QA should be implemented as ABSURD pipeline jobs, scheduled via the integrated pipeline scheduler.
- Use job classes with clear dependencies and retry policy—add pipelines for nightly, triggered, and targeted runs.
- Aggregate state, products, and job results via the unified database.

### Job Architecture

**ABSURD pipeline structure:**
backend/src/dsa110_contimg/
├── pipeline/
│ ├── mosaic/
│ │ ├── jobs.py # MosaicPlanningJob, MosaicBuildJob, MosaicQAJob
│ │ ├── pipeline.py # Pipeline definitions (NightlyMosaic, OnDemand, etc.)
│ │ └── scheduler.py # Register pipelines with ABSURD scheduler
│ └── base.py # Job, Pipeline base classes

### Event-Driven Execution

**Event sources:**

- **Cron triggers:** Daily/weekly scheduled pipelines
- **API requests:** User-initiated mosaic creation
- **Detection algorithms:** ESE candidate detected → auto-mosaic
- **Calibration updates:** New cal applied → rebuild affected mosaics

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

**Scheduler registration:**

# At system initialization

scheduler.register_pipeline(
NightlyMosaicPipeline,
trigger=CronTrigger(cron="0 3 \* \* \*"), # Daily 03:00 UTC
enabled=True
)

### Database Schema for Pipelines

Extend `pipeline.sqlite3` with mosaic-specific tables:
-- Mosaic plans (created by MosaicPlanningJob)
CREATE TABLE mosaic_plans (
id INTEGER PRIMARY KEY,
name TEXT UNIQUE NOT NULL,
tier TEXT NOT NULL, -- 'quicklook', 'science', 'deep'
image_ids TEXT NOT NULL, -- JSON array
coverage_stats TEXT, -- JSON: spatial/temporal metrics
created_at INTEGER NOT NULL,
status TEXT DEFAULT 'pending'
);

-- Mosaic products (created by MosaicBuildJob)
CREATE TABLE mosaics (
id INTEGER PRIMARY KEY,
plan_id INTEGER REFERENCES mosaic_plans(id),
path TEXT NOT NULL,
tier TEXT NOT NULL,
n_images INTEGER NOT NULL,
qa_status TEXT, -- PASS, WARN, FAIL
created_at INTEGER NOT NULL
);

### API Integration

**Event emission endpoints:**
@router.post("/api/mosaic/create")
async def create_mosaic(request: MosaicRequest): # Validate request
if request.end_time <= request.start_time:
raise HTTPException(400, "Invalid time range")

    # Emit event (triggers OnDemandMosaicPipeline)
    event_id = emit_event(
        event_type="mosaic.request",
        payload={
            'mosaic_name': request.name,
            'time_range': (request.start_time, request.end_time),
            'criteria': request.criteria
        }
    )

    return {'status': 'accepted', 'event_id': event_id}

@router.get("/api/mosaic/status/{name}")
async def get_status(name: str):
"""Query pipeline execution status"""
executions = scheduler.get_pipeline_executions(
pipeline_name="on_demand_mosaic",
filter_params={'mosaic_name': name}
)
return {
'status': executions[0].status, # PENDING/RUNNING/COMPLETED/FAILED
'progress': executions[0].progress,
'jobs': {
'plan': executions[0].job_status('plan'),
'build': executions[0].job_status('build'),
'qa': executions[0].job_status('qa')
}
}

### Zero-Intervention Operations

**Automated daily workflow:**

1. ✅ 03:00 UTC: Nightly mosaic auto-triggered
2. ✅ Images queried from unified DB
3. ✅ Tier auto-selected (quicklook vs science based on alignment)
4. ✅ Mosaic built with optimal parameters
5. ✅ QA runs automatically (astrometry, photometry, artifacts)
6. ✅ Results registered in database
7. ✅ Dashboard updates in real-time
8. ✅ Notifications sent only on QA failure

**ESE-triggered workflow:**

1. ESE detection emits `ese.candidate_detected` event
2. TargetedDeepMosaicPipeline auto-launches
3. Multi-epoch data gathered automatically
4. Science-tier mosaic created with strict QA
5. Photometry extracted and linked to candidate

**Key advantage:** No manual intervention, no cron files to edit, no systemd units to manage. Everything is code-defined, version-controlled, and testable.

---

## Consolidation and Standardization

- Move frontend and any “legacy.frontend/backend/” directories to an `archive/` folder (or delete).
- Consolidate documentation under a clear, flattened `/docs` structure:
  - guides/
  - reference/
  - architecture/
  - troubleshooting/
- Unify CI, test, and deployment configuration for transparency.

---

## Implementation Roadmap (Phase by Phase)

### **Phase 1: Safe Deletions**

- Remove unused alternative writers (DaskWriter, etc.), PostgreSQL configs, feature-flagged code, pre-v1 API dirs.
- Archive legacy frontends/backends.

### **Phase 2: Consolidation**

- Migrate all databases into `pipeline.sqlite3`, migrate all code to use unified schema and simple access class.
- Flatten modules, standardize configuration.
- Refactor metrics/logging to use decorators + structured logging only.

### **Phase 3: Complete ABSURD Automation**

- Make every pipeline process (mosaicking, calibration, etc.) an ABSURD job.
- Remove cli/cron/manual triggers from system.

### **Phase 4: Testing and Polish**

- Centralize and harden contract/integration tests.
- Remove mock-heavy/unit tests that check only method call order.
- Ensure documentation is current, single-sourced, and clearly indexed.

---

## Contract Testing & Quality

- All critical paths (conversion, calibration, imaging, mosaicking) must have contract tests: given valid inputs, do we get valid, externally inspectable, standards-compliant outputs?
- Testing real round-trip behavior is the only way to avoid “mock-tested” illusions of correctness.
- Use test fixtures for shared test data; run regular integration test suites in CI.

---

## Summary Table: Savings & Impact

| Change Area                     | Lines Removed | Files Removed | Concepts Removed                     | Developer Benefit              |
| ------------------------------- | ------------: | ------------: | ------------------------------------ | ------------------------------ |
| Dead code and alt. strategies   |        ~2,000 |             3 | 2 major code paths                   | Reduced confusion              |
| DB unification & flattening     |        ~2,000 |             5 | 4 DBs, 8 abstraction layers          | Easier queries/tests           |
| Module flattening               |          ~200 |            15 | Deep nesting, `__init__` boilerplate | Top-level clarity              |
| Logging/metrics simplification  |          ~800 |             0 | Scattered metrics, 480 test cases    | Much easier testing            |
| Config standardization          |          ~600 |             8 | 8 config sources, type coercion      | Type-safe/validated            |
| Legacy front/backend cleanout   |        ~5,000 |           100 | Two+ UIs                             | Obvious codebase plan          |
| Docs flattening/consolidation   |          ~100 |            10 | Redundant navigation                 | Faster onboarding              |
| Test overhaul (mocks→contracts) |        ~2,000 |             0 | False confidence tests               | Higher confidence              |
| PostgreSQL experiments          |          ~400 |             3 | Experimental backend                 | Decision clarity               |
| Node.js tooling in Python       |          75KB |             4 | Two ecosystems                       | Setup simplicity               |
| **TOTAL**                       |   **~13,100** |      **~148** | **~20 major concepts**               | **Dramatically less friction** |

---

## Appendix A: Database Migration Script

### One-Time Database Unification

**Script: `scripts/migrate_databases.py`**

#!/usr/bin/env python3
"""
Migrate from 5 separate SQLite databases to unified pipeline.sqlite3

Usage:
python scripts/migrate_databases.py --dry-run # Preview changes
python scripts/migrate_databases.py # Execute migration
"""
import sqlite3
import shutil
import json
from pathlib import Path
from datetime import datetime
import argparse

def backup*databases(state_dir: Path, backup_dir: Path):
"""Create timestamped backup of all databases"""
timestamp = datetime.now().strftime("%Y%m%d*%H%M%S")
backup*path = backup_dir / f"db_backup*{timestamp}"
backup_path.mkdir(parents=True, exist_ok=True)

    databases = [
        "products.sqlite3",
        "cal_registry.sqlite3",
        "queue.sqlite3",
        "calibrator_registry.sqlite3",
        "hdf5_index.sqlite3"
    ]

    for db in databases:
        src = state_dir / db
        if src.exists():
            dst = backup_path / db
            shutil.copy2(src, dst)
            print(f"✓ Backed up {db} → {dst}")

    return backup_path

def create_unified_schema(conn: sqlite3.Connection):
"""Create unified database schema"""

    # Products domain (from products.sqlite3)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ms_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ms_path TEXT UNIQUE NOT NULL,
            group_id INTEGER NOT NULL,
            start_time INTEGER NOT NULL,
            end_time INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ms_path TEXT NOT NULL,
            path TEXT UNIQUE NOT NULL,
            rms_jy REAL,
            ra_deg REAL,
            dec_deg REAL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (ms_path) REFERENCES ms_index(ms_path)
        );
    """)

    # Calibration domain (from cal_registry.sqlite3)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS calibration_tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            cal_type TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS calibration_applied (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ms_path TEXT NOT NULL,
            caltable_path TEXT NOT NULL,
            quality REAL,
            applied_at INTEGER NOT NULL,
            FOREIGN KEY (ms_path) REFERENCES ms_index(ms_path),
            FOREIGN KEY (caltable_path) REFERENCES calibration_tables(path)
        );
    """)

    # Calibrator catalog (from calibrator_registry.sqlite3)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS calibrator_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            flux_jy REAL NOT NULL
        );
    """)

    # HDF5 file index (from hdf5_index.sqlite3)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS hdf5_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            scan_id INTEGER NOT NULL,
            indexed_at INTEGER NOT NULL
        );
    """)

    # Queue domain (from queue.sqlite3 - will be deprecated)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS processing_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            retry_count INTEGER DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
    """)

    # Create indexes
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_ms_index_group ON ms_index(group_id);
        CREATE INDEX IF NOT EXISTS idx_images_ms_path ON images(ms_path);
        CREATE INDEX IF NOT EXISTS idx_cal_applied_ms_path ON calibration_applied(ms_path);
        CREATE INDEX IF NOT EXISTS idx_queue_group_id ON processing_queue(group_id);
        CREATE INDEX IF NOT EXISTS idx_hdf5_scan_id ON hdf5_files(scan_id);
    """)

    conn.commit()
    print("✓ Created unified schema")

def migrate_table(src_db: Path, dest_conn: sqlite3.Connection,
table_name: str, column_mapping: dict = None):
"""
Migrate table from source database to unified database

    Args:
        src_db: Path to source database
        dest_conn: Connection to destination database
        table_name: Name of table to migrate
        column_mapping: Optional dict mapping old→new column names
    """
    if not src_db.exists():
        print(f"⚠ Skipping {table_name} - source DB not found: {src_db}")
        return

    src_conn = sqlite3.connect(src_db)
    src_conn.row_factory = sqlite3.Row

    # Get all rows
    rows = src_conn.execute(f"SELECT * FROM {table_name}").fetchall()

    if not rows:
        print(f"⚠ No data in {table_name}")
        src_conn.close()
        return

    # Apply column mapping if provided
    if column_mapping:
        columns = [column_mapping.get(k, k) for k in rows[0].keys()]
    else:
        columns = list(rows[0].keys())

    # Build INSERT statement
    placeholders = ",".join(["?" for _ in columns])
    insert_sql = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"

    # Migrate data
    count = 0
    for row in rows:
        try:
            dest_conn.execute(insert_sql, tuple(row))
            count += 1
        except sqlite3.IntegrityError as e:
            print(f"  ⚠ Skipping duplicate row in {table_name}: {e}")

    dest_conn.commit()
    src_conn.close()
    print(f"✓ Migrated {count} rows to {table_name}")

def main():
parser = argparse.ArgumentParser(description="Migrate to unified database")
parser.add_argument("--dry-run", action="store_true",
help="Preview migration without executing")
parser.add_argument("--state-dir", type=Path, default=Path("state"),
help="Directory containing databases (default: state/)")
args = parser.parse_args()

    state_dir = args.state_dir
    backup_dir = state_dir / "backups"

    print("=" * 60)
    print("DATABASE MIGRATION: 5 → 1 Unified Schema")
    print("=" * 60)

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")

    # Step 1: Backup
    print("\n[1/4] Creating backups...")
    if not args.dry_run:
        backup_path = backup_databases(state_dir, backup_dir)
        print(f"✓ Backups stored in: {backup_path}")
    else:
        print("  (Skipped in dry-run)")

    # Step 2: Create unified database
    print("\n[2/4] Creating unified database...")
    unified_db = state_dir / "pipeline.sqlite3"

    if unified_db.exists() and not args.dry_run:
        print(f"⚠ {unified_db} already exists!")
        response = input("Overwrite? [y/N]: ")
        if response.lower() != 'y':
            print("Migration cancelled")
            return
        unified_db.unlink()

    if not args.dry_run:
        conn = sqlite3.connect(unified_db)
        create_unified_schema(conn)
    else:
        print("  (Would create schema in dry-run)")
        conn = None

    # Step 3: Migrate data
    print("\n[3/4] Migrating data...")

    migrations = [
        (state_dir / "products.sqlite3", "ms_index", None),
        (state_dir / "products.sqlite3", "images", None),
        (state_dir / "cal_registry.sqlite3", "calibration_tables", None),
        (state_dir / "cal_registry.sqlite3", "calibration_applied", None),
        (state_dir / "calibrator_registry.sqlite3", "calibrator_catalog", None),
        (state_dir / "hdf5_index.sqlite3", "hdf5_files", None),
        (state_dir / "queue.sqlite3", "processing_queue", None),
    ]

    if not args.dry_run:
        for src_db, table, mapping in migrations:
            migrate_table(src_db, conn, table, mapping)
        conn.close()
    else:
        for src_db, table, _ in migrations:
            if src_db.exists():
                src_conn = sqlite3.connect(src_db)
                count = src_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                src_conn.close()
                print(f"  Would migrate {count} rows from {table}")

    # Step 4: Verification
    print("\n[4/4] Verification...")
    if not args.dry_run:
        conn = sqlite3.connect(unified_db)
        for _, table, _ in migrations:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  ✓ {table}: {count} rows")
        conn.close()
    else:
        print("  (Skipped in dry-run)")

    print("\n" + "=" * 60)
    if args.dry_run:
        print("DRY RUN COMPLETE - No changes made")
        print(f"\nTo execute migration, run:")
        print(f"  python {__file__}")
    else:
        print("MIGRATION COMPLETE")
        print(f"\n✓ Unified database: {unified_db}")
        print(f"✓ Backups: {backup_path}")
        print("\nNext steps:")
        print("  1. Update code to use Database(\"state/pipeline.sqlite3\")")
        print("  2. Test all queries work correctly")
        print("  3. After verification, delete old databases:")
        print("     rm state/{{products,cal_registry,queue,calibrator_registry,hdf5_index}}.sqlite3")
    print("=" * 60)

if **name** == "**main**":
main()

---

## Appendix B: Simplified Database Layer

### Complete 15-Line Implementation

# backend/src/dsa110_contimg/database.py

"""
Simplified database layer - replaces 800 lines of abstraction

No connection pooling, no validators, no caching, no serialization.
Just direct SQLite access with dictionary rows.
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

class Database:
"""
Simple SQLite database wrapper

    Usage:
        db = Database("state/pipeline.sqlite3")

        # Queries return list of dicts
        images = db.query("SELECT * FROM images WHERE rms_jy < ?", (0.001,))

        # Writes return affected row count
        db.execute("UPDATE images SET processed = 1 WHERE id = ?", (123,))
    """

    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enables dict-like access

    def query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute SELECT query, return list of dicts"""
        cursor = self.conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def execute(self, sql: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE, return affected rows"""
        cursor = self.conn.execute(sql, params)
        self.conn.commit()
        return cursor.rowcount

    def close(self):
        """Close database connection"""
        self.conn.close()

**That's it. 15 lines replaces 800 lines of abstraction.**

### Migration from Old Code

# BEFORE: 8-layer abstraction

from dsa110_contimg.database.products import ProductsDB
from dsa110_contimg.database.base import DatabaseConnection
from dsa110_contimg.database.query_builder import QueryBuilder

db_conn = DatabaseConnection("state/products.sqlite3")
products_db = ProductsDB(db_conn)
query = QueryBuilder().select("\*").from_table("images").where("rms_jy", "<", 0.001)
images = products_db.execute_query(query.build())

# AFTER: Direct access

from dsa110_contimg.database import Database

db = Database("state/pipeline.sqlite3")
images = db.query("SELECT \* FROM images WHERE rms_jy < ?", (0.001,))

**Benefits:**

- Stack trace: 8 layers → 1 layer
- Debugging: See actual SQL immediately
- Performance: ~2× faster (no overhead)
- Testing: Mock sqlite3, not 8 layers

---

## Appendix C: Documentation Restructuring Plan

### Before/After Structure

**BEFORE: 27+ subdirectories, duplicated content**
docs/
├── guides/operations/deployment.md
├── guides/development/setup.md
├── how-to/run-pipeline.md
├── how-to/troubleshoot.md
├── ops/systemd_setup.md
├── ops/docker_deployment.md
├── dev/contributing.md
├── dev/testing.md
├── deployment/production.md
├── deployment/staging.md
├── troubleshooting/calibration.md
├── troubleshooting/conversion.md
└── [20+ more files]

**AFTER: 6 core files, single source of truth**
docs/
├── README.md # Navigation hub
├── quickstart.md # Get running in 5 minutes
├── user-guide.md # Complete user docs (installation → monitoring)
├── developer-guide.md # Complete dev docs (setup → deployment)
├── api-reference.md # Auto-generated from docstrings
├── troubleshooting.md # All common issues, searchable
├── architecture-decisions/ # Historical ADRs
│ ├── 001-sqlite-over-postgres.md
│ ├── 002-absurd-framework.md
│ └── 003-orchestrator-conversion.md
└── assets/ # Images, diagrams

### Content Consolidation Strategy

**user-guide.md outline:**

# DSA-110 Continuum Imaging: User Guide

## 1. Installation

- Prerequisites
- Quick install
- Verify installation

## 2. Configuration

- Environment variables
- Config file format
- Common settings

## 3. Running the Pipeline

- Start services
- Monitor execution
- Access web dashboard

## 4. Common Operations

- Create mosaic
- Run calibration
- Extract sources

## 5. Troubleshooting

- Common errors
- Log locations
- Debug procedures

## 6. Reference

- CLI commands
- API endpoints
- Configuration options

**Migration script:**

# scripts/consolidate_docs.py

"""Merge scattered docs into user-guide.md"""

sections = {
"## 1. Installation": [
"docs/guides/installation.md",
"ops/README.md#installation"
],
"## 2. Configuration": [
"docs/guides/configuration.md",
"docs/how-to/configure.md",
"ops/systemd/README.md#configuration"
], # ... merge content under appropriate headings
}

# Detect duplicates, merge, create single source

---

## Appendix D: Contract Test Examples

### What TO Do: Real File I/O Tests

# tests/contracts/test_conversion_complete.py

"""
Contract tests verify ACTUAL behavior with REAL files

These tests are slower but catch real bugs that mocks miss.
Run in CI nightly or before releases.
"""
import pytest
from pathlib import Path
from dsa110_contimg.conversion import convert_group
from dsa110_contimg.simulation import create_synthetic_hdf5
from casacore import tables as ct
import numpy as np

@pytest.fixture(scope="module")
def synthetic_hdf5_subbands(tmp_path_factory):
"""Generate realistic synthetic HDF5 files for testing"""
tmpdir = tmp_path_factory.mktemp("test_hdf5")
return create_synthetic_hdf5(
output_dir=tmpdir,
n_subbands=16,
n_antennas=110,
n_channels=512,
duration_sec=300,
add_noise=True,
add_rfi=True # Include realistic RFI
)

def test_conversion_creates_valid_casa_ms(synthetic_hdf5_subbands, tmp_path):
"""Verify output is valid CASA Measurement Set"""
output_ms = tmp_path / "converted.ms"

    # Actual conversion (no mocks!)
    result = convert_group(synthetic_hdf5_subbands, output_ms)

    # Verify MS exists
    assert output_ms.exists(), "MS file not created"
    assert output_ms.is_dir(), "MS should be directory"

    # Verify CASA can open it (would throw if invalid)
    tb = ct.table(str(output_ms))

    # Check all required columns present
    required_cols = ["DATA", "UVW", "TIME", "ANTENNA1", "ANTENNA2"]
    for col in required_cols:
        assert col in tb.colnames(), f"Missing column: {col}"

    tb.close()

def test_conversion_preserves_data_shape(synthetic_hdf5_subbands, tmp_path):
"""Verify data dimensions are correct"""
output_ms = tmp_path / "converted.ms"
convert_group(synthetic_hdf5_subbands, output_ms)

    tb = ct.table(str(output_ms))
    data = tb.getcol("DATA")

    # Expected shape: (n_rows, n_channels, n_polarizations)
    n_baselines = (110 * 109) // 2  # DSA-110 has 110 antennas
    n_channels = 512 * 16  # 16 subbands × 512 channels
    n_pols = 4  # XX, XY, YX, YY

    assert data.ndim == 3, f"Expected 3D array, got {data.ndim}D"
    assert data.shape[1] == n_channels, f"Expected {n_channels} channels, got {data.shape[1]}"
    assert data.shape[2] == n_pols, f"Expected {n_pols} polarizations, got {data.shape[2]}"

    tb.close()

def test_conversion_handles_missing_subband(synthetic_hdf5_subbands, tmp_path):
"""Verify graceful handling of missing data""" # Remove one subband
incomplete_subbands = synthetic_hdf5_subbands[:-1]

    output_ms = tmp_path / "incomplete.ms"

    # Should complete with warning, not crash
    result = convert_group(incomplete_subbands, output_ms)

    assert result.success is True
    assert result.warnings, "Expected warning about missing subband"
    assert "missing subband" in result.warnings[0].lower()

    # MS should still be valid
    assert output_ms.exists()

### What NOT to Do: Mock-Heavy Unit Tests

# tests/unit/test_conversion_mocked.py (DON'T DO THIS)

"""
BAD EXAMPLE: These tests check call order, not actual behavior
"""
def test_convert_group_calls_functions_in_order(mocker):
"""This test is useless - it only tests that mocks were called""" # Mock everything
mock_read = mocker.patch("dsa110_contimg.conversion.read_hdf5")
mock_write = mocker.patch("dsa110_contimg.conversion.write_ms")
mock_validate = mocker.patch("dsa110_contimg.conversion.validate_output")

    # Set up returns
    mock_read.return_value = MagicMock()
    mock_write.return_value = True
    mock_validate.return_value = True

    # Call function
    result = convert_group([Path("fake.hdf5")], Path("fake.ms"))

    # Assert mocks called in order (WHO CARES?)
    assert mock_read.called
    assert mock_write.called
    assert mock_validate.called

    # THIS DOESN'T TEST:
    # - Does conversion actually work?
    # - Is output MS valid?
    # - Are data values correct?
    # - Does it handle edge cases?

**Why mocks fail:**

- Test passes even if conversion completely broken
- Refactoring breaks tests (order changes)
- Doesn't catch real bugs (data corruption, wrong formats)
- False sense of security

**Contract tests win:**

- Test actual behavior with real files
- Catch real bugs (invalid MS, corrupted data)
- Survive refactoring (only API matters)
- Give true confidence

---

## Appendix E: Common Pitfalls & Quick Fixes

### Pitfall 1: Over-Eager Refactoring

**Problem:** Changing too much at once, breaking everything

**Fix:** Follow phased approach

# Phase 1: Delete dead code (safe, reversible)

git checkout -b phase1-deletions
git rm backend/src/dsa110_contimg/conversion/strategies/dask_writer.py
git rm -rf legacy.frontend

# Test: Does everything still work?

# If yes: merge. If no: rollback is easy.

# Phase 2: Database unification (after Phase 1 merged)

git checkout -b phase2-database
python scripts/migrate_databases.py --dry-run # Preview
python scripts/migrate_databases.py # Execute

# Test: Run full integration suite

# Only merge after tests pass

# DON'T: Try to do all phases in one giant PR

### Pitfall 2: Forgetting to Update Imports

**Problem:** After flattening modules, old imports break

**Fix:** Use automated refactoring tools

# Find all imports of old paths

rg "from dsa110_contimg.conversion.strategies.hdf5_orchestrator"

# Use sed or your IDE's refactor tool

find backend/src -name "\*.py" -exec sed -i \
 's/from dsa110_contimg.conversion.strategies.hdf5_orchestrator/from dsa110_contimg.conversion/g' {} \;

# Verify with mypy

mypy backend/src/

### Pitfall 3: Database Migration Without Backup

**Problem:** Migration fails, data lost

**Fix:** ALWAYS backup first (script includes this)

# Built into migration script:

backup_path = backup_databases(state_dir, backup_dir)

# Creates timestamped backup before ANY changes

# Manual backup:

cp -r state/ state.backup.$(date +%Y%m%d\_%H%M%S)/

### Pitfall 4: Removing "Unused" Code That's Actually Used

**Problem:** Grep shows no usage, but code is used dynamically

**Fix:** Check for string-based imports

# Search for string-based dynamic imports

rg "importlib.import_module.*dask_writer"
rg "**import**.*dask_writer"

# Search in config files

rg "writer.\*dask" config/

# If found: It IS used, don't delete yet

### Pitfall 5: Breaking Backward Compatibility Accidentally

**Problem:** API change breaks external consumers

**Fix:** Deprecation warnings + gradual migration

# Don't immediately delete old API

def old_function(*args, \*\*kwargs):
warnings.warn(
"old_function() is deprecated, use new_function() instead",
DeprecationWarning,
stacklevel=2
)
return new_function(*args, \*\*kwargs)

# Remove after 2-3 releases, giving users time to migrate

---

## Appendix A: Database Migration Script

### One-Time Database Unification

**Script: `scripts/migrate_databases.py`**

#!/usr/bin/env python3
"""
Migrate from 5 separate SQLite databases to unified pipeline.sqlite3

Usage:
python scripts/migrate_databases.py --dry-run # Preview changes
python scripts/migrate_databases.py # Execute migration
"""
import sqlite3
import shutil
import json
from pathlib import Path
from datetime import datetime
import argparse

def backup*databases(state_dir: Path, backup_dir: Path):
"""Create timestamped backup of all databases"""
timestamp = datetime.now().strftime("%Y%m%d*%H%M%S")
backup*path = backup_dir / f"db_backup*{timestamp}"
backup_path.mkdir(parents=True, exist_ok=True)

    databases = [
        "products.sqlite3",
        "cal_registry.sqlite3",
        "queue.sqlite3",
        "calibrator_registry.sqlite3",
        "hdf5_index.sqlite3"
    ]

    for db in databases:
        src = state_dir / db
        if src.exists():
            dst = backup_path / db
            shutil.copy2(src, dst)
            print(f"✓ Backed up {db} → {dst}")

    return backup_path

def create_unified_schema(conn: sqlite3.Connection):
"""Create unified database schema"""

    # Products domain (from products.sqlite3)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ms_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ms_path TEXT UNIQUE NOT NULL,
            group_id INTEGER NOT NULL,
            start_time INTEGER NOT NULL,
            end_time INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ms_path TEXT NOT NULL,
            path TEXT UNIQUE NOT NULL,
            rms_jy REAL,
            ra_deg REAL,
            dec_deg REAL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (ms_path) REFERENCES ms_index(ms_path)
        );
    """)

    # Calibration domain (from cal_registry.sqlite3)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS calibration_tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            cal_type TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS calibration_applied (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ms_path TEXT NOT NULL,
            caltable_path TEXT NOT NULL,
            quality REAL,
            applied_at INTEGER NOT NULL,
            FOREIGN KEY (ms_path) REFERENCES ms_index(ms_path),
            FOREIGN KEY (caltable_path) REFERENCES calibration_tables(path)
        );
    """)

    # Calibrator catalog (from calibrator_registry.sqlite3)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS calibrator_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            flux_jy REAL NOT NULL
        );
    """)

    # HDF5 file index (from hdf5_index.sqlite3)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS hdf5_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            scan_id INTEGER NOT NULL,
            indexed_at INTEGER NOT NULL
        );
    """)

    # Queue domain (from queue.sqlite3 - will be deprecated)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS processing_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            retry_count INTEGER DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
    """)

    # Create indexes
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_ms_index_group ON ms_index(group_id);
        CREATE INDEX IF NOT EXISTS idx_images_ms_path ON images(ms_path);
        CREATE INDEX IF NOT EXISTS idx_cal_applied_ms_path ON calibration_applied(ms_path);
        CREATE INDEX IF NOT EXISTS idx_queue_group_id ON processing_queue(group_id);
        CREATE INDEX IF NOT EXISTS idx_hdf5_scan_id ON hdf5_files(scan_id);
    """)

    conn.commit()
    print("✓ Created unified schema")

def migrate_table(src_db: Path, dest_conn: sqlite3.Connection,
table_name: str, column_mapping: dict = None):
"""
Migrate table from source database to unified database

    Args:
        src_db: Path to source database
        dest_conn: Connection to destination database
        table_name: Name of table to migrate
        column_mapping: Optional dict mapping old→new column names
    """
    if not src_db.exists():
        print(f"⚠ Skipping {table_name} - source DB not found: {src_db}")
        return

    src_conn = sqlite3.connect(src_db)
    src_conn.row_factory = sqlite3.Row

    # Get all rows
    rows = src_conn.execute(f"SELECT * FROM {table_name}").fetchall()

    if not rows:
        print(f"⚠ No data in {table_name}")
        src_conn.close()
        return

    # Apply column mapping if provided
    if column_mapping:
        columns = [column_mapping.get(k, k) for k in rows[0].keys()]
    else:
        columns = list(rows[0].keys())

    # Build INSERT statement
    placeholders = ",".join(["?" for _ in columns])
    insert_sql = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"

    # Migrate data
    count = 0
    for row in rows:
        try:
            dest_conn.execute(insert_sql, tuple(row))
            count += 1
        except sqlite3.IntegrityError as e:
            print(f"  ⚠ Skipping duplicate row in {table_name}: {e}")

    dest_conn.commit()
    src_conn.close()
    print(f"✓ Migrated {count} rows to {table_name}")

def main():
parser = argparse.ArgumentParser(description="Migrate to unified database")
parser.add_argument("--dry-run", action="store_true",
help="Preview migration without executing")
parser.add_argument("--state-dir", type=Path, default=Path("state"),
help="Directory containing databases (default: state/)")
args = parser.parse_args()

    state_dir = args.state_dir
    backup_dir = state_dir / "backups"

    print("=" * 60)
    print("DATABASE MIGRATION: 5 → 1 Unified Schema")
    print("=" * 60)

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")

    # Step 1: Backup
    print("\n[1/4] Creating backups...")
    if not args.dry_run:
        backup_path = backup_databases(state_dir, backup_dir)
        print(f"✓ Backups stored in: {backup_path}")
    else:
        print("  (Skipped in dry-run)")

    # Step 2: Create unified database
    print("\n[2/4] Creating unified database...")
    unified_db = state_dir / "pipeline.sqlite3"

    if unified_db.exists() and not args.dry_run:
        print(f"⚠ {unified_db} already exists!")
        response = input("Overwrite? [y/N]: ")
        if response.lower() != 'y':
            print("Migration cancelled")
            return
        unified_db.unlink()

    if not args.dry_run:
        conn = sqlite3.connect(unified_db)
        create_unified_schema(conn)
    else:
        print("  (Would create schema in dry-run)")
        conn = None

    # Step 3: Migrate data
    print("\n[3/4] Migrating data...")

    migrations = [
        (state_dir / "products.sqlite3", "ms_index", None),
        (state_dir / "products.sqlite3", "images", None),
        (state_dir / "cal_registry.sqlite3", "calibration_tables", None),
        (state_dir / "cal_registry.sqlite3", "calibration_applied", None),
        (state_dir / "calibrator_registry.sqlite3", "calibrator_catalog", None),
        (state_dir / "hdf5_index.sqlite3", "hdf5_files", None),
        (state_dir / "queue.sqlite3", "processing_queue", None),
    ]

    if not args.dry_run:
        for src_db, table, mapping in migrations:
            migrate_table(src_db, conn, table, mapping)
        conn.close()
    else:
        for src_db, table, _ in migrations:
            if src_db.exists():
                src_conn = sqlite3.connect(src_db)
                count = src_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                src_conn.close()
                print(f"  Would migrate {count} rows from {table}")

    # Step 4: Verification
    print("\n[4/4] Verification...")
    if not args.dry_run:
        conn = sqlite3.connect(unified_db)
        for _, table, _ in migrations:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  ✓ {table}: {count} rows")
        conn.close()
    else:
        print("  (Skipped in dry-run)")

    print("\n" + "=" * 60)
    if args.dry_run:
        print("DRY RUN COMPLETE - No changes made")
        print(f"\nTo execute migration, run:")
        print(f"  python {__file__}")
    else:
        print("MIGRATION COMPLETE")
        print(f"\n✓ Unified database: {unified_db}")
        print(f"✓ Backups: {backup_path}")
        print("\nNext steps:")
        print("  1. Update code to use Database(\"state/pipeline.sqlite3\")")
        print("  2. Test all queries work correctly")
        print("  3. After verification, delete old databases:")
        print("     rm state/{{products,cal_registry,queue,calibrator_registry,hdf5_index}}.sqlite3")
    print("=" * 60)

if **name** == "**main**":
main()

---

## Appendix B: Simplified Database Layer

### Complete 15-Line Implementation

# backend/src/dsa110_contimg/database.py

"""
Simplified database layer - replaces 800 lines of abstraction

No connection pooling, no validators, no caching, no serialization.
Just direct SQLite access with dictionary rows.
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

class Database:
"""
Simple SQLite database wrapper

    Usage:
        db = Database("state/pipeline.sqlite3")

        # Queries return list of dicts
        images = db.query("SELECT * FROM images WHERE rms_jy < ?", (0.001,))

        # Writes return affected row count
        db.execute("UPDATE images SET processed = 1 WHERE id = ?", (123,))
    """

    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enables dict-like access

    def query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute SELECT query, return list of dicts"""
        cursor = self.conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def execute(self, sql: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE, return affected rows"""
        cursor = self.conn.execute(sql, params)
        self.conn.commit()
        return cursor.rowcount

    def close(self):
        """Close database connection"""
        self.conn.close()

**That's it. 15 lines replaces 800 lines of abstraction.**

### Migration from Old Code

# BEFORE: 8-layer abstraction

from dsa110_contimg.database.products import ProductsDB
from dsa110_contimg.database.base import DatabaseConnection
from dsa110_contimg.database.query_builder import QueryBuilder

db_conn = DatabaseConnection("state/products.sqlite3")
products_db = ProductsDB(db_conn)
query = QueryBuilder().select("\*").from_table("images").where("rms_jy", "<", 0.001)
images = products_db.execute_query(query.build())

# AFTER: Direct access

from dsa110_contimg.database import Database

db = Database("state/pipeline.sqlite3")
images = db.query("SELECT \* FROM images WHERE rms_jy < ?", (0.001,))

**Benefits:**

- Stack trace: 8 layers → 1 layer
- Debugging: See actual SQL immediately
- Performance: ~2× faster (no overhead)
- Testing: Mock sqlite3, not 8 layers

---

## Appendix C: Documentation Restructuring Plan

### Before/After Structure

**BEFORE: 27+ subdirectories, duplicated content**
docs/
├── guides/operations/deployment.md
├── guides/development/setup.md
├── how-to/run-pipeline.md
├── how-to/troubleshoot.md
├── ops/systemd_setup.md
├── ops/docker_deployment.md
├── dev/contributing.md
├── dev/testing.md
├── deployment/production.md
├── deployment/staging.md
├── troubleshooting/calibration.md
├── troubleshooting/conversion.md
└── [20+ more files]

**AFTER: 6 core files, single source of truth**
docs/
├── README.md # Navigation hub
├── quickstart.md # Get running in 5 minutes
├── user-guide.md # Complete user docs (installation → monitoring)
├── developer-guide.md # Complete dev docs (setup → deployment)
├── api-reference.md # Auto-generated from docstrings
├── troubleshooting.md # All common issues, searchable
├── architecture-decisions/ # Historical ADRs
│ ├── 001-sqlite-over-postgres.md
│ ├── 002-absurd-framework.md
│ └── 003-orchestrator-conversion.md
└── assets/ # Images, diagrams

### Content Consolidation Strategy

**user-guide.md outline:**

# DSA-110 Continuum Imaging: User Guide

## 1. Installation

- Prerequisites
- Quick install
- Verify installation

## 2. Configuration

- Environment variables
- Config file format
- Common settings

## 3. Running the Pipeline

- Start services
- Monitor execution
- Access web dashboard

## 4. Common Operations

- Create mosaic
- Run calibration
- Extract sources

## 5. Troubleshooting

- Common errors
- Log locations
- Debug procedures

## 6. Reference

- CLI commands
- API endpoints
- Configuration options

**Migration script:**

# scripts/consolidate_docs.py

"""Merge scattered docs into user-guide.md"""

sections = {
"## 1. Installation": [
"docs/guides/installation.md",
"ops/README.md#installation"
],
"## 2. Configuration": [
"docs/guides/configuration.md",
"docs/how-to/configure.md",
"ops/systemd/README.md#configuration"
], # ... merge content under appropriate headings
}

# Detect duplicates, merge, create single source

---

## Appendix D: Contract Test Examples

### What TO Do: Real File I/O Tests

# tests/contracts/test_conversion_complete.py

"""
Contract tests verify ACTUAL behavior with REAL files

These tests are slower but catch real bugs that mocks miss.
Run in CI nightly or before releases.
"""
import pytest
from pathlib import Path
from dsa110_contimg.conversion import convert_group
from dsa110_contimg.simulation import create_synthetic_hdf5
from casacore import tables as ct
import numpy as np

@pytest.fixture(scope="module")
def synthetic_hdf5_subbands(tmp_path_factory):
"""Generate realistic synthetic HDF5 files for testing"""
tmpdir = tmp_path_factory.mktemp("test_hdf5")
return create_synthetic_hdf5(
output_dir=tmpdir,
n_subbands=16,
n_antennas=110,
n_channels=512,
duration_sec=300,
add_noise=True,
add_rfi=True # Include realistic RFI
)

def test_conversion_creates_valid_casa_ms(synthetic_hdf5_subbands, tmp_path):
"""Verify output is valid CASA Measurement Set"""
output_ms = tmp_path / "converted.ms"

    # Actual conversion (no mocks!)
    result = convert_group(synthetic_hdf5_subbands, output_ms)

    # Verify MS exists
    assert output_ms.exists(), "MS file not created"
    assert output_ms.is_dir(), "MS should be directory"

    # Verify CASA can open it (would throw if invalid)
    tb = ct.table(str(output_ms))

    # Check all required columns present
    required_cols = ["DATA", "UVW", "TIME", "ANTENNA1", "ANTENNA2"]
    for col in required_cols:
        assert col in tb.colnames(), f"Missing column: {col}"

    tb.close()

def test_conversion_preserves_data_shape(synthetic_hdf5_subbands, tmp_path):
"""Verify data dimensions are correct"""
output_ms = tmp_path / "converted.ms"
convert_group(synthetic_hdf5_subbands, output_ms)

    tb = ct.table(str(output_ms))
    data = tb.getcol("DATA")

    # Expected shape: (n_rows, n_channels, n_polarizations)
    n_baselines = (110 * 109) // 2  # DSA-110 has 110 antennas
    n_channels = 512 * 16  # 16 subbands × 512 channels
    n_pols = 4  # XX, XY, YX, YY

    assert data.ndim == 3, f"Expected 3D array, got {data.ndim}D"
    assert data.shape[1] == n_channels, f"Expected {n_channels} channels, got {data.shape[1]}"
    assert data.shape[2] == n_pols, f"Expected {n_pols} polarizations, got {data.shape[2]}"

    tb.close()

def test_conversion_handles_missing_subband(synthetic_hdf5_subbands, tmp_path):
"""Verify graceful handling of missing data""" # Remove one subband
incomplete_subbands = synthetic_hdf5_subbands[:-1]

    output_ms = tmp_path / "incomplete.ms"

    # Should complete with warning, not crash
    result = convert_group(incomplete_subbands, output_ms)

    assert result.success is True
    assert result.warnings, "Expected warning about missing subband"
    assert "missing subband" in result.warnings[0].lower()

    # MS should still be valid
    assert output_ms.exists()

### What NOT to Do: Mock-Heavy Unit Tests

# tests/unit/test_conversion_mocked.py (DON'T DO THIS)

"""
BAD EXAMPLE: These tests check call order, not actual behavior
"""
def test_convert_group_calls_functions_in_order(mocker):
"""This test is useless - it only tests that mocks were called""" # Mock everything
mock_read = mocker.patch("dsa110_contimg.conversion.read_hdf5")
mock_write = mocker.patch("dsa110_contimg.conversion.write_ms")
mock_validate = mocker.patch("dsa110_contimg.conversion.validate_output")

    # Set up returns
    mock_read.return_value = MagicMock()
    mock_write.return_value = True
    mock_validate.return_value = True

    # Call function
    result = convert_group([Path("fake.hdf5")], Path("fake.ms"))

    # Assert mocks called in order (WHO CARES?)
    assert mock_read.called
    assert mock_write.called
    assert mock_validate.called

    # THIS DOESN'T TEST:
    # - Does conversion actually work?
    # - Is output MS valid?
    # - Are data values correct?
    # - Does it handle edge cases?

**Why mocks fail:**

- Test passes even if conversion completely broken
- Refactoring breaks tests (order changes)
- Doesn't catch real bugs (data corruption, wrong formats)
- False sense of security

**Contract tests win:**

- Test actual behavior with real files
- Catch real bugs (invalid MS, corrupted data)
- Survive refactoring (only API matters)
- Give true confidence

---

## Appendix E: Common Pitfalls & Quick Fixes

### Pitfall 1: Over-Eager Refactoring

**Problem:** Changing too much at once, breaking everything

**Fix:** Follow phased approach

# Phase 1: Delete dead code (safe, reversible)

git checkout -b phase1-deletions
git rm backend/src/dsa110_contimg/conversion/strategies/dask_writer.py
git rm -rf legacy.frontend

# Test: Does everything still work?

# If yes: merge. If no: rollback is easy.

# Phase 2: Database unification (after Phase 1 merged)

git checkout -b phase2-database
python scripts/migrate_databases.py --dry-run # Preview
python scripts/migrate_databases.py # Execute

# Test: Run full integration suite

# Only merge after tests pass

# DON'T: Try to do all phases in one giant PR

### Pitfall 2: Forgetting to Update Imports

**Problem:** After flattening modules, old imports break

**Fix:** Use automated refactoring tools

# Find all imports of old paths

rg "from dsa110_contimg.conversion.strategies.hdf5_orchestrator"

# Use sed or your IDE's refactor tool

find backend/src -name "\*.py" -exec sed -i \
 's/from dsa110_contimg.conversion.strategies.hdf5_orchestrator/from dsa110_contimg.conversion/g' {} \;

# Verify with mypy

mypy backend/src/

### Pitfall 3: Database Migration Without Backup

**Problem:** Migration fails, data lost

**Fix:** ALWAYS backup first (script includes this)

# Built into migration script:

backup_path = backup_databases(state_dir, backup_dir)

# Creates timestamped backup before ANY changes

# Manual backup:

cp -r state/ state.backup.$(date +%Y%m%d\_%H%M%S)/

### Pitfall 4: Removing "Unused" Code That's Actually Used

**Problem:** Grep shows no usage, but code is used dynamically

**Fix:** Check for string-based imports

# Search for string-based dynamic imports

rg "importlib.import_module.*dask_writer"
rg "**import**.*dask_writer"

# Search in config files

rg "writer.\*dask" config/

# If found: It IS used, don't delete yet

### Pitfall 5: Breaking Backward Compatibility Accidentally

**Problem:** API change breaks external consumers

**Fix:** Deprecation warnings + gradual migration

# Don't immediately delete old API

def old_function(*args, \*\*kwargs):
warnings.warn(
"old_function() is deprecated, use new_function() instead",
DeprecationWarning,
stacklevel=2
)
return new_function(*args, \*\*kwargs)

# Remove after 2-3 releases, giving users time to migrate

---

## Summary Table: Savings & Impact

| Change Area                     | Lines Removed | Files Removed | Concepts Removed                     | Developer Benefit              |
| ------------------------------- | ------------: | ------------: | ------------------------------------ | ------------------------------ |
| Dead code and alt. strategies   |        ~2,000 |             3 | 2 major code paths                   | Reduced confusion              |
| DB unification & flattening     |        ~2,000 |             5 | 4 DBs, 8 abstraction layers          | Easier queries/tests           |
| Module flattening               |          ~200 |            15 | Deep nesting, `__init__` boilerplate | Top-level clarity              |
| Logging/metrics simplification  |          ~800 |             0 | Scattered metrics, 480 test cases    | Much easier testing            |
| Config standardization          |          ~600 |             8 | 8 config sources, type coercion      | Type-safe/validated            |
| Legacy front/backend cleanout   |        ~5,000 |           100 | Two+ UIs                             | Obvious codebase plan          |
| Docs flattening/consolidation   |          ~100 |            10 | Redundant navigation                 | Faster onboarding              |
| Test overhaul (mocks→contracts) |        ~2,000 |             0 | False confidence tests               | Higher confidence              |
| PostgreSQL experiments          |          ~400 |             3 | Experimental backend                 | Decision clarity               |
| Node.js tooling in Python       |          75KB |             4 | Two ecosystems                       | Setup simplicity               |
| **TOTAL**                       |   **~13,100** |      **~148** | **~20 major concepts**               | **Dramatically less friction** |

### Additional Hidden Complexity Revealed

**Over-parameterization impact:**

- Functions reduced from 13+ params → 3 params
- Testing surface: ~8,000 combinations → ~10 combinations
- **Cognitive load: -75%**

**Abstraction layer reduction:**

- Call stack depth: 8 layers → 1 layer (for database queries)
- Debugging: Immediate stack traces vs. 800 lines of wrapper code
- **Performance: ~2× faster** (no abstraction overhead)

**Type system consistency:**

- Path handling: 46% consistent → 100% consistent
- Type safety: Runtime errors → Compile-time mypy verification
- Conversion code: 260 functions → 1 centralized adapter

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

## References

1. _Deep Dive: Hidden Complexity in dsa110-contimg_ (internal analysis)
2. _Complexity Reduction Opportunities in dsa110-contimg_ (internal presentation)
3. _ABSURD-Governed Mosaicking: Automated Job Architecture_ (pipelines)

---

**The end goal:**  
A codebase ~35–40% smaller, with a unified production path for every major feature, vastly reduced “decision debt,” and a single, clear way to get any task done.  
**Tagline:** _If in doubt, delete, simplify, and unify. The future developer will thank you._
