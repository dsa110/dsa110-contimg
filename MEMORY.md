# DSA-110 Continuum Imaging Project Memory

## Key Lessons and Principles

### UVH5 to MS Conversion Process

1. **Circular Import Issues**: The `uvh5_to_ms_converter_v2.py` had circular import dependencies that were resolved by:
   - Implementing lazy imports in `dsa110_contimg.conversion.__init__.py`
   - Creating missing modules (`writers.py`) and functions (`write_ms_from_subbands`)
   - Using direcports from specific modules rather than package-level imports

2. **FUSE Temporary Files**: Large `.fuse_hidden*` files (70+ GB each) are created during MS writing operations:
   - These are temporary files created by FUSE filesystems during large data operations
   - They can accumulate in multiple locations: root directory, MS directories, and QA directories
   - They can accumulate if processes don't clean up properly
   - Use `sudo fuser -k` and `sudo rm -f` to force cleanup when processes hold file descriptors
   - Normal behavior for CASA/pyuvdata operations writing large datasets
   - Total cleanup freed ~400GB of disk space (from 5.1T to 4.7T usage)

3. **Python Environment**: The system requires:
   - `casa6` conda environment for `pyuvdata` and CASA tools
   - `PYTHONPATH=/data/dsa110-contimg/src` for package imports
   - Python 3.11 (not Python 2.7) for modern syntax support

4. **Conversion Success**: The v2 converter successfully:
   - Groups subbands by timestamp (30s tolerance)
   - Merges frequency channels in ascending order
   - Creates proper CASA Measurement Sets with UVW coordinates
   - Finds and creates calibrator MS files with MODEL_DATA
   - Uses direct subband writer for optimal performance
   - Preallocates `MODEL_DATA`/`CORRECTED_DATA` after writing to avoid CASA errors
5. **Module Layout**: Active conversion code now lives in `dsa110_contimg/conversion/` (helpers, batch converter, streaming daemon, strategy writers). Legacy implementations are archived under `archive/legacy/core_conversion/`; imports from `dsa110_contimg.core.conversion` are no longer supported.

### File Structure
- Input: `/data/incoming/` (UVH5 subband files)
- Output: `/data/dsa110-contimg/data-samples/ms/` (CASA MS files)
- QA: `/data/dsa110-contimg/state/qa/` (Quality assurance plots)

### Common Issues and Solutions
- **ImportError**: Check PYTHONPATH and conda environment
- **Circular imports**: Use lazy imports and direct module references
- **Outdated import paths**: Update any remaining `dsa110_contimg.core.conversion.*` imports to `dsa110_contimg.conversion.*`
- **Large temp files**: Monitor for `.fuse_hidden*` files and clean up if needed
- **Missing modules**: Create required modules and functions as needed
- **CASA Calibrater error (no array in MODEL_DATA row)**: If `MODEL_DATA` exists but arrays are uninitialized, CASA `gaincal`/`bandpass` can fail with "TSM: no array in row ... of column MODEL_DATA". Fix by preallocating `MODEL_DATA` (unity or zeros) and initializing `CORRECTED_DATA` across all rows after MS write. The converter now does this automatically.

### Recent Fixes (2025-10-10 → 2025-10-13)
- Field selection in delay solve now honors CASA-style names/ranges: numeric IDs, `A~B`, comma lists, and glob matches against `FIELD::NAME`. This removes a crash when `--field` is a name.
- Calibration table prefixes now use `os.path.splitext(ms)[0]` instead of `rstrip('.ms')`, preventing accidental truncation (e.g., `runs.ms` → `runs`, not `run`).
- Streaming converter now uses the strategy orchestrator (writer=`direct-subband`) in both subprocess and in‑process paths; writer type is recorded in metrics.
- Products DB helpers added: centralized `ms_index`/`images` schema management, upserts, and indices.
- API/monitoring integrates recent calibrator matches and QA discovery.

# Currently Working On:

## Calibration Recovery & Execution Plan (2025-10-10)

Context
- Current abort during calibration is thrown by casatools (gaincal/msmetadata) when opening the MS produced by the dask‑ms writer: `RecordInterface: field type is unknown`.
- casacore opens the MS and subtables fine; the failure is specific to casatools parsing a record in the dask‑ms‑written MS.
- Goal is to reach a clean calibration on the 5‑min group `0834_555_transit` and then re‑enable features incrementally.

