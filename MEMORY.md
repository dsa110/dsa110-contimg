# DSA-110 Continuous Imaging Project Memory

## Key Lessons and Principles

### UVH5 to MS Conversion Process

1. **Circular Import Issues**: The `uvh5_to_ms_converter_v2.py` had circular import dependencies that were resolved by:
   - Implementing lazy imports in `dsa110_contimg.conversion.__init__.py`
   - Creating missing modules (`writers.py`) and functions (`write_ms_from_subbands`)
   - Using direct imports from specific modules rather than package-level imports

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
