# Database Path Migration Plan

Move any remaining SQLite references from `/stage/dsa110-contimg/state/` to
`/data/dsa110-contimg/state/` and ensure code uses env-configurable paths.

## Current Hardcoded References (primary)

- `scripts/ops/imaging/milestone1_pipeline.py` – `state_dir=Path("/stage/dsa110-contimg/state")`
- `scripts/ops/imaging/milestone1_60min_mosaic.py` – `PRODUCTS_DB = Path("/stage/dsa110-contimg/state/db/products.sqlite3")`
- `scripts/ops/imaging/milestone1_60min_mosaic.py` – `CAL_REGISTRY_DB = Path("/stage/dsa110-contimg/state/db/cal_registry.sqlite3")`
- `backend/src/dsa110_contimg/scripts/ops/cleanup_unused_stage_dirs.py` – docs mention duplicate state dir

Other `/stage/...` occurrences are mostly data paths (MS/images) rather than DB
state; keep them separate from the DB migration work.

## Migration Steps

1. **Pre-checks**
   - Stop pipeline services (systemd/docker) to quiesce DB writes.
   - Confirm target dir exists: `/data/dsa110-contimg/state`.
2. **Copy + verify**
   - `rsync -av --progress /stage/dsa110-contimg/state/ /data/dsa110-contimg/state/`
   - Verify file counts and checksums (e.g., `find ... -name '*.sqlite3' -print0 | xargs -0 sha256sum` on both).
3. **Update configuration (env-first)**
   - Set `PIPELINE_STATE_DIR=/data/dsa110-contimg/state`
   - Set `PIPELINE_QUEUE_DB=/data/dsa110-contimg/state/ingest.sqlite3`
   - Set `PIPELINE_PRODUCTS_DB=/data/dsa110-contimg/state/products.sqlite3`
   - Set `CAL_REGISTRY_DB=/data/dsa110-contimg/state/cal_registry.sqlite3`
   - For legacy scripts, also set `CATALOG_DB_DIR=/data/dsa110-contimg/state/catalogs`
   - Update `ops/systemd/contimg.env` to match (queue/products/registry vars).
4. **Code touch-up (post-env)**
   - Swap hardcoded `/stage/dsa110-contimg/state` in milestone imaging scripts
     for `Path(os.getenv("PIPELINE_STATE_DIR", "/data/dsa110-contimg/state"))`.
   - Add optional `PIPELINE_PRODUCTS_DB`/`CAL_REGISTRY_DB` overrides in those
     scripts for direct DB references.
   - Drop stale references in `cleanup_unused_stage_dirs.py` once migration is
     complete.
5. **Rollout**
   - Restart services; watch logs for path errors.
   - Remove or archive old `/stage/.../state` after a backup window.

> Pending host actions (Ops required):
> - `sudo systemctl daemon-reload && sudo systemctl restart contimg-stream.service contimg-api.service`
> - `sudo systemctl enable --now data-retention-cleanup.timer`
> - If notification secrets change in `ops/systemd/contimg.env`, rerun daemon-reload + service restarts

## Quick Commands

```bash
# Inventory any remaining state DB references
rg -n "/stage/dsa110-contimg/state" scripts backend ops

# Dry-run rsync preview
rsync -avn /stage/dsa110-contimg/state/ /data/dsa110-contimg/state/

# Verify env wiring in systemd
grep -n "PIPELINE_.*DB" ops/systemd/contimg.env
```
