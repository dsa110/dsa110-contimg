# Mosaic Orchestrator Usage Guide

This guide provides comprehensive usage examples for the enhanced
`create_10min_mosaic.py` script and `MosaicOrchestrator` class.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Transit Selection](#transit-selection)
3. [Time Range Override](#time-range-override)
4. [Quality Filtering](#quality-filtering)
5. [Batch Processing](#batch-processing)
6. [Existing Mosaic Handling](#existing-mosaic-handling)
7. [Preview Mode](#preview-mode)
8. [Advanced Examples](#advanced-examples)

## Basic Usage

### Default: Earliest Transit

The simplest usage creates a mosaic using the earliest available transit:

```bash
python create_10min_mosaic.py
```

This will:

- Use calibrator `0834+555`
- Find the earliest available transit
- Create a 12-minute mosaic centered on that transit
- Output to `/stage/dsa110-contimg/mosaics/`

### Custom Timespan

Specify a different timespan (in minutes):

```bash
python create_10min_mosaic.py --timespan-minutes 20
```

## Transit Selection

### 1. Interactive Selection with Quality Metrics

List available transits and select interactively:

```bash
python create_10min_mosaic.py --list-transits
```

This displays a table showing:

- **Index**: Transit number (0-based)
- **Transit Time**: ISO timestamp
- **PB Resp**: Primary beam response (0.0-1.0)
- **MS Count**: Number of Measurement Set files available
- **Days Ago**: How many days ago the transit occurred

Example output:

```
:clipboard: Listing available transits for 0834+555...

:check: Found 5 transit(s):

Index    Transit Time            PB Resp    MS Count   Days Ago
---------------------------------------------------------------------------
0        2025-01-15T10:30:00     0.95       3          5
1        2025-01-14T10:30:00     0.94       3          6
2        2025-01-13T10:30:00     0.93       2          7
3        2025-01-12T10:30:00     0.92       3          8
4        2025-01-11T10:30:00     0.91       3          9

Select transit index (0-4) or 'q' to quit:
```

### 2. Select by Index

Select a specific transit by its index:

```bash
python create_10min_mosaic.py --transit-index 2
```

This uses the transit at index 2 from the available transits list.

### 3. Select by Time

Specify the exact transit time:

```bash
python create_10min_mosaic.py --transit-time "2025-01-15T10:30:00"
```

The time must be in ISO format (`YYYY-MM-DDTHH:MM:SS`).

## Time Range Override

Override the transit-centered calculation with explicit start and end times:

```bash
python create_10min_mosaic.py \
    --start-time "2025-01-15T10:00:00" \
    --end-time "2025-01-15T10:12:00"
```

**Important**: Both `--start-time` and `--end-time` must be provided together.
The script will error if only one is specified.

This is useful when:

- You want a specific time window regardless of transit times
- You're analyzing a specific event or time period
- You need to align with external data sources

## Quality Filtering

Filter transits by quality metrics before selection:

### Filter by Primary Beam Response

Only consider transits with PB response above a threshold:

```bash
python create_10min_mosaic.py --min-pb-response 0.9
```

**Note**: For drift scans at constant declination, PB response may be constant
for a given calibrator. This filter is more useful when comparing different
calibrators or observing modes.

### Filter by MS File Count

Only consider transits with sufficient MS files:

```bash
python create_10min_mosaic.py --min-ms-count 3
```

This ensures you have at least 3 MS files (the minimum for a proper mosaic).

### Combined Filters

Combine multiple filters:

```bash
python create_10min_mosaic.py \
    --list-transits \
    --min-pb-response 0.9 \
    --min-ms-count 3
```

This will only show transits that meet both criteria.

## Batch Processing

Process multiple transits in a single run:

### Process All Available Transits

```bash
python create_10min_mosaic.py --all-transits
```

This creates mosaics for all available transits, applying any quality filters
you've specified.

### Process a Range of Transits

Process a specific range of transits:

```bash
python create_10min_mosaic.py --transit-range 0:5
```

This processes transits at indices 0, 1, 2, 3, and 4 (5 total).

### Batch with Quality Filters

Combine batch processing with quality filtering:

```bash
python create_10min_mosaic.py \
    --all-transits \
    --min-pb-response 0.9 \
    --min-ms-count 3
```

This processes all transits that meet the quality criteria.

### Batch Results

Batch processing provides a summary at the end:

```
:chart: Batch processing mosaics for 0834+555

============================================================
Processing transit 1/5: 2025-01-15T10:30:00
============================================================
:check: Successfully created mosaic: /stage/.../mosaic_1.fits

============================================================
Processing transit 2/5: 2025-01-14T10:30:00
============================================================
:check: Successfully created mosaic: /stage/.../mosaic_2.fits

...

:check: Batch processing complete: 5/5 successful
```

## Existing Mosaic Handling

### Check for Existing Mosaics

By default, the pipeline checks if a mosaic with the exact same parameters
already exists. If found, it stops execution:

```bash
python create_10min_mosaic.py --transit-time "2025-01-15T10:30:00"
```

If a mosaic already exists, you'll see:

```
============================================================
EXISTING MOSAIC FOUND
============================================================
A mosaic with these exact parameters already exists:
  ID: 42
  Name: mosaic_0834+555_2025-01-15T10:30:00
  Path: /stage/dsa110-contimg/mosaics/mosaic_0834+555_2025-01-15T10:30:00.fits
  Created: 2025-01-15T11:00:00
  Start: 2025-01-15T10:24:00
  End: 2025-01-15T10:36:00
  Images: 3

To overwrite this mosaic, add the --overwrite flag to your command.
```

### Overwrite Existing Mosaics

To overwrite an existing mosaic, use the `--overwrite` flag:

```bash
python create_10min_mosaic.py \
    --transit-time "2025-01-15T10:30:00" \
    --overwrite
```

**Important**: The check happens at the very start of the run, before any work
is done. This prevents accidentally recreating mosaics that already exist.

## Preview Mode

Preview mode validates and plans the mosaic without actually creating it:

```bash
python create_10min_mosaic.py --preview
```

Or use the equivalent:

```bash
python create_10min_mosaic.py --dry-run
```

### Enhanced Preview Output

Preview mode now provides detailed information:

```
============================================================
DRY-RUN MODE: Validating mosaic plan without building
============================================================

Mosaic plan:
  - Calibrator: 0834+555
  - Transit time: 2025-01-15T10:30:00
  - Window: 2025-01-15T10:24:00 to 2025-01-15T10:36:00
  - Timespan: 12 minutes
  - Required MS files: 3
  - Available MS files: 3
  - Group ID: (will be created)
  - MS file paths:
      1. /stage/.../ms_001.ms
      2. /stage/.../ms_002.ms
      3. /stage/.../ms_003.ms

============================================================
VALIDATION WARNINGS (may cause issues):
============================================================
  :warning: Only 3 MS files available, would create asymmetric mosaic.

:check: Validation complete. Ready to build.
Run with dry_run=False to create the mosaic.
```

This helps you:

- Verify the plan before execution
- Check for potential issues
- See what MS files will be used
- Validate time ranges and parameters

## Advanced Examples

### Example 1: High-Quality Transit Selection

Find and use the highest quality transit:

```bash
# List transits with quality metrics
python create_10min_mosaic.py \
    --list-transits \
    --min-pb-response 0.95 \
    --min-ms-count 3
```

Then select the best one interactively.

### Example 2: Specific Time Window Analysis

Create a mosaic for a specific time window:

```bash
python create_10min_mosaic.py \
    --start-time "2025-01-15T10:00:00" \
    --end-time "2025-01-15T10:15:00" \
    --preview
```

First preview to verify, then run without `--preview` to create.

### Example 3: Batch Processing with Quality Control

Process all high-quality transits from the last 30 days:

```bash
python create_10min_mosaic.py \
    --all-transits \
    --min-pb-response 0.9 \
    --min-ms-count 3 \
    --overwrite
```

The `--overwrite` flag ensures any existing mosaics are recreated.

### Example 4: Programmatic Usage

Use the orchestrator directly in Python:

```python
from astropy.time import Time
from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator
from pathlib import Path

# Initialize orchestrator
orchestrator = MosaicOrchestrator(
    products_db_path=Path("state/products.sqlite3")
)

# List available transits with quality metrics
transits = orchestrator.list_available_transits_with_quality(
    calibrator_name="0834+555",
    max_days_back=60,
    min_pb_response=0.9,
    min_ms_count=3,
)

# Select the first transit
if transits:
    transit_time = transits[0]["transit_time"]

    # Create mosaic
    mosaic_path = orchestrator.create_mosaic_centered_on_calibrator(
        calibrator_name="0834+555",
        timespan_minutes=12,
        wait_for_published=False,
        transit_time=transit_time,
        overwrite=False,
    )

    print(f"Created mosaic: {mosaic_path}")
```

### Example 5: Batch Processing Programmatically

```python
from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator
from pathlib import Path

orchestrator = MosaicOrchestrator(
    products_db_path=Path("state/products.sqlite3")
)

# Process all transits with quality filters
results = orchestrator.create_mosaics_batch(
    calibrator_name="0834+555",
    all_transits=True,
    timespan_minutes=12,
    min_pb_response=0.9,
    min_ms_count=3,
    wait_for_published=False,
    overwrite=False,
)

# Check results
success_count = sum(1 for r in results if r["status"] == "success")
print(f"Successfully created {success_count}/{len(results)} mosaics")

for result in results:
    if result["status"] == "success":
        print(f"  :check: {result['transit_time']}: {result['path']}")
    else:
        print(f"  :cross: {result['transit_time']}: {result.get('error', 'Unknown error')}")
```

## Command-Line Reference

### Transit Selection (mutually exclusive)

- `--transit-time ISO_TIME`: Use specific transit time
- `--transit-index N`: Select transit by index (0-based)
- `--list-transits`: Interactive selection with quality metrics

### Time Range

- `--start-time ISO_TIME`: Explicit start time (requires `--end-time`)
- `--end-time ISO_TIME`: Explicit end time (requires `--start-time`)

### Quality Filtering

- `--min-pb-response FLOAT`: Minimum primary beam response (0.0-1.0)
- `--min-ms-count INT`: Minimum number of MS files required

### Batch Processing (mutually exclusive)

- `--all-transits`: Process all available transits
- `--transit-range START:END`: Process range of transits (e.g., `0:5`)

### Other Options

- `--preview` or `--dry-run`: Preview mode (validate without creating)
- `--overwrite`: Allow overwriting existing mosaics
- `--timespan-minutes INT`: Mosaic timespan in minutes (default: 12)

## Tips and Best Practices

1. **Always preview first**: Use `--preview` to validate before creating
2. **Check existing mosaics**: The pipeline automatically checks, but you can
   verify manually
3. **Use quality filters**: Filter by PB response and MS count to ensure good
   data
4. **Batch processing**: Use `--all-transits` for systematic processing
5. **Time range override**: Use explicit time ranges for precise control
6. **Interactive selection**: Use `--list-transits` to see all options before
   choosing

## Troubleshooting

### "No transits found"

- Check that the calibrator name is correct
- Increase `max_days_back` if needed (programmatic usage)
- Verify transit database has data

### "Existing mosaic found"

- Use `--overwrite` to recreate the mosaic
- Or use different parameters (different transit time or timespan)

### "MS files not available"

- The pipeline will trigger HDF5 conversion automatically
- Ensure HDF5 source files are available
- Check disk space and permissions

### "Validation errors"

- Review the error messages in preview mode
- Fix any missing prerequisites
- Check database connectivity

## See Also

- `create_10min_mosaic.py --help`: Full command-line help
- `pipeline_flowchart.mmd`: Visual pipeline flow diagram
- `test_mosaic_orchestrator_features.py`: Test suite for new features