High‑Level Strategy
- First produce a CASA‑friendly MS (non‑dask writer, single FIELD) and calibrate successfully.
- Then reintroduce options (combine across fields, per‑integration FIELDs, dask‑ms) one at a time, validating at each step.

Phase 1 — Rebuild MS without dask-ms
- Why: Avoid the casatools/dask‑ms record incompatibility.
- Action: Run `scripts/run_conversion.sh` (uses the strategy orchestrator with the `direct-subband` writer by default). The converter preallocates imaging columns and `MODEL_DATA` to prevent CASA errors.
- Outcome: casatools `msmetadata.open()` succeeds.

Phase 2 — Validate with casatools and run calibration (no combine)
- Quick checks:
  - `from casatools import msmetadata; md=msmetadata(); md.open(<MS>); md.close()`
  - `from casatasks import gaincal; gaincal(vis=<MS>, caltable='/tmp/k', field='23', solint='inf', refant='67', gaintype='K', combine='scan,obs')`
- Calibration run:
  - `scripts/calibrate_bandpass.sh --ms <MS> --no-combine`
  - The script auto‑selects fields via catalog, uses refant from QA ranking, and keeps pre‑solve flagging off by default (toggle with `--flagging` if needed).
  - Fix applied: calibration now correctly honors `--no-combine` (previously always combined due to a bug).

Phase 3 — Incrementally re‑enable features
- Combine across fields:
  - Re‑run without `--no-combine` (or pass `--combine`) to produce a single BP/G solution across the selected window.
  - If K/BP/G succeed, keep combine enabled where beneficial.
- Per‑integration FIELDs:
  - pyuvdata default already yields per‑integration FIELDs; calibration now succeeds with this structure.
- dask‑ms writer:
  - Re‑enable `--dask-write` and validate: `msmetadata.open()` and a `gaincal` smoke test must succeed before full calibration.
  - If casatools aborts again, revert to non‑dask writer for calibration‑grade outputs.

Phase 4 — Optional post‑write normalization for dask‑ms
- If dask‑ms must be used, add a post‑write normalizer that:
  - Attaches canonical MEASINFO to `TIME`, `TIME_CENTROID` (`{'Ref':'UTC','Type':'Epoch'}`) and `UVW` (`{'Ref':'ITRF','Type':'UVW'}`).
  - Verifies presence and shapes of `RESOLUTION`/`EFFECTIVE_BW`, `SIGMA`/`WEIGHT`, `WEIGHT_SPECTRUM`.
  - Uses a `msmetadata.open()` check as a gate before exposing the MS to solvers.

Operational Notes
- `scripts/calibrate_bandpass.sh`
  - Combine is controlled by `--combine` / `--no-combine` (default in repo is `COMBINE=false`).
  - Pre‑solve flagging is off by default; enable with `--flagging` for stability if needed.
- `scripts/run_conversion.sh`
  - For calibration‑grade runs, prefer the non‑dask path unless dask‑ms is explicitly required.

Status & Decisions
- msfix and the `--msfix` flag have been removed; we will not patch MS metadata during calibration. Prefer reconversion or the normalizer described above.
- Root cause under investigation: casatools/dask‑ms record handling edge case on MS written with per‑integration FIELDs; non‑dask writers remain robust in our CASA 6.7 env.

Next Actions (as of 2025‑10‑10)
1) Reconvert `0834_555_transit` without dask‑ms and `--field-per-integration`.
2) Validate with `msmetadata.open()`; run `gaincal` smoke test.
3) Run full calibration via `calibrate_bandpass.sh --no-combine`.
4) If success, re‑enable combine; then test per‑integration FIELDs; finally test dask‑ms with the normalizer.
5) If dask‑ms remains unstable with casatools, keep the non‑dask writer for calibration‑grade products.


