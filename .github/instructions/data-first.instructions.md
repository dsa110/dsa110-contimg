---
description: Query existing data before writing code that operates on it
applyTo: "**"
---

# Data-First Principle

Before writing any code that reads, processes, or tests data:

## 0. STOP AND VERIFY (Mandatory Checkpoint)

**Before taking ANY action**, state:
1. What existing system/database will I use?
2. What table/file structure already exists?
3. Am I building something new, or using something that exists?

If you cannot answer these from memory, QUERY FIRST:

```bash
# For database tasks
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 ".tables"
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 ".schema <relevant_table>"

# For file tasks  
ls <target_directory> | head -5
find <path> -name "*.ext" | wc -l
```

**If the user's request is ambiguous** (e.g., could use multiple systems), ASK which one they mean before proceeding.

## 1. Query Existing State First

```bash
# Check what tables/collections exist
sqlite3 /path/to/db.sqlite3 ".tables"

# Check record counts and states
sqlite3 /path/to/db.sqlite3 "SELECT state, COUNT(*) FROM <table> GROUP BY state"
```

Do NOT assume the database is empty or that you need to populate it.

## 2. Check Scale Before Scanning

Before calling any method that scans directories or iterates collections:

```bash
# How many files?
find /path -name "*.ext" | wc -l

# How many records?
sqlite3 db.sqlite3 "SELECT COUNT(*) FROM table"
```

If the count is > 1000, reconsider the approach.

## 3. Follow the Data Model

Ask: "Where does this data live?" BEFORE "How do I get this data?"

- If there's a database, query it directly
- Don't scan filesystems when an index exists
- Don't bootstrap/populate when data already exists

## 4. Use Read-Only Operations First

When testing or exploring:

1. `SELECT` / `count()` / `get()` first
2. Verify the data looks correct
3. Only then consider write operations

## 5. Pick ONE Record to Test

For smoke tests, find a specific record:

```bash
sqlite3 db.sqlite3 "SELECT id FROM table WHERE state='ready' LIMIT 1"
```

Then test with that ONE record, not the entire dataset.
