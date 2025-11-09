---
title: Mosaic Quickstart
status: draft
owner: @docs-team
audience: user
last_updated: 2025-01-15
tags: [how-to, mosaic]
related:
  - concepts/STREAMING_MOSAIC_WORKFLOW.md
  - concepts/pipeline_workflow_visualization.md
  - how-to/mosaic.md
  - reference/cli.md
  - reference/database_schema.md
---

# Mosaic Quickstart

Create a basic sky mosaic from pipeline tiles in minutes.

## Overview
This guide shows the minimal steps to plan and build a mosaic from 5‑minute, primary‑beam‑corrected tiles already indexed in the products database. It complements the full guide in [Mosaic (How‑To)](mosaic.md) and the conceptual background in [Streaming Mosaic Workflow](../concepts/STREAMING_MOSAIC_WORKFLOW.md).

## Prerequisites
- Run commands from the repo root (so `python -m dsa110_contimg...` resolves), or install the package with `pip install -e .`.
- Pipeline has produced tiles and populated `state/products.sqlite3` (`images` table).
- Sufficient disk space for the output mosaic directory.
- Optional (recommended for metrics and CASA image output): a working CASA6 environment. See [CASA6 Environment Guide](../CASA6_ENVIRONMENT_GUIDE.md). If using conda: `conda activate casa6`.

## Steps

### 1) Pick a time window and a name
Choose the UTC window you want to mosaic and a name for the run.

Examples (bash; adjust dates):
```bash
SINCE=$(date -u -d '2025-01-15 00:00:00' +%s)
UNTIL=$(date -u -d '2025-01-16 00:00:00' +%s)
NAME=night_20250115
```

Tip: List recent tile rows to gauge availability:
```bash
sqlite3 state/products.sqlite3 "select datetime(created_at,'unixepoch'), path, pbcor from images order by created_at desc limit 10;"
```

### 2) Plan the mosaic
Record a plan (tile list) into the `mosaics` table. By default, only PB‑corrected tiles (`pbcor=1`) are included.

Choose a combination method:
- `mean` (default): simple average, robust when PB images are unavailable
- `weighted`: noise‑weighted (does not require PB images)
- `pbweighted`: primary‑beam‑weighted (requires PB images alongside tiles)

```bash
# Simple and robust (recommended if unsure):
python -m dsa110_contimg.mosaic.cli plan \
  --products-db state/products.sqlite3 \
  --name "$NAME" \
  --since "$SINCE" \
  --until "$UNTIL"

# Or, prefer weighting explicitly:
# Noise‑weighted
python -m dsa110_contimg.mosaic.cli plan \
  --products-db state/products.sqlite3 \
  --name "$NAME" \
  --since "$SINCE" \
  --until "$UNTIL" \
  --method weighted

# PB‑weighted (requires PB images)
python -m dsa110_contimg.mosaic.cli plan \
  --products-db state/products.sqlite3 \
  --name "$NAME" \
  --since "$SINCE" \
  --until "$UNTIL" \
  --method pbweighted
```

Notes:
- Add `--include-unpbcor` to include tiles without PB correction (not recommended for science products).
- The command prints how many tiles were found and saves the plan with the chosen method.

### 3) Build the mosaic
Combine the planned tiles into a single mosaic image. Choose an output path in your mosaics directory.

```bash
OUTDIR=/data/ms/mosaics
mkdir -p "$OUTDIR"

# Use a base path (no extension). FITS export will write ${NAME}.fits when CASA is available.
python -m dsa110_contimg.mosaic.cli build \
  --products-db state/products.sqlite3 \
  --name "$NAME" \
  --output "$OUTDIR/${NAME}"

# Optional: validate without building (measure twice)
python -m dsa110_contimg.mosaic.cli build \
  --products-db state/products.sqlite3 \
  --name "$NAME" \
  --output "$OUTDIR/${NAME}" \
  --dry-run
```

Notes:
- With CASA available, the builder uses CASA image math and can emit CASA images and optional FITS exports; without CASA, metrics and some image operations may be skipped.
- The builder validates pre‑conditions and tile quality before combining; fix issues or use `--ignore-validation` cautiously during experimentation.

## Validation
Confirm a mosaic was created and its plan recorded:

```bash
ls -1 "$OUTDIR/${NAME}"*

sqlite3 state/products.sqlite3 \
  "select name, status, substr(tiles,1,80)||'...' as tiles_prefix, datetime(created_at,'unixepoch') \
   from mosaics order by created_at desc limit 3;"
```

If FITS export was enabled, view it in your preferred FITS viewer. For CASA images, use `imhead` & `imstat` to inspect headers and basic stats.

## Troubleshooting
- No tiles found
  - Check your time window; inspect `images.created_at` and `images.pbcor` values.
  - Re‑run plan with `--include-unpbcor` if PB‑corrected tiles are not yet available.
- Pre‑flight complains about missing PB images
  - Use `--method mean` (or re‑plan with that method) if PB images are not present.
  - For noise‑weighted builds, you can proceed with `--method weighted`; if pre‑flight still requires PB, use `--ignore-validation` (development only).
  - For PB‑weighted builds, ensure PB images exist alongside tiles.
- Grid mismatch errors
  - Ensure tiles are produced by the same imaging configuration (cell size, image shape). See the detailed [Mosaic How‑To](mosaic.md).
- Missing CASA tools
  - Some metrics or operations may be skipped without CASA; see [CASA6 Environment Guide](../CASA6_ENVIRONMENT_GUIDE.md) to enable full functionality.

## See Also
- Concept: [Streaming Mosaic Workflow](../concepts/STREAMING_MOSAIC_WORKFLOW.md)
- Concept: [Pipeline Workflow Visualization](../concepts/pipeline_workflow_visualization.md)
- How‑To: [Mosaic (detailed)](mosaic.md)
- Reference: [CLI](../reference/cli.md), [Database Schema](../reference/database_schema.md)
