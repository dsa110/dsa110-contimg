---
description: Security, data handling, and operational safety
applyTo: "**"
---

# Security and Data Handling

- **Databases**: Use SQLite only (unless ABSURD PostgreSQL explicitly). Keep DBs in `state/db/` or `state/catalogs/`. No ad-hoc CSV/TXT stores.
- **Production data**: `pipeline.sqlite3` and streaming state are production—read-only unless change is intentional and reviewed.
- **Paths**: Do not create new top-level directories; respect `/data`, `/stage`, `/scratch`, `/dev/shm` roles.
- **Secrets**: Do not hardcode credentials; prefer env vars or configs in `ops/`. Avoid logging secrets or PII (none expected).
- **Network**: Use local resources and DocSearch; avoid external calls unless required and approved.
- **Validation**: Validate inputs (filenames, group IDs, DB params). Reject invalid subband filenames early.
- **Error handling**: Use structured logging and explicit error codes. Avoid silent excepts; raise or return clear errors.
- **Migrations**: Back up DBs before schema changes; prefer additive migrations. Confirm counts before/after.
- **Catalogs**: Keep catalog rebuild sources in `state/catalogs/sources/`; outputs in `state/catalogs/`.
- **Downloads/build artifacts**: Use scratch storage; clean up temp files.

