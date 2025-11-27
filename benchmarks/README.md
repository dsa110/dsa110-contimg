# DSA-110 Pipeline Benchmarks

This directory contains performance benchmarks for the DSA-110 continuum imaging
pipeline, using [airspeed-velocity (asv)](https://asv.readthedocs.io/).

## Quick Start

```bash
conda activate casa6

# Run all benchmarks (single iteration for quick check)
asv run --quick --python=same

# Run specific benchmark class
asv run --quick --python=same --bench "Calibration"

# Run with multiple samples for statistics
asv run --python=same

# Generate HTML report
asv publish
asv preview  # Opens browser
```

## Benchmark Structure

```
benchmarks/
├── asv.conf.json           # ASV configuration
├── bench_calibration.py    # Calibration stage benchmarks
├── bench_flagging.py       # RFI flagging benchmarks
├── bench_conversion.py     # HDF5 → MS conversion benchmarks
├── bench_imaging.py        # WSClean imaging benchmarks
└── bench_photometry.py     # Forced photometry benchmarks
```

## Writing Benchmarks

ASV benchmarks follow specific conventions:

```python
class TimeSomething:
    """Benchmark class - must start with 'Time' for timing benchmarks."""

    # Class-level attributes for configuration
    timeout = 600  # Maximum seconds per benchmark

    def setup(self):
        """Called before each benchmark - not timed."""
        self.data = load_test_data()

    def time_operation(self):
        """Timed method - must start with 'time_'."""
        do_operation(self.data)

    def teardown(self):
        """Called after each benchmark - not timed."""
        cleanup()
```

## Test Data

Benchmarks use data from:

- `/stage/dsa110-contimg/ms/` - Measurement Sets
- `/data/incoming/` - Raw HDF5 files

The `setup()` method should verify data exists before benchmarks run.

## Interpreting Results

ASV reports:

- **Wall time**: Total elapsed time
- **Iterations**: Number of samples (more = better statistics)
- **Standard deviation**: Variation across runs

Regressions >10% are flagged (configurable in `asv.conf.json`).

## CI Integration

Benchmarks can run in CI to detect performance regressions:

```bash
# Compare current branch to master
asv continuous master HEAD --factor 1.1
```