### Scratch Workflow for High I/O Jobs
- **Staging area**: Heavy CASA conversions should run on the NVMe SSD at `/scratch/dsa110-contimg` (ext4) for fast writes.
- **Sync helpers**: Use `scripts/scratch_sync.sh` to move data between `/data/dsa110-contimg` and the scratch area. Examples:
  - `scripts/scratch_sync.sh stage data-samples/ms/run123` (copy from `/data` to `/scratch`)
  - `scripts/scratch_sync.sh archive data-samples/ms/run123 --delete` (mirror back to `/data`)
  - `scripts/scratch_sync.sh clean data-samples/ms/run123` (remove staged copy after archiving)
- **Monitor space**: `scripts/scratch_sync.sh status` reports usage; keep at least ~100 GB free on the root filesystem.
- **Workflow tip**: Run converters with output paths under `/scratch/dsa110-contimg`, validate results, then archive to `/data` once finalized.
- **Hands-on**: `docs/notebooks/ms_staging_workflow.ipynb` walks through the staging workflow step by step (status, optional input staging, conversion, archiving, cleanup).
- **Quicklooks**: Generate shadeMS / ragavi artifacts without reconversion via `python -m dsa110_contimg.qa.quicklooks --ms <path/to.ms> [--ragavi]`.
- **Fast QA**: Use `python -m dsa110_contimg.qa.fast_plots --ms <ms>` for matplotlib-based amplitude/time/frequency/UV plots without CASA; integrate via `--fast-plots` when calling `qa.quicklooks`.

### Calibration Pipeline Architecture
- **Modular Design**: The calibration system is split into focused modules:
  - `calibration.py`: Core CASA task wrappers (delay, bandpass, gain solving)
  - `selection.py`: Field selection algorithms using primary beam weighting
  - `catalogs.py`: VLA calibrator catalog integration
  - `flagging.py`: RFI and data quality flagging
  - `qa.py`: Quality assurance plotting and analysis
  - `cli.py`: Command-line interface with auto-field selection
- **Auto-Field Selection**: The system can automatically select optimal fields for bandpass calibration using:
  - Primary beam response weighting at 1.4 GHz
  - VLA calibrator catalog search within configurable radius
  - Contiguous field window selection based on PB gain thresholds
  - Fallback to fixed window size if threshold-based selection fails
- **Reference Antenna Selection**: Uses QA analysis to rank antennas and automatically select the best reference antenna
- **Calibration Strategy**: Three-stage approach:
  1. **Delay (K) solve**: Slow timescale delay correction on peak field
  2. **Bandpass (BP) solve**: Two-stage amplitude then phase bandpass correction
  3. **Gain (G) solve**: Amplitude and phase gain correction with optional flux scaling
- **Field Combination**: Option to combine solutions across multiple fields for more robust calibration
- **Environment Stability**: Uses single-threaded CASA execution to avoid stability issues in Jupyter environments

### MS Writing Strategies
- Primary: `direct-subband` writer via the strategy orchestrator (parallel per‑subband MS writes + CASA concat inside the writer).
- Alternative: `pyuvdata` monolithic writer (`UVData.write_ms`) when needed.
- Historical: dask‑ms writer path existed; avoid for CASA compatibility.
- Validation: Post‑write checks and imaging‑column initialization are in place to keep CASA happy.

### Workflow Scripts
- **run_conversion.sh**: End‑to‑end conversion with the strategy orchestrator (`direct-subband` by default), optional SSD staging, and validation helpers; see `scripts/run_conversion.sh`.
- **calibrate_bandpass.sh**: End-to-end calibration script with:
  - Auto-field selection using VLA catalog
  - Reference antenna ranking via QA analysis
  - Configurable primary beam thresholds
  - Optional field combination for robust solutions

### Calibration Issues and Solutions
- **Field-per-Integration MS Calibration**: When using field-per-integration mode (24 fields), CASA calibration tasks can fail with:
  - "Array has no elements" errors due to empty arrays from `minMax` function
  - "RecordInterface: field type is unknown" errors due to MS structure incompatibility
  - Poor SNR solutions when trying to solve for each field individually
