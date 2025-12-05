---
description: Query existing data before writing code that operates on it
applyTo: "**"
---

# Data-First Principle

Before writing any code that reads, processes, or tests data:

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
