# Catalog Coverage Visualization Guide

## Overview

The catalog coverage visualization tool generates graphical representations of
catalog database coverage and status, helping users understand which catalogs
are available for the current telescope declination.

## Installation

The visualization tool requires:

- Python 3.7+
- `matplotlib` (for plotting)
- `numpy` (for calculations)

Install dependencies:

```bash
pip install matplotlib numpy
```

## Basic Usage

### Generate Coverage Plot

```bash
python -m dsa110_contimg.catalog.visualize_coverage \
    --dec 54.6 \
    --plot-type coverage \
    --output-dir state/catalogs
```

### Generate Summary Table

```bash
python -m dsa110_contimg.catalog.visualize_coverage \
    --dec 54.6 \
    --plot-type table \
    --output-dir state/catalogs
```

### Generate Both

```bash
python -m dsa110_contimg.catalog.visualize_coverage \
    --dec 54.6 \
    --plot-type both \
    --output-dir state/catalogs
```

## Command-Line Options

### `--dec DEC`

- **Type**: Float
- **Description**: Current declination in degrees
- **Default**: Auto-detected from pointing history (if `--ingest-db` provided)
- **Example**: `--dec 54.6`

### `--ingest-db PATH`

- **Type**: Path
- **Description**: Path to ingest database (for auto-detecting declination)
- **Default**: Searches common locations
  (`/data/dsa110-contimg/state/ingest.sqlite3`, `state/ingest.sqlite3`)
- **Example**: `--ingest-db /data/dsa110-contimg/state/ingest.sqlite3`

### `--output-dir PATH`

- **Type**: Path
- **Description**: Output directory for generated plots
- **Default**: `state/catalogs`
- **Example**: `--output-dir /tmp/plots`

### `--plot-type TYPE`

- **Type**: Choice (`both`, `coverage`, `table`)
- **Description**: Type of visualization to generate
- **Default**: `both`
- **Options**:
  - `coverage`: Horizontal bar chart showing coverage ranges
  - `table`: Summary table with status information
  - `both`: Generate both plot and table

### `--no-db-status`

- **Type**: Flag
- **Description**: Don't show database existence status in plots
- **Default**: False (status is shown)

## Output Files

### Coverage Plot (`coverage_plot.png`)

A horizontal bar chart showing:

- **Coverage bars**: Each catalog's declination range
  - Blue: NVSS
  - Orange: FIRST
  - Green: RACS (RAX)
- **Opacity**:
  - High opacity (0.7): Database exists
  - Low opacity (0.3): Database missing
- **Current declination**: Red dashed vertical line
- **Coverage limits**: Labels at range boundaries
- **Status indicators**: Text showing database existence

**Example:**

```
┌─────────────────────────────────────────────────────────┐
│ Catalog Coverage Limits and Database Status             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  NVSS ✓ DB exists    [──────────────]                  │
│         -40.0°                             90.0°        │
│                                                          │
│  FIRST ✗ DB missing  [──────────────]                   │
│         -40.0°                             90.0°        │
│                                                          │
│  RAX (outside)       [──────────]                        │
│         -90.0°                   49.9°                  │
│                                                          │
│  ────┼───────────────────────────────────────────────    │
│      │ Current: 54.6°                                   │
└─────────────────────────────────────────────────────────┘
```

### Summary Table (`coverage_table.png`)

A color-coded table showing:

- **Catalog names**: NVSS, FIRST, RACS (RAX)
- **Coverage ranges**: Declination limits
- **Within coverage**: Yes/No
- **Database exists**: Yes/No/N/A
- **Status**: Color-coded cells
  - Green: ✓ Ready (database exists)
  - Red: ✗ Missing (database missing but should exist)
  - Gray: Outside coverage (database not expected)

**Example:**

```
┌──────────┬──────────────────┬─────────────────┬─────────────────┬──────────┐
│ Catalog  │ Coverage Range   │ Within Coverage  │ Database Exists │ Status   │
├──────────┼──────────────────┼─────────────────┼─────────────────┼──────────┤
│ NVSS     │ -40.0° to 90.0°  │ Yes              │ Yes             │ ✓ Ready  │
│ FIRST    │ -40.0° to 90.0°  │ Yes              │ No              │ ✗ Missing│
│ RACS     │ -90.0° to 49.9°  │ No               │ N/A             │ Outside  │
└──────────┴──────────────────┴─────────────────┴─────────────────┴──────────┘
```

## Auto-Detection of Declination

If `--dec` is not provided, the tool attempts to auto-detect the current
declination from pointing history:

```bash
python -m dsa110_contimg.catalog.visualize_coverage \
    --ingest-db state/ingest.sqlite3 \
    --plot-type both
```

The tool:

1. Connects to the ingest database
2. Queries the most recent entry in `pointing_history`
3. Uses the `dec_deg` value
4. Falls back gracefully if database is unavailable

## Programmatic Usage

### Python API

```python
from dsa110_contimg.catalog.visualize_coverage import (
    plot_catalog_coverage,
    plot_coverage_summary_table,
)
from pathlib import Path

# Generate coverage plot
plot_path = plot_catalog_coverage(
    dec_deg=54.6,
    output_path=Path("output/coverage.png"),
    show_database_status=True,
)

# Generate summary table
table_path = plot_coverage_summary_table(
    dec_deg=54.6,
    output_path=Path("output/table.png"),
)

print(f"Plot: {plot_path}")
print(f"Table: {table_path}")
```

### Without Declination

```python
# Auto-detect from pointing history
from pathlib import Path

plot_path = plot_catalog_coverage(
    dec_deg=None,  # Will try to get from ingest DB
    output_path=Path("output/coverage.png"),
    ingest_db_path=Path("state/ingest.sqlite3"),
)
```

## Use Cases

### 1. Pipeline Status Monitoring

Generate daily coverage reports:

```bash
# Add to cron job
0 0 * * * python -m dsa110_contimg.catalog.visualize_coverage \
    --output-dir /var/www/html/status \
    --plot-type both
```

### 2. Pre-Observation Planning

Check catalog availability before observations:

```bash
python -m dsa110_contimg.catalog.visualize_coverage \
    --dec 45.0 \
    --plot-type table
```

### 3. Troubleshooting

Identify missing databases:

```bash
python -m dsa110_contimg.catalog.visualize_coverage \
    --plot-type both \
    --output-dir /tmp/debug
```

### 4. Documentation

Include in reports and presentations:

```bash
python -m dsa110_contimg.catalog.visualize_coverage \
    --dec 54.6 \
    --plot-type both \
    --output-dir reports/coverage_status
```

## Customization

### Output Resolution

Modify the DPI in the source code:

```python
plt.savefig(output_path, dpi=300, bbox_inches="tight")  # High resolution
```

### Color Scheme

Colors are defined in `plot_catalog_coverage()`:

- NVSS: `#1f77b4` (blue)
- FIRST: `#ff7f0e` (orange)
- RAX: `#2ca02c` (green)

### Plot Size

Modify figure size:

```python
fig, ax = plt.subplots(figsize=(14, 10))  # Larger plot
```

## Troubleshooting

### Issue: "No module named 'matplotlib'"

**Solution:**

```bash
pip install matplotlib
```

### Issue: Plot not generated

**Check:**

1. Output directory is writable
2. Sufficient disk space
3. No permission errors

### Issue: Declination not detected

**Check:**

1. Ingest database exists
2. Pointing history has entries
3. Database path is correct

### Issue: Empty plot

**Possible causes:**

1. No declination provided and can't be detected
2. Coverage limits not defined
3. Database status checks failing

## Integration

### With Pipeline Status API

```python
import requests
from dsa110_contimg.catalog.visualize_coverage import plot_catalog_coverage

# Get status from API
response = requests.get("http://localhost:8000/api/status")
status = response.json()

if status.get("catalog_coverage"):
    dec = status["catalog_coverage"]["dec_deg"]
    plot_catalog_coverage(dec_deg=dec, output_path="status.png")
```

### With Monitoring Systems

Add to monitoring dashboards:

```bash
# Generate plot for web dashboard
python -m dsa110_contimg.catalog.visualize_coverage \
    --output-dir /var/www/html/dashboard \
    --plot-type both
```

## Examples

### Example 1: Quick Status Check

```bash
python -m dsa110_contimg.catalog.visualize_coverage \
    --dec 54.6 \
    --plot-type table
```

### Example 2: Full Report

```bash
python -m dsa110_contimg.catalog.visualize_coverage \
    --ingest-db /data/dsa110-contimg/state/ingest.sqlite3 \
    --plot-type both \
    --output-dir reports/$(date +%Y%m%d)
```

### Example 3: Without Database Status

```bash
python -m dsa110_contimg.catalog.visualize_coverage \
    --dec 54.6 \
    --plot-type coverage \
    --no-db-status
```

## Best Practices

1. **Regular updates**: Generate plots periodically to track status changes
2. **Archive**: Save historical plots for trend analysis
3. **Automation**: Integrate into monitoring systems
4. **Documentation**: Include plots in status reports
5. **Version control**: Track plot generation scripts

## Related Documentation

- `COVERAGE_FEATURES_IMPLEMENTATION.md`: Implementation details
- `API_DOCUMENTATION.md`: API endpoint documentation
- `TESTING_GUIDE.md`: Testing procedures