- **Solutions**:
  - Use the orchestrator `direct-subband` or pyuvdata writer; avoid dask‑ms for CASA workflows
  - Prefer catalog-driven MODEL_DATA via CASA ft: write a point-source model at the catalog calibrator (RA/Dec/flux) before bandpass
  - Keep `smodel=[]` only as a fallback if no calibrator match is available
  - Use peak field only as the reference for K/BP selection; select data over the requested window
  - Solver defaults aligned with reference pipeline:
    - Bandpass: `solint='inf'`, `minsnr=5.0`, `selectdata=True`, `combine='scan,field'` when combining (otherwise "")
    - Gains: `solint='inf'` (and optional short), `minsnr=5.0`, `selectdata=True`, `combine='scan,field'` when combining
  - Combine remains configurable; default is no cross-field combine
  - Mount Type Warnings: CASA warnings about "unhandled mount type" stem from ANTENNA::MOUNT; converter now writes `alt-az`
  - Key fix: When using ranges like "19~23", use the peak field for reference, but select the full range for data

### Calibration Defaults (aligned with dsa110_hi)
- MODEL_DATA: populated via catalog-driven CASA ft (point source at RA/Dec with known flux). `setjy` not used in bandpass.
- Bandpass: `solint='inf'`, `minsnr=5.0`, `selectdata=True`, `combine='scan,field'` only when requested.
- Gains: `solint='inf'` (plus optional short), `minsnr=5.0`, `selectdata=True`, `combine='scan,field'` only when requested.
- Delay: robust K step on peak field; conservative retry path retained.

### CalibratorSearch Tool (future)
- Planned: web‑based calibrator selection dashboard building on existing API endpoints and catalog tools.
- **Architecture**:
  - Main notebook: Interactive widgets and UI
  - Helper module: `calibrator_helper.py` with core functionality
  - Clean separation of UI and data processing logic
- **Key Functions**:
  - `load_pointing()`: Reads MS/UVH5 files, extracts pointing and timing info
  - `candidates_near_pointing()`: Finds calibrators within declination band and flux cut
  - `score_calibrators()`: Calculates PB response, weighted flux, altitude at observation
  - `plot_altitude_tracks()`: Generates 24-hour altitude plots with transit analysis
- **Improvements (2025-01-10)**:
  - Fixed syntax error in notebook JSON structure
  - Added comprehensive error handling and input validation
  - Implemented catalog caching for improved performance
  - Enhanced documentation with detailed docstrings and examples
  - Added progress indicators for long operations
  - Improved visual output with better formatting and status indicators
  - Added robust error recovery and user feedback

### DSA110 Shell Repository Structure (2025-10-12)

**Overview for New Developers**

The DSA110 project uses a meta-repository approach with `~/proj/dsa110-shell/` containing **25+ individual repositories** managed via `myrepo (mr)`. This modular architecture separates concerns across specialized components, making it easier for developers to work on specific aspects without affecting the entire system.

**Getting Started:**
```bash
# Clone the shell repository
git clone git@github.com/dsa110/dsa110-shell dsa110
cd dsa110

# Add to myrepo trust
echo "<path-to-dsa110/.mrconfig>" >> ~/.mrtrust

# Checkout all repositories
mr checkout
```

**Core Infrastructure Repositories:**
- **`dsa110-calib/`** - Calibration system
  - Handles delay, bandpass, and gain calibration
  - Integrates with CASA calibration tasks
  - Python-based with conda environment requirements
- **`dsa110-antpos/`** - Antenna positioning
  - Manages antenna coordinates and pointing models
  - Critical for accurate source tracking
- **`dsa110-alignment/`** - Pointing and alignment
  - Pointing measurements and corrections
  - Contains historical pointing test data
- **`dsa110-cnf/`** - Configuration files and YAML configs
  - Centralized configuration management
  - Contains antenna calibration files, service configs
  - Push to etcd functionality for distributed configs
- **`dsa110-controlscripts/`** - Control and scheduling scripts
  - Observation scheduling and execution
  - Catalog management for calibrator sources
  - Restart and monitoring utilities

**Data Processing Pipeline:**
- **`dsa110-psrdada/`** - PSRDADA (Pulsar Data Archive) implementation
  - Core data acquisition and buffering system
  - C-based with Python bindings
  - Handles real-time data streaming from correlator
- **`dsa110-sigproc/`** - Signal processing utilities
  - C-based signal processing functions
  - Used for data format conversions and preprocessing
- **`dsa110-xengine/`** - Correlation engine
  - FPGA-based correlation processing
  - Handles real-time correlation of antenna signals
