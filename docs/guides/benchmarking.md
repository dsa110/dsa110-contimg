# Performance Benchmarking Guide

This guide covers statistical performance benchmarking for the DSA-110 continuum
imaging pipeline using [airspeed-velocity (asv)](https://asv.readthedocs.io/).
Our methodology is inspired by
[casabench](https://github.com/casangi/casabench), the official CASA
benchmarking framework.

## Overview

### Why Benchmark?

Performance benchmarks provide:

1. **Regression Detection**: Catch slowdowns before they reach production
2. **Optimization Validation**: Statistically verify performance improvements
3. **Capacity Planning**: Understand real-world throughput limits
4. **Historical Tracking**: Compare performance across commits and releases

### Quick Start

=== "Make (Recommended)"

    ```bash
    conda activate casa6

    # Quick check (~5 minutes)
    make bench-quick

    # Full run with statistics (~30 minutes)
    make bench

    # Generate HTML report
    make bench-report
    make bench-preview
    ```

=== "CLI"

    ```bash
    conda activate casa6

    # Quick check
    dsa110-benchmark quick

    # Full run
    dsa110-benchmark run

    # Report
    dsa110-benchmark report --open
    ```

=== "Raw ASV"

    ```bash
    conda activate casa6
    cd benchmarks

    asv run --quick --python=same --set-commit-hash=$(git rev-parse HEAD)
    asv publish && asv preview
    ```

---

## Benchmark Categories

### Conversion Benchmarks

**File**: `benchmarks/bench_conversion.py`

Measures HDF5 → Measurement Set conversion performance. These benchmarks stage
data from HDD to SSD to match production pipeline behavior.

| Benchmark                    | Description                                        | Typical Time |
| ---------------------------- | -------------------------------------------------- | ------------ |
| `time_load_single_subband`   | Load one HDF5 file via pyuvdata                    | ~5s          |
| `time_load_four_subbands`    | Batched load of 4 subbands (merge included)        | ~70s         |
| `time_convert_subband_group` | Full 16-subband pipeline (load → merge → write MS) | ~4min        |

**Key Implementation Detail**: Conversion benchmarks copy HDF5 files from
`/data/incoming/` (HDD) to `/scratch/` (SSD) before timing, matching how the
production streaming converter works.

### Calibration Benchmarks

**File**: `benchmarks/bench_calibration.py`

Measures CASA calibration task performance using actual pipeline functions.

| Benchmark                    | Description                        | Typical Time |
| ---------------------------- | ---------------------------------- | ------------ |
| `time_import_calibration`    | Import calibration module          | <1s          |
| `time_bandpass_single_field` | Bandpass solve (1.8M visibilities) | ~31s         |
| `time_gaincal_single_field`  | Gain calibration                   | ~10s         |
| `time_applycal_single_table` | Apply calibration table            | ~4s          |

### Flagging Benchmarks

**File**: `benchmarks/bench_flagging.py`

Measures RFI flagging operations.

| Benchmark          | Description                      | Typical Time |
| ------------------ | -------------------------------- | ------------ |
| `time_reset_flags` | Clear all flags from MS          | ~9s          |
| `time_flag_zeros`  | Flag zero-amplitude visibilities | ~18s         |

!!! note "AOFlagger Disabled" AOFlagger benchmarks are disabled by default due
to execution time (~30+ minutes). Enable by removing the `_` prefix from
`_TimeRFIFlagging`.

### Imaging Benchmarks

**File**: `benchmarks/bench_imaging.py`

WSClean imaging benchmarks (disabled by default).

| Benchmark            | Description              | Typical Time |
| -------------------- | ------------------------ | ------------ |
| `time_dirty_imaging` | Dirty image only         | ~minutes     |
| `time_clean_imaging` | Full CLEAN deconvolution | ~10+ min     |

!!! warning "Disabled by Default" Imaging benchmarks are disabled because they
take too long for routine testing. Enable by removing the `_` prefix from class
names.

---

## Understanding Results

### Single Iteration Output

```text
[  5.00%] ·· Benchmarking bench_calibration.TimeBandpassSolve.time_bandpass_single_field
[  5.00%] ··· 31.14s
```

- **31.14s**: Wall-clock time to execute the benchmark
- Lower is better

### Statistical Output (Full Run)

```text
·· bench_calibration.TimeBandpassSolve.time_bandpass_single_field
··· ok
··· 31.1±0.5s
```

- **31.1±0.5s**: Mean ± standard deviation across samples
- Lower variance indicates more consistent performance

### Regression Detection

ASV automatically flags regressions exceeding the threshold (default: 10%):

```text
REGRESSION: bench_conversion.time_convert_subband_group (1.25x slower)
  Before: 240.5s
  After:  301.2s
```

---

## Command Reference

### Make Targets

| Target                               | Description                    | Time      |
| ------------------------------------ | ------------------------------ | --------- |
| `make bench-quick`                   | Single iteration per benchmark | 5-15 min  |
| `make bench`                         | Full statistical run           | 30-60 min |
| `make bench-calibration`             | Only calibration benchmarks    | ~5 min    |
| `make bench-conversion`              | Only conversion benchmarks     | ~15 min   |
| `make bench-report`                  | Generate HTML report           | <1 min    |
| `make bench-preview`                 | Open report in browser         | -         |
| `make bench-check`                   | Verify benchmark configuration | <1 min    |
| `make bench-info`                    | Show environment info          | <1 min    |
| `make bench-compare BASE=X TARGET=Y` | Compare commits                | varies    |

### CLI Commands

```bash
# Get help
dsa110-benchmark --help

# Quick benchmark check
dsa110-benchmark quick
dsa110-benchmark quick --filter Calibration
dsa110-benchmark quick --verbose

# Full benchmark run
dsa110-benchmark run
dsa110-benchmark run --filter time_bandpass
dsa110-benchmark run --samples 10

# Generate and view report
dsa110-benchmark report
dsa110-benchmark report --open

# Compare commits
dsa110-benchmark compare HEAD~1 HEAD
dsa110-benchmark compare main feature-branch --factor 1.05

# Show latest results
dsa110-benchmark show

# Check configuration
dsa110-benchmark check

# Environment info
dsa110-benchmark info
```

---

## Writing New Benchmarks

### Basic Template

```python
class TimeSomething:
    """Benchmark class name must start with 'Time' for timing benchmarks."""

    # Configuration
    timeout = 600  # Max seconds (default: 60)
    processes = 1  # Don't parallelize

    def setup(self):
        """Called before each benchmark - NOT timed."""
        self.data = load_test_data()
        if self.data is None:
            raise NotImplementedError("Test data not available")

    def time_operation(self):
        """Timed method - name must start with 'time_'."""
        do_operation(self.data)

    def teardown(self):
        """Called after each benchmark - NOT timed."""
        cleanup()
```

### Naming Conventions

| Prefix   | Type             | Example               |
| -------- | ---------------- | --------------------- |
| `Time*`  | Timing benchmark | `TimeConversion`      |
| `Mem*`   | Memory benchmark | `MemLoadSubbands`     |
| `Peak*`  | Peak memory      | `PeakMemConversion`   |
| `time_*` | Timing method    | `time_bandpass_solve` |
| `mem_*`  | Memory method    | `mem_load_data`       |

### Best Practices

#### 1. Stage I/O-bound data to SSD

```python
def setup(self):
    """Stage files from HDD to SSD for realistic timing."""
    import shutil
    from pathlib import Path

    hdd_source = Path("/data/incoming/group_xxx")
    ssd_scratch = Path("/scratch/benchmarks")
    ssd_scratch.mkdir(exist_ok=True)

    self.staged_files = []
    for f in hdd_source.glob("*.hdf5"):
        dest = ssd_scratch / f.name
        shutil.copy2(f, dest)
        self.staged_files.append(dest)
```

#### 2. Work on copies

```python
def setup(self):
    """Create a fresh copy to avoid state pollution."""
    import shutil
    from uuid import uuid4

    self.original = Path("/stage/dsa110-contimg/ms/test.ms")
    self.working_copy = Path(f"/tmp/bench_{uuid4()}.ms")
    shutil.copytree(self.original, self.working_copy)

def teardown(self):
    """Clean up working copy."""
    import shutil
    if self.working_copy.exists():
        shutil.rmtree(self.working_copy)
```

#### 3. Skip gracefully when data unavailable

```python
def setup(self):
    """Skip if test data doesn't exist."""
    self.ms_path = Path("/stage/dsa110-contimg/ms/test.ms")
    if not self.ms_path.exists():
        raise NotImplementedError(f"Test MS not found: {self.ms_path}")
```

#### 4. Set appropriate timeouts

```python
# Fast operations
class TimeImport:
    timeout = 30

# Moderate operations
class TimeCalibration:
    timeout = 300  # 5 minutes

# Slow operations
class TimeConversion:
    timeout = 600  # 10 minutes
```

---

## CI Integration

### Detecting Regressions

```bash
# Compare feature branch to main (fail if >10% regression)
asv continuous main HEAD --factor 1.1
echo "Exit code: $?"  # 1 = regression detected
```

### GitHub Actions Example

```yaml
name: Performance Benchmarks

on:
  pull_request:
    branches: [main, master-dev]

jobs:
  benchmark:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0 # Need full history for comparison

      - name: Setup environment
        run: |
          conda activate casa6
          pip install asv

      - name: Run benchmarks
        run: |
          cd benchmarks
          asv run --quick --python=same --set-commit-hash=${{ github.sha }}

      - name: Check for regressions
        run: |
          cd benchmarks
          asv compare ${{ github.event.pull_request.base.sha }} ${{ github.sha }} --factor 1.1
```

---

## Troubleshooting

### Common Issues

#### "asv: command not found"

```bash
conda activate casa6
pip install asv
```

#### "No benchmark results found"

Results require explicit commit hash when using `environment_type: existing`:

```bash
asv run --python=same --set-commit-hash=$(git rev-parse HEAD)
```

#### "Benchmark skipped: Test data not found"

Ensure test data exists:

```bash
ls -la /stage/dsa110-contimg/ms/*.ms
ls -la /data/incoming/*.hdf5
```

#### "Machine file not found"

Create machine configuration:

```bash
cd benchmarks
asv machine --yes
```

#### "Results not persisting"

With `environment_type: existing`, results require `--set-commit-hash`:

```bash
asv run --python=same --set-commit-hash=$(git rev-parse HEAD)
```

### Performance Debugging

If benchmarks are slower than expected:

1. **Check system load**: Other processes consuming resources?
2. **Verify SSD staging**: Is `/scratch/` on SSD?
3. **Check I/O patterns**: Is test data on expected storage?
4. **Monitor memory**: Are we swapping?

```bash
# System monitoring during benchmark
htop                              # CPU/memory
iostat -x 1                       # Disk I/O
nvidia-smi -l 1                   # GPU (if applicable)
watch -n1 'cat /proc/meminfo | grep -E "MemFree|Cached|Dirty"'
```

---

## Reference Results

### Production Hardware (lxd110h17)

- **CPU**: Intel Xeon Silver 4210 (40 logical cores)
- **RAM**: 128GB DDR4
- **GPU**: 2× NVIDIA RTX 2080 Ti
- **Storage**: HDD (`/data/`), NVMe SSD (`/scratch/`, `/stage/`)

| Benchmark                    | Time    | Notes                      |
| ---------------------------- | ------- | -------------------------- |
| `time_load_single_subband`   | 4.54s   | Single HDF5 file           |
| `time_load_four_subbands`    | 69s     | 4-file batch               |
| `time_convert_subband_group` | 4.05min | Full 16-subband conversion |
| `time_bandpass_single_field` | 31.1s   | 1.8M row MS                |
| `time_gaincal_single_field`  | 10.3s   | 1.8M row MS                |
| `time_applycal_single_table` | 4.08s   | Single caltable            |
| `time_reset_flags`           | 9.29s   | Full MS                    |
| `time_flag_zeros`            | 18.2s   | Full MS                    |

---

## Further Reading

- [ASV Documentation](https://asv.readthedocs.io/)
- [casabench](https://github.com/casangi/casabench) - CASA benchmark methodology
- [benchmarks/README.md](../../benchmarks/README.md) - Quick reference
