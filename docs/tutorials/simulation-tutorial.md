# DSA-110 Synthetic UVH5 Generator

Generate synthetic visibility data in UVH5 format for testing the DSA-110
continuum imaging pipeline. This module creates realistic multi-subband
observations that match the expected format from the DSA-110 correlator.

## Overview

The DSA-110 correlator produces **16 subbands per observation** with identical
timestamps. This generator creates test data matching that format:

```
2025-10-05T12:30:00_sb01.hdf5  # Subband 1
2025-10-05T12:30:00_sb02.hdf5  # Subband 2
...
2025-10-05T12:30:00_sb16.hdf5  # Subband 16
```

Each file contains:

- **384 channels** (DSA-110 channels per subband)
- **4 polarizations** (XX, XY, YX, YY)
- **117 antennas** (DSA-110 array minus 200E/200W)
- Realistic antenna positions from ITRF coordinates
- Phased visibility data toward a specified sky position

## Quick Start

### Generate a Single 5-Minute Observation

```bash
conda activate casa6

python simulation/make_synthetic_uvh5.py \
    --layout-meta simulation/config/reference_layout.json \
    --telescope-config simulation/pyuvsim/telescope.yaml \
    --output simulation/output/test_obs \
    --start-time "2025-10-06T12:00:00" \
    --duration-minutes 5.0 \
    --subbands 16
```

This creates 16 HDF5 files in `simulation/output/test_obs/`:

```
2025-10-06T12:00:00_sb00.hdf5
2025-10-06T12:00:00_sb01.hdf5
...
2025-10-06T12:00:00_sb15.hdf5
```

### Test with Conversion Pipeline

```bash
# Generate synthetic data
python simulation/make_synthetic_uvh5.py \
    --output /tmp/synthetic_subbands \
    --start-time "2025-10-06T12:00:00"

# Convert to Measurement Set
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /tmp/synthetic_subbands \
    /tmp/test_ms \
    "2025-10-06 12:00:00" \
    "2025-10-06 12:05:00"
```

## Configuration Files

### `reference_layout.json`

Metadata extracted from real DSA-110 observations:

- Frequency array (384 channels × 16 subbands = 6144 total channels)
- Channel width: -244.140625 kHz (descending frequency order)
- Integration time: ~12.88 seconds
- LST array, antenna configuration

### `telescope.yaml`

Telescope configuration parameters:

```yaml
site:
  latitude_deg: 37.23398 # OVRO latitude
  longitude_deg: -118.2821 # OVRO longitude
  altitude_m: 1188.0 # OVRO elevation

spectral:
  num_subbands: 16
  channels_per_subband: 384
  channel_width_hz: -244140.625 # Negative = descending
  reference_frequency_hz: 1487153319.6875

temporal:
  integration_time_sec: 12.88
  total_duration_sec: 300 # 5 minutes

phase_center:
  ra_deg: 10.0 # Right ascension
  dec_deg: 54.6 # Declination
```

## Command-Line Options

### Required Arguments

- `--layout-meta PATH` - JSON metadata from reference observation
- `--telescope-config PATH` - Telescope configuration YAML

### Optional Arguments

#### Output Configuration

- `--output PATH` - Output directory (default: `simulation/output`)
- `--subbands N` - Number of subbands to generate (default: 16)
- `--shuffle-subbands` - Randomize file creation order to test ingestion

#### Observation Parameters

- `--start-time "YYYY-MM-DDTHH:MM:SS"` - Observation start time UTC (default:
  2025-01-01T00:00:00)
- `--duration-minutes N` - Observation duration in minutes (default: 5.0)
- `--flux-jy N` - Calibrator flux density in Janskys (default: 25.0)

#### Frequency Configuration

- `--freq-order {asc,desc}` - Frequency ordering per subband (default: desc)

#### Template

- `--template PATH` - Reference UVH5 file for metadata scaffolding

## Usage Examples

### 1. Quick Test (Single Observation)

```bash
python simulation/make_synthetic_uvh5.py \
    --output /tmp/quick_test \
    --start-time "2025-10-06T12:00:00" \
    --duration-minutes 5 \
    --flux-jy 25.0
```

### 2. Bright Calibrator (100 Jy)

```bash
python simulation/make_synthetic_uvh5.py \
    --output /tmp/bright_cal \
    --start-time "2025-10-06T15:30:00" \
    --flux-jy 100.0 \
    --subbands 16
```

### 3. Testing Subband Ordering

```bash
# Generate with shuffled write order
python simulation/make_synthetic_uvh5.py \
    --output /tmp/shuffle_test \
    --shuffle-subbands \
    --start-time "2025-10-06T20:00:00"

# Streaming converter should handle any arrival order
python -m dsa110_contimg.conversion.streaming.streaming_converter \
    --input-dir /tmp/shuffle_test \
    --output-dir /tmp/test_ms
```

### 4. Multiple Observation Groups

```bash
# Generate 3 observation groups (15 minutes total)
for i in 0 5 10; do
    python simulation/make_synthetic_uvh5.py \
        --output /tmp/multi_obs \
        --start-time "2025-10-06T12:$(printf %02d $i):00" \
        --duration-minutes 5
done

# Results in:
# 2025-10-06T12:00:00_sb*.hdf5  (16 files)
# 2025-10-06T12:05:00_sb*.hdf5  (16 files)
# 2025-10-06T12:10:00_sb*.hdf5  (16 files)
```

## Technical Details

### Data Generation Process

