---
description: Ground truth hierarchy - code over docs, data over assumptions
applyTo: '**'
---

# Ground Truth Hierarchy

1. Code beats docs. Treat docs as intent; design docs (e.g., `COMPLEXITY_REDUCTION.md`) describe the future. Trust the source files.
2. Data beats assumptions. Check production SQLite before acting:
   - `sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 ".tables"`
   - `sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 ".schema <table>"`
   - `sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 "SELECT COUNT(*) FROM <table>"`
3. One before many. Prove it on one file/record before scaling.
4. Know system status. `pipeline.sqlite3`, `hdf5_file_index`, batch conversion = **PRODUCTION**; ABSURD ingestion = **EXPERIMENTAL**. If unsure, check `ops/systemd/`, production configs in `ops/`, and whether data exists in production paths.
5. Question design claims. Only believe what's implemented; if no code does it, it's a plan.

## Before Documenting Infrastructure/Services

Always verify against live system first:

- [ ] **Filesystem check**: Does the file/service actually exist?
  ```bash
  find . -name "*pattern*" -type f
  ls -la /path/to/thing
  ```
- [ ] **Recognize systemd templates**: If filename has `@` (e.g., `service@.service`), it's a template that requires an instance parameter

  ```bash
  systemctl list-units --state=running | grep <keyword>
  # Document the actual running instance (e.g., service@1), not the template
  ```

- [ ] **Test the command**: Run what you're about to document

  ```bash
  systemctl status dsa110-absurd-worker@1  # Actually works?
  curl http://localhost:8000/api/status    # Response valid?
  ```

- [ ] **Cross-reference live state**: Compare docs claim vs actual running system
  ```bash
  ps aux | grep <process>
  netstat -tlnp | grep <port>
  systemctl show <service> --no-pager
  ```

Example pattern that catches errors:

```bash
# Before documenting a service, run this checklist:
find ops/systemd -name "*absurd*"           # See actual filenames
systemctl list-units --all | grep absurd    # See actual running instances
systemctl status dsa110-absurd-worker@1     # Verify the command works
# Only then document: dsa110-absurd-worker@1 (not just dsa110-absurd-worker)
```

**Why this matters**: The filesystem and running system are ground truth. A `@` symbol in a filename is literal syntax, not decoration.