- **`dsa110-xGPU/`** - GPU acceleration
  - CUDA-based processing for computationally intensive tasks
  - Used for fast Fourier transforms and other GPU-accelerated operations
- **`dsa110-mbheimdall/`** - Heimdall burst search pipeline
  - Real-time transient detection and classification
  - C++/CUDA implementation for fast processing

**Software Components:**
- **`dsa110-pyutils/`** - Python utilities
  - Common Python functions and classes
  - Shared across multiple repositories
  - Includes service management and deployment tools
- **`dsa110-scheduler/`** - Scheduling system
  - Celery-based task scheduling
  - Handles observation planning and execution
- **`dsa110-vis/`** - Visualization tools
  - Data visualization and plotting utilities
  - Quality assurance plots and analysis
- **`dsa110-meridian-fs/`** - Meridian filesystem
  - Custom filesystem for data management
  - Handles large-scale data storage and retrieval
- **`dsa110-hwmc/`** - Hardware monitoring and control
  - Real-time hardware status monitoring
  - Control interfaces for telescope subsystems

**External Dependencies:**
- **`pyuvdata/`** - UV data handling
  - Standard radio astronomy data format library
  - Used for reading/writing UVH5 and MS files
- **`psrdada-python/`** - Python bindings for PSRDADA
  - Python interface to PSRDADA C library
- **`dsalabjack-py/`** - LabJack hardware interface
  - Python interface for LabJack data acquisition hardware
- **`mcant-py/`** - Antenna control
  - Python interface for antenna positioning systems

**Development Workflow:**
- **Repository Management**: Uses `myrepo (mr)` for multi-repository management
  - `.mrconfig` file defines all repository locations and branches
  - `mr checkout` clones all repositories
  - `mr update` updates all repositories to latest versions
- **Version Control**: Semantic versioning across all repositories
  - `main` branch for active development
  - `master` branch for production releases
  - Version tags follow semver (major.minor.patch)
- **Deployment**: Automated deployment scripts
  - `deploy` and `deploy_screen.bash` for production deployments
  - `check_versions.sh` for version consistency checking

**Data Flow Architecture:**
```
Hardware Control → Data Acquisition → Correlation → Calibration → Analysis
     ↓                    ↓              ↓           ↓           ↓
dsa110-hwmc/    dsa110-psrdada/  dsa110-xengine/  dsa110-calib/  dsa110-vis/
dsa110-antpos/   dsa110-sigproc/  dsa110-xGPU/    dsa110-pyutils/ analysis tools
dsa110-alignment/                  dsa110-mbheimdall/
```

**Key Development Principles:**
- **Modular Design**: Each repository handles a specific aspect of telescope operation
- **Independent Development**: Teams can work on different components without conflicts
- **Centralized Configuration**: All configs managed through `dsa110-cnf/`
- **Clear Interfaces**: Well-defined APIs between components
- **External Integration**: Seamless integration with standard radio astronomy tools (CASA, PSRDADA, etc.)
- **Testing**: Each repository has its own test suite and CI/CD pipeline

**For New Developers:**
1. Start with `dsa110-pyutils/` to understand common utilities
2. Review `dsa110-cnf/` to understand system configuration
3. Examine `dsa110-calib/` for calibration workflows
4. Check `dsa110-controlscripts/` for operational procedures
5. Use `dsa110-vis/` for data visualization and analysis

This structure supports the continuum imaging workflow where data flows from hardware control through data acquisition, correlation, calibration, and finally to analysis, with each stage handled by specialized repositories.

### Calibrator Analysis Pipeline (2025-10-12)

**Critical Lesson: UVH5 Declination Storage Format**
- **UVH5 files store declination in RADIANS, not degrees** in the `phase_center_dec` field
- **Common Error**: Using the raw value (e.g., 0.952486) as degrees instead of converting from radians
- **Correct Conversion**: `dec_deg = np.degrees(dec_rad)` where `dec_rad` is the stored value
- **Verification Method**: Check fringestopping table filename (e.g., `fringestopping_table_dec54.6deg_96ant.npz`) to confirm actual pointing
- **Impact**: Using wrong declination leads to completely incorrect calibrator selection (wrong part of sky)

