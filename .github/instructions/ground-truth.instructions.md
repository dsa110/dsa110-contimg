---
description: Ground truth hierarchy - code over docs, data over assumptions
applyTo: '**'
---

# Ground Truth Hierarchy

When working on this codebase, follow this hierarchy of truth:

## 1. Running Code > Documentation

- **Code is truth, docs are intent**
- If docs say X but code does Y, the code is correct (docs may be outdated or aspirational)
- Design docs like `COMPLEXITY_REDUCTION.md` describe the FUTURE, not the present
- Always verify claims by reading actual source files

## 2. Existing Data > Assumptions

Before any operation:

```bash
# What's actually in the database?
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 ".tables"
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 ".schema <table>"

# How much data exists?
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 "SELECT COUNT(*) FROM <table>"
```

## 3. One Before Many

- Test with 1 file before processing 1000
- Test with 1 record before migrating a table
- Get one working example before generalizing

## 4. System Status Awareness

| System           | Status           | Database                      |
| ---------------- | ---------------- | ----------------------------- |
| pipeline.sqlite3 | **PRODUCTION**   | SQLite                        |
| hdf5_file_index  | **PRODUCTION**   | SQLite (/data/incoming/)      |
| batch conversion | **PRODUCTION**   | Uses hdf5_file_index          |
| ABSURD ingestion | **EXPERIMENTAL** | PostgreSQL + pipeline.sqlite3 |

When in doubt about a subsystem's status, check:

1. Is there a systemd service for it in `ops/systemd/`?
2. Is it referenced in production configs in `ops/`?
3. Does it have data in production paths?

## 5. Question Design Doc Claims

When `COMPLEXITY_REDUCTION.md` or other design docs say something:

- Check if it's implemented yet
- Look for actual code that does what the doc describes
- If no code exists, it's a plan, not reality
