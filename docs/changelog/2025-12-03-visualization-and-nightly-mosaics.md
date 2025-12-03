# 2025-12-03: Visualization Module & Nightly Mosaic Infrastructure

## Summary

Added a consolidated visualization module for pipeline diagnostics and created
infrastructure for automated nightly mosaics.

## Changes

### Visualization Module (`backend/src/dsa110_contimg/visualization/`)

New consolidated module providing standardized plotting and reporting across the
pipeline. Replaces scattered plotting code with a unified interface.

**Files created:**

| File                   | Lines | Purpose                                   |
| ---------------------- | ----- | ----------------------------------------- |
| `__init__.py`          | 90    | Module exports                            |
| `config.py`            | 161   | `FigureConfig`, `PlotStyle` configuration |
| `fits_plots.py`        | 512   | FITS image plotting with WCS support      |
| `calibration_plots.py` | 536   | Bandpass, gains, delays, dynamic spectra  |
| `source_plots.py`      | 373   | Lightcurves, spectra, source comparisons  |
| `mosaic_plots.py`      | 307   | Tile grids, footprints, coverage maps     |
| `report.py`            | 451   | HTML/PDF report generation                |

**Key features:**

- Three style presets: `QUICKLOOK` (fast), `PUBLICATION` (high-quality), `PRESENTATION`
- Configurable DPI, figure size, colormaps, fonts
- WCS-aware plotting with coordinate overlays
- Automatic colorbar scaling and labeling
- HTML report generation with embedded figures
- PDF export via WeasyPrint (optional)

**Tests:** 12 unit tests in `backend/tests/unit/visualization/test_visualization.py`

### Documentation

- **`docs/guides/visualization.md`** (~380 lines) - Comprehensive guide covering:

  - Quick start examples
  - Configuration options
  - FITS image plotting
  - Calibration diagnostics
  - Source analysis plots
  - Mosaic visualizations
  - Report generation

- Added to `mkdocs.yml` navigation under Guides → Workflow

### Nightly Mosaic Infrastructure

Created systemd service and timer for automated nightly mosaics (not yet enabled).

**Files created:**

| File                                            | Purpose                         |
| ----------------------------------------------- | ------------------------------- |
| `ops/systemd/contimg-mosaic-nightly.service`    | Oneshot service to run pipeline |
| `ops/systemd/contimg-mosaic-nightly.timer`      | Timer for 03:00 UTC daily       |
| `backend/src/dsa110_contimg/mosaic/__main__.py` | CLI entry point                 |

**CLI commands:**

```bash
# Run nightly mosaic (processes previous 24 hours)
python -m dsa110_contimg.mosaic nightly

# Run for specific date
python -m dsa110_contimg.mosaic nightly --date 2025-01-15

# Dry run (preview only)
python -m dsa110_contimg.mosaic nightly --dry-run

# Check status
python -m dsa110_contimg.mosaic status

# On-demand mosaic
python -m dsa110_contimg.mosaic on-demand --name custom --start TS --end TS
```

**Schedule:** 03:00 UTC daily (when enabled)

**To enable (future):**

```bash
sudo cp /data/dsa110-contimg/ops/systemd/contimg-mosaic-nightly.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now contimg-mosaic-nightly.timer
```

### Documentation Updates

- **`docs/guides/mosaicking.md`** - Added "Automated Nightly Mosaics" section with:
  - Enablement instructions
  - Manual execution commands
  - Environment variables
  - Monitoring and troubleshooting

## Testing

- All 12 visualization unit tests passing
- Mosaic CLI dry-run verified
- Mosaic status command verified

## Files Changed

```
backend/src/dsa110_contimg/visualization/__init__.py     (new)
backend/src/dsa110_contimg/visualization/config.py       (new)
backend/src/dsa110_contimg/visualization/fits_plots.py   (new)
backend/src/dsa110_contimg/visualization/calibration_plots.py (new)
backend/src/dsa110_contimg/visualization/source_plots.py (new)
backend/src/dsa110_contimg/visualization/mosaic_plots.py (new)
backend/src/dsa110_contimg/visualization/report.py       (new)
backend/src/dsa110_contimg/mosaic/__main__.py            (new)
backend/tests/unit/visualization/test_visualization.py  (new)
docs/guides/visualization.md                             (new)
docs/guides/mosaicking.md                                (updated)
mkdocs.yml                                               (updated)
ops/systemd/contimg-mosaic-nightly.service               (new)
ops/systemd/contimg-mosaic-nightly.timer                 (new)
```

## Status

- ✅ Visualization module: Complete and tested
- ✅ Nightly mosaic infrastructure: Complete (manual execution ready)
- ⏸️ Nightly mosaic automation: Infrastructure ready, not enabled
