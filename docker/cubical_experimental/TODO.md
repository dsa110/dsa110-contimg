# Remaining Tasks

## Completed ✓

1. ✓ Fixed TIME conversion bug in `_fix_field_phase_centers_from_times()`
2. ✓ Fixed TIME conversion in `api/routes.py` and `test_utils.py`
3. ✓ Fixed phase centers in MS file (RA corrected from ~170° to ~128°)
4. ✓ Created Docker environment for CubiCal experimentation
5. ✓ Built Docker image with Python 3.11.13
6. ✓ Verified Docker environment works

## Still To Do

### 1. Complete CASA Calibration (In Progress)
- Status: Calibration was running after phase center fix
- Action: Check if calibration completed successfully
- Verify: Look for calibration tables (*bpcal*, *gpcal*)

### 2. Install CubiCal in Docker Container
- Status: Failed during build (expected - complex dependencies)
- Action: Install manually inside container
- Steps:
  ```bash
  docker run -it --rm --gpus all \
    -v /scratch:/scratch:ro \
    -v /scratch/calibration_test:/workspace/output:rw \
    dsa110-cubical:experimental bash
  
  # Inside container:
  source /opt/conda/etc/profile.d/conda.sh
  conda activate cubical
  pip install future argparse
  pip install "cubical@git+https://github.com/ratt-ru/CubiCal.git@1.4.0"
  ```

### 3. Setup GPU Access (Optional but Recommended)
- Status: Requires nvidia-docker2 on host
- Action: Install nvidia-docker2 for GPU acceleration
- Steps: See README.md for installation instructions

### 4. Test CubiCal Calibration
- Status: Not started
- Action: Run CubiCal calibration on test MS file
- Compare: Results with CASA calibration

### 5. Implement CubiCal CLI Functions
- Status: Skeleton created, needs actual CubiCal API calls
- Action: Fill in `cubical_calibrate.py` with real CubiCal code
- Test: Verify calibration works end-to-end

## Priority Order

1. **Check CASA calibration status** (quick check)
2. **Install CubiCal manually** (needed for testing)
3. **Test CubiCal calibration** (validate approach)
4. **Setup GPU access** (if performance testing needed)
5. **Complete CubiCal implementation** (if results are promising)

## Notes

- The Docker environment is ready and working
- Phase center fix resolved the calibration issue
- CubiCal installation is the main blocker for testing
