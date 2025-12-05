---
description: Query existing data before writing code that operates on it
applyTo: "**"
---

# Data-First Principle

1) Stop and verify what system/table/files exist and whether you are reusing data or creating new. If ambiguous, ask.
2) Query first (read-only):
   - `sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 ".tables"`
   - `sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 ".schema <table>"`
   - `ls <dir> | head -5`, `find <path> -name "*.ext" | wc -l`
3) Check scale before scanning; if counts > 1000 (files or rows), rethink.
4) Follow the data model: query the DB/index instead of scanning the filesystem; do not repopulate when data exists.
5) Read-only first: `SELECT` / `count()` / `get()` to validate shape; only then write.
6) Test with one record/file first (e.g., `sqlite3 db.sqlite3 "SELECT id FROM table LIMIT 1"`), not the whole set.