**Drift-Scan Calibrator Analysis (Corrected Understanding)**
- **Telescope Pointing vs. Latitude**: Telescope pointing declination (54.6°) determines primary beam coverage, not telescope latitude (37.2°)
- **Primary Beam Coverage**: ~3.16° × 3.16° field of view centered on pointing declination
- **Time in Primary Beam**: ~12.6 minutes for calibrators at same declination as pointing
- **5-Minute Data Dumps**: Focus on specific dumps containing calibrator transit peaks, not 30-minute scheduling windows
- **Continuous Observation**: No setup time or scheduling flexibility needed for drift-scan mode

**Calibrator Selection for Drift-Scan**
- **Declination Range**: ±1.5° around telescope pointing declination (not latitude!)
- **Transit Dump Analysis**: Find which 5-minute dump contains each calibrator's transit peak
- **Primary Beam Response**: Calculate if calibrator is within primary beam during its transit dump
- **Elevation Optimization**: Prioritize calibrators with highest elevation during transit
- **Flux Density Scoring**: Multi-band flux analysis for calibration quality assessment

**Pipeline Integration**
- **Drift-Scan Focused**: Algorithm designed for continuous drift-scan observations
- **Dump-Specific Results**: Outputs specific 5-minute dumps containing optimal calibrators
- **Primary Beam Awareness**: Only considers calibrators that actually enter the primary beam
- **Real-Time Ready**: Suitable for streaming pipeline integration

**Key Corrections from Previous Understanding**
- **30-minute windows are inappropriate** for drift-scan observations
- **Telescope pointing declination** (not latitude) determines calibrator visibility
- **5-minute data dumps** are the relevant time windows for calibrator selection
- **Primary beam coverage** is centered on pointing direction, not zenith

### Comprehensive Pipeline Testing Plan (2025-10-12)

**Testing Strategy Overview**
- **6 Testing Phases**: From UVH5 conversion through bandpass calibration
- **Drift-Scan Focused**: Specifically designed for continuous drift-scan observations
- **5-Minute Dump Awareness**: Tests the new calibrator analysis approach
- **Comprehensive Validation**: Covers data integrity, performance, and quality
- **Error Handling**: Tests robustness and recovery mechanisms

**Phase 1: UVH5 to MS Conversion Testing**
- **Single Subband Conversion**: Verify basic conversion functionality with MS structure validation
- **Multi-Subband Conversion**: Test full observation conversion with 16 subband files
- **MS Structure Validation**: Use CASA tools to validate antenna table, field table, l window table
- **Validation Criteria**: MS opens without errors, data dimensions correct, no corrupted data

**Phase 2: Calibrator Analysis Testing**
- **Drift-Scan Calibrator Selection**: Test updated analysis with 5-minute dump identification
- **Primary Beam Response**: Calculate if calibrators are within primary beam during transit dumps
- **Calibrator Quality Assessment**: Validate flux density measurements and elevation optimization

**Phase 3: Calibration Pipeline Testing**
- **Model Data Preparation**: Create point-source models in MODEL_DATA column for calibrators
- **Delay Calibration (K-step)**: Test on peak field with reference antenna selection
- **Bandpass Calibration (BP-step)**: Test with prepared model and field combination
- **Gain Calibration (G-step)**: Test amplitude and phase solutions with flux scaling

**Phase 4: End-to-End Pipeline Testing**
- **Full Pipeline Execution**: Complete pipeline from UVH5 to calibrated MS
- **Data Quality Assessment**: Compare pre/post calibration data with noise reduction measurement
- **Success Criteria**: >2x noise reduction, <50% flagging fraction, no data corruption

**Phase 5: Performance and Robustness Testing**
- **Multi-Subband Calibration**: Test across all 16 subbands with consistency validation
- **Error Handling**: Test with corrupted data, missing calibrators, insufficient SNR
- **Recovery Mechanisms**: Verify graceful error handling and appropriate error messages

**Phase 6: Validation and Documentation**
- **Results Validation**: Compare with reference pipeline and validate metrics
- **Documentation Update**: Update MEMORY.md with test results and troubleshooting guide
- **Performance Benchmarks**: Document processing time, memory usage, and quality metrics

**Critical Success Criteria**
- **All pipeline steps complete without errors**
- **Calibration improves data quality by >2x**
- **Processing time <60 minutes for full observation**
- **Memory usage <16 GB**
- **No data corruption or loss**

