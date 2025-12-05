---
description: Domain invariants and constants for DSA-110 continuum imaging
applyTo: "**"
---

# Domain Invariants

- **Subbands**: Every observation group has 16 subbands (`sb00`-`sb15`). Never process a single subband alone.
- **Grouping**:
  - Preferred: exact `group_id` after normalization (streaming converter renames jittered files).
  - Legacy: cluster within ±60 seconds tolerance when files are unnormalized.
- **File patterns**: `YYYY-MM-DDTHH:MM:SS_sbXX.hdf5`
- **Active codebase**: Use `backend/src/dsa110_contimg/` (not legacy paths).
- **Databases**:
  - Pipeline SQLite at `/data/dsa110-contimg/state/db/pipeline.sqlite3` is production.
  - Catalog SQLite DBs live in `/data/dsa110-contimg/state/catalogs/`; use existing indexes before filesystem scans.
  - ABSURD uses PostgreSQL (`dsa110_absurd`) and is labeled EXPERIMENTAL.
- **Storage**:
  - `/data` = HDD, production data (slow; avoid heavy I/O)
  - `/stage` = NVMe for outputs and working data
  - `/scratch` = NVMe for temp/builds
  - `/dev/shm` = tmpfs for in-memory staging
- **CASA/pyuvdata compatibility**:
  - CASA 6.7, Python 3.11, pyuvdata 3.2.4
  - Use `Nants_telescope`, not deprecated `Nants_data`; set `strict_uvw_antpos_check=False`
- **Antenna positions**: Always use `dsa110_contimg.utils.antpos_local.get_itrf()` (ITRF meters). Do not hardcode.
- **Field naming**: Default 24 fields `meridian_icrs_t0..t23`; auto-renamed to calibrators when detected.
- **MS writing**: Use direct/parallel subband writers (`conversion/strategies/writers.py`); `pyuvdata` writer is test-only.
- **Environments**: Activate `casa6` for backend; Node 22+ for frontend.
- **Safety**: Treat `pipeline.sqlite3` and streaming converter state as production; avoid destructive operations.