1. **Load Template**: Reads reference UVH5 file for metadata structure
2. **Build Time Arrays**: Creates time/LST arrays based on integration time
3. **Calculate UVW**: Computes baseline UVW coordinates using CASA measures
4. **Generate Visibilities**: Creates point-source visibilities with specified
   flux
5. **Write Subbands**: Outputs 16 separate HDF5 files with correct frequency
   ranges

### Frequency Structure

Each subband has 384 channels. For descending order (default):

```python
subband_00: 1498.6 - 1405.1 MHz (highest frequencies)
subband_01: 1405.1 - 1311.6 MHz
...
subband_15: 1030.0 -  936.5 MHz (lowest frequencies)
```

Total bandwidth: ~562 MHz (1498.6 - 936.5 MHz)

### Antenna Positions

Loads ITRF coordinates from `DSA110_Station_Coordinates.csv`:

- 117 antennas (stations 1-117)
- Excludes 200E and 200W
- Relative to OVRO array center

### Phase Center

All visibilities are phased toward a specified RA/Dec:

- Default: RA=10.0°, Dec=54.6° (from telescope.yaml)
- Stored in MS-compatible phase center metadata
- UVW coordinates calculated relative to this direction

## Integration with Pipeline

The synthetic data is designed to work seamlessly with both converters:

### Batch Converter

```bash
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /path/to/synthetic/subbands \
    /path/to/output/ms \
    "2025-10-06 00:00:00" \
    "2025-10-06 23:59:59"
```

### Streaming Converter

```bash
python -m dsa110_contimg.conversion.streaming.streaming_converter \
    --input-dir /path/to/synthetic/subbands \
    --output-dir /path/to/output/ms \
    --chunk-duration 5.0
```

Both will:

1. Group files by timestamp
2. Combine 16 subbands into single observation
3. Create CASA Measurement Set
4. Add imaging columns and antenna positions

## Validation

### Check Generated Files

```bash
# List generated subbands
ls -lh simulation/output/*.hdf5

# Verify with pyuvdata
python -c "
from pyuvdata import UVData
uv = UVData()
uv.read('simulation/output/2025-10-06T12:00:00_sb00.hdf5')
print(f'Nants: {uv.Nants_telescope}')
print(f'Nfreqs: {uv.Nfreqs}')
print(f'Npols: {uv.Npols}')
print(f'Ntimes: {uv.Ntimes}')
print(f'Integration: {uv.integration_time[0]:.2f}s')
"
```

Expected output:

```
Nants: 117
Nfreqs: 384
Npols: 4
Ntimes: 23  # For 5-minute obs with ~12.88s integration
Integration: 12.88s
```

### Validate Conversion

```python
# After converting to MS
from casacore.tables import table

with table('output.ms') as tb:
    print(f"Rows: {tb.nrows()}")
    print(f"Columns: {tb.colnames()}")
    data = tb.getcol('DATA')
    print(f"Data shape: {data.shape}")
```

## Troubleshooting

### ImportError: No module named 'yaml'

```bash
conda activate casa6
conda install pyyaml
```

### Missing antenna positions

```bash
# Ensure antenna CSV exists
ls pipeline/pipeline/utils/data/DSA110_Station_Coordinates.csv

# Or use local copy
ls antpos_local/data/DSA110_Station_Coordinates.csv
```

### Template file not found

```bash
# Default template may not exist yet
# Generate one first or specify custom template:
--template /path/to/existing/file.hdf5
```

### Frequency mismatch warnings

```
WARNING: Requested 16 subbands, but configuration expects 8.
```

This is normal if using a template from an 8-subband observation. The generator
will still create the requested number.

## Performance

Typical generation times (on 8-core system):

- **Single observation (16 subbands, 5 min)**: ~30-60 seconds
- **Per subband**: ~2-4 seconds
- **Memory usage**: ~500 MB - 2 GB depending on observation duration

## Advanced Usage

### Custom Source Position

Edit `telescope.yaml`:

```yaml
phase_center:
  ra_deg: 123.45 # Your RA
  dec_deg: -12.34 # Your Dec
```

### Longer Observations

```bash
# Generate 1-hour observation (12 groups of 5 minutes each)
for i in {0..55..5}; do
    python simulation/make_synthetic_uvh5.py \
        --output /tmp/long_obs \
        --start-time "2025-10-06T12:$(printf %02d $i):00" \
        --duration-minutes 5
done
```

### Custom Flux Calibrators

```bash
# 3C286 (typical ~15 Jy at L-band)
--flux-jy 15.0

# 3C48 (typical ~30 Jy at L-band)
--flux-jy 30.0

# Very bright pulsar (hundreds of Jy)
--flux-jy 500.0
```

## Known Limitations

1. **Point source only**: All flux in a single point at phase center
2. **No noise**: Visibilities are noise-free
3. **No RFI**: No simulated interference
4. **Perfect calibration**: No antenna-based gains or delays
5. **Static sky**: Source flux doesn't vary with time

Future enhancements could add:

- Extended source models
- Realistic thermal noise
- RFI contamination
- Time-variable sources
- Multiple sources in field

## See Also

- [Conversion Pipeline Documentation](../how-to/uvh5_to_ms_conversion.md)
- [Streaming Converter Guide](../how-to/streaming_converter_guide.md)
- [PyUVData Documentation](https://pyuvdata.readthedocs.io/)

## Support

For issues or questions:

1. Check that conda `casa6` environment is activated
2. Verify all dependencies are installed (see `environment.yml`)
3. Test with default parameters first before customization
4. Check generated files with pyuvdata validation utilities