**Test Execution Schedule**
- **Day 1**: Conversion testing (single and multi-subband)
- **Day 2**: Calibrator analysis and quality assessment
- **Day 3**: Calibration pipeline (K, BP, G steps)
- **Day 4**: End-to-end testing and data quality assessment
- **Day 5**: Performance testing and validation

**Rollback Plan**
- **Immediate**: Revert to last known good configuration
- **Short-term**: Use reference pipeline for production
- **Long-term**: Fix issues and re-run testing

**Monitoring and Logging**
- **Log Files**: Conversion, calibration, and analysis logs in structured directories
- **Real-time Monitoring**: Progress tracking, resource usage, error detection
- **Performance Metrics**: Collection and analysis of processing statistics

## Streaming Pipeline Status (2025-10-13)

This documents the current end-to-end streaming path and operational knobs.

### Components and Entry Points
- Conversion: `dsa110_contimg.conversion.uvh5_to_ms` (single/dir)
- Streaming service: `dsa110_contimg.conversion.streaming_converter`
- Calibration solves: `dsa110_contimg.calibration.calibration` (K/BP/G)
- Apply calibration: `dsa110_contimg.calibration.applycal.apply_to_target`
- Imaging: `dsa110_contimg.imaging.cli.image_ms`
- QA: `dsa110_contimg.qa.fast_plots` (supports `--bcal`)
- Registry: `dsa110_contimg.database.registry` (register/applylist)

### Implemented Flow
1. Detect complete 16‑subband group (via QueueDB). Stage subbands (symlink or copy).
2. Convert all subbands to per‑subband `.ms` (uvh5_to_ms.convert_directory).
3. Concatenate to `<group_id>.ms` (multi‑SPW) using CASA `concat`.
4. Calibrator group:
   - Use QA to auto-identify suitable refant.
   - Solve delay (K), bandpass (BA+BP), gains (GA+GP, optional 2G).
   - Register set in calibration registry with ±30 min window around mid‑MJD.
   - Generate QA: fast plots for MS and per‑antenna Bcal plots (`_bpcal`).
5. Target group:
   - Lookup registry `get_active_applylist(mjd)` and `applycal` to `<group_id>.ms`.
   - Image with `image_ms` (PB-corrected, FITS exported when present).

### Stage Tracking (PIPELINE_PRODUCTS_DB)
- If `PIPELINE_PRODUCTS_DB` is set, streaming upserts `ms_index` at each step:
  - `concatenated`: after CASA concat.
  - `calibrated`: after K/BP/G and registry registration.
  - `applycal_done` / `applycal_failed`: after applying caltables.
  - `imaged`: after imaging; sets `imagename`, `processed_at`, `status=done`.
- `start_mjd`, `end_mjd`, `mid_mjd` are filled on first touch via `msmetadata`.
- Image artifacts recorded in `images` for `.image`, `.pb`, `.pbcor`, `.residual`, `.model` when present.

### Runtime Policies (Environment)
- `PIPELINE_PRODUCTS_DB`: SQLite path for `ms_index`/`images` (optional).
- `PIPELINE_STATE_DIR`: base for QA outputs (default `state`).
- `BP_MINSNR`: bandpass min SNR (float; default 5.0).
- Imaging params for `image_ms`:
  - `IMG_IMSIZE` (int; default 1024)
  - `IMG_ROBUST` (float; default 0.0)
  - `IMG_NITER` (int; default 1000)
  - `IMG_THRESHOLD` (str; default `0.0Jy`)

### Converter Guarantees
- Imaging columns (`MODEL_DATA`, `CORRECTED_DATA`) preallocated post‑write to prevent CASA concat/solver errors (TSM array issues).
- Explicit midpoint phasing before MS write to ensure consistent phase center.

### What’s Working
- End‑to‑end streaming for both calibrator and target groups.
- Calibration registry registration and applylist retrieval.
- QA generation post‑calibration including Bcal per‑antenna pages.
- Stage tracking and artifact cataloging when `PIPELINE_PRODUCTS_DB` is set.

### Potential Next Steps
- Add refant override from QA ranking.
- Per‑stage timing metrics into `ms_index`.
- Lightweight dashboard reading `ms_index`/`images` for live ops.
