# DSA-110 Pipeline Performance Benchmarks

This directory contains **statistical performance benchmarks** for the DSA-110
continuum imaging pipeline, using
[airspeed-velocity (asv)](https://asv.readthedocs.io/). These benchmarks follow
the methodology established by
[casabench](https://github.com/casangi/casabench) for rigorous, reproducible
performance testing.

## Why Benchmark?

Performance benchmarks serve three critical purposes:

1. **Regression Detection**: Catch performance regressions before they reach
   production
2. **Optimization Validation**: Measure the impact of optimizations with
   statistical confidence
3. **Documentation**: Provide empirical baseline for system capacity planning

---

## Quick Start (Novice Users)

If you just want to run benchmarks to see current performance:

```bash
# Activate the required environment
conda activate casa6

# Quick check - runs each benchmark once (~5-15 minutes)
make bench-quick

# Or using the CLI
dsa110-benchmark quick
```

### Understanding the Output

```
[  0.00%] · For dsa110-contimg commit 2af725e9 (master-dev):
[  5.00%] ·· Benchmarking bench_calibration.TimeBandpassSolve.time_bandpass_single_field
[  5.00%] ··· 31.14s
```

- **31.14s** = Time to run bandpass calibration on a single field
- Results are saved and can be compared across commits

---

## Full Benchmark Run (Expert Users)

For statistical analysis and regression detection:

```bash
# Full run with multiple samples (~30-60 minutes)
make bench

# Generate HTML report
make bench-report
make bench-preview  # Opens in browser

# Compare performance between commits
make bench-compare BASE=HEAD~5 TARGET=HEAD
```

### CLI Commands (Alternative to Make)

```bash
# All available commands
dsa110-benchmark --help

# Quick check
dsa110-benchmark quick

# Full run with statistics
dsa110-benchmark run

# Filter by benchmark name
dsa110-benchmark run --filter Calibration
dsa110-benchmark run --filter time_bandpass

# Generate report
dsa110-benchmark report --open

# Compare commits
dsa110-benchmark compare HEAD~1 HEAD

# Show environment info
dsa110-benchmark info
```

---

## Benchmark Categories

### Conversion (`bench_conversion.py`)

Measures HDF5 → Measurement Set conversion performance.

| Benchmark                     | Typical Time | Description                              |
| ----------------------------- | ------------ | ---------------------------------------- |
| `time_load_single_subband`    | 4-5s         | Load one HDF5 subband via pyuvdata       |
| `time_load_four_subbands`     | 65-75s       | Load + merge 4 subbands (batched loader) |
| `time_convert_subband_group`  | 4-5min       | Full 16-subband conversion pipeline      |

**Note**: Conversion benchmarks stage HDF5 files from HDD (`/data/incoming`) to
SSD (`/scratch/`) before processing, matching the production pipeline behavior.

### Calibration (`bench_calibration.py`)

Measures CASA calibration task performance.

| Benchmark                    | Typical Time | Description                       |
| ---------------------------- | ------------ | --------------------------------- |
| `time_import_calibration`    | <1s          | Import calibration module         |
| `time_bandpass_single_field` | 30-35s       | Bandpass solve (1.8M visibilities)|
| `time_gaincal_single_field`  | 10-12s       | Gain calibration                  |
| `time_applycal_single_table` | 4-5s         | Apply calibration table           |

### Flagging (`bench_flagging.py`)

Measures RFI flagging operations.

| Benchmark          | Typical Time | Description                     |
| ------------------ | ------------ | ------------------------------- |
| `time_reset_flags` | 9-10s        | Clear all flags from MS         |
| `time_flag_zeros`  | 18-20s       | Flag zero-amplitude visibilities|

### Imaging (`bench_imaging.py`)

WSClean imaging benchmarks (disabled by default - too slow for routine testing).

| Benchmark             | Typical Time | Description           |
| --------------------- | ------------ | --------------------- |
| `time_dirty_imaging`  | ~minutes     | Dirty image (no clean)|
| `time_clean_imaging`  | ~10+ min     | Full CLEAN deconvolution|

---

## Test Data Requirements

Benchmarks require access to:

- **HDF5 files**: `/data/incoming/` (raw subband files)
- **Measurement Sets**: `/stage/dsa110-contimg/ms/` (calibrated MS files)

The `setup()` method in each benchmark verifies data availability and skips if
missing.

---

## Interpreting Results

### Single Run Output

```
bench_calibration.TimeBandpassSolve.time_bandpass_single_field   31.14s
```

- **Metric**: Wall-clock time (lower is better)
- **Unit**: Seconds (s), minutes (m), or milliseconds (ms)

### Statistical Analysis

Full runs collect multiple samples:

```
·· For dsa110-contimg commit 2af725e9 (master-dev):
·· bench_calibration.TimeBandpassSolve.time_bandpass_single_field
··· ok
··· 31.1±0.5s
```

- **31.1±0.5s** = Mean ± standard deviation
- Lower variance = more consistent performance

### Regression Detection

ASV flags regressions exceeding 10% (configurable in `asv.conf.json`):

```
REGRESSION: bench_conversion.time_convert_subband_group (1.25x slower)
  Before: 240.5s
  After:  301.2s
```

---

## Directory Structure

```
benchmarks/
├── asv.conf.json           # ASV configuration
├── __init__.py             # Required for module discovery
├── README.md               # This file
│
├── bench_calibration.py    # Calibration benchmarks
├── bench_conversion.py     # HDF5 → MS conversion benchmarks
├── bench_flagging.py       # RFI flagging benchmarks
├── bench_imaging.py        # WSClean imaging benchmarks (disabled)
│
└── .asv/                   # ASV working directory (gitignored)
    ├── machine.json        # Machine configuration
    ├── results/            # Benchmark results by commit
    └── html/               # Generated HTML reports
```

---

## Writing New Benchmarks

### Basic Pattern

```python
class TimeSomething:
    """Benchmark class name must start with 'Time' for timing benchmarks."""

    # Configuration
    timeout = 600  # Max seconds per benchmark (default: 60)
    processes = 1  # Don't parallelize (CASA not thread-safe)

    def setup(self):
        """Called before each benchmark iteration - NOT timed.
        
        Use for data loading, path validation, and setup.
        Raise NotImplementedError to skip if data unavailable.
        """
        self.data = load_test_data()
        if self.data is None:
            raise NotImplementedError("Test data not available")

    def time_operation(self):
        """Timed method - name must start with 'time_'.
        
        Only the code inside this method is timed.
        """
        do_operation(self.data)

    def teardown(self):
        """Called after each benchmark - NOT timed.
        
        Use for cleanup.
        """
        cleanup()
```

### Best Practices

1. **Stage to SSD**: For I/O benchmarks, copy data to SSD first
   ```python
   def setup(self):
       # Copy from HDD to SSD for realistic pipeline timing
       self.scratch_path = shutil.copytree(hdd_path, ssd_path)
   ```

2. **Work on copies**: Never modify original test data
   ```python
   self.ms_copy = f"/tmp/bench_{uuid4()}.ms"
   shutil.copytree(self.ms_path, self.ms_copy)
   ```

3. **Validate data**: Skip gracefully if data unavailable
   ```python
   if not Path(self.ms_path).exists():
       raise NotImplementedError("Test MS not found")
   ```

4. **Set realistic timeouts**: Conversion may take 5+ minutes
   ```python
   timeout = 600  # 10 minutes
   ```

---

## CI Integration

Detect regressions in continuous integration:

```bash
# Compare feature branch to main
asv continuous main HEAD --factor 1.1

# Exit code 1 = regression detected
```

### GitHub Actions Example

```yaml
- name: Run benchmarks
  run: |
    cd benchmarks
    asv run --quick --python=same --set-commit-hash=${{ github.sha }}

- name: Check for regressions
  run: |
    cd benchmarks
    asv compare HEAD~1 HEAD --factor 1.1
```

---

## Troubleshooting

### "Error: asv: command not found"

```bash
conda activate casa6
pip install asv
```

### "No benchmark results found"

Results require explicit commit hash when using `environment_type: existing`:

```bash
asv run --python=same --set-commit-hash=$(git rev-parse HEAD)
```

### "Benchmark skipped: Test data not found"

Ensure test data exists at expected paths:

```bash
ls -la /stage/dsa110-contimg/ms/*.ms
ls -la /data/incoming/*.hdf5
```

### "Machine file not found"

ASV needs machine configuration. Created automatically on first run, or
manually:

```bash
cd benchmarks
asv machine --yes
```

---

## Reference Results (lxd110h17)

Baseline results on production hardware (Intel Xeon Silver 4210, 128GB RAM):

| Benchmark                              | Time    | Notes                    |
| -------------------------------------- | ------- | ------------------------ |
| `time_load_single_subband`             | 4.54s   | Single HDF5 file         |
| `time_load_four_subbands`              | 69s     | 4-file batch load+merge  |
| `time_convert_subband_group`           | 4.05min | Full 16-subband pipeline |
| `time_bandpass_single_field`           | 31.1s   | 1.8M row MS              |
| `time_gaincal_single_field`            | 10.3s   | 1.8M row MS              |
| `time_applycal_single_table`           | 4.08s   | Single caltable          |
| `time_reset_flags`                     | 9.29s   | Clear all flags          |
| `time_flag_zeros`                      | 18.2s   | Flag zero amplitudes     |

---

## Further Reading

- **Project Docs**: `docs/guides/benchmarking.md` (full guide)
- **ASV Documentation**: https://asv.readthedocs.io/
- **casabench**: https://github.com/casangi/casabench (methodology reference)

