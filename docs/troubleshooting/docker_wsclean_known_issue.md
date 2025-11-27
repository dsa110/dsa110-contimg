# Docker WSClean Container Cleanup Hang - Known Issue

**Date:** 2025-11-19  
**Type:** Known Limitation  
**Status:** 🔴 Unresolved (Workaround Available)

---

## Problem

Docker-based WSClean `-predict` operations consistently hang at "Cleaning up
temporary files..." and never complete, even with timeouts added to
subprocess.run().

## Symptoms

```
Writing changed model back to /data_ms/2025-10-19T14:31:45.ms:
 0%....10%....20%....30%....40%....50%....60%....70%....80%....90%....100%
Cleaning up temporary files...
[HANGS INDEFINITELY - timeouts don't trigger]
```

## Affected Operations

- NVSS sky model prediction (`-predict` with Docker WSClean)
- Any Docker WSClean operation that writes to MS MODEL_DATA
- Specifically: Self-calibration with `use_nvss_seeding=True`

## Root Cause (Suspected)

**Docker volume unmounting after container completion.**

1. WSClean completes successfully and begins cleanup
2. Docker attempts to unmount volumes (`/data_ms`, `/data_txt`) with `--rm` flag
3. Volume unmounting hangs (likely causes):
   - File locks on MS from CASA/WSClean
   - NFS latency on `/stage` mount
   - Kernel-level issues with bind mounts
4. Process hangs before subprocess timeout can trigger
5. External process interruption (session timeout, OOM, system limit)

## Why Timeouts Don't Help

Added timeouts to subprocess.run() calls:

```python
subprocess.run(cmd_predict, check=True, timeout=600)  # 10 min
```

**But the process gets interrupted BEFORE the timeout expires.**

This suggests the hang is at a lower level (kernel/Docker daemon) rather than
the Python subprocess level.

## Attempted Fixes (All Failed)

1. ✅ **Fixed MODEL_DATA conflict** - Disabled dual seeding (calibrator + NVSS)
2. ✅ **Disabled model export** - Removed CASA incompatibility
3. ❌ **Added subprocess timeouts** - Process interrupted before timeout
4. ❌ **Permission fixes** - Already implemented, didn't help
5. ❌ **Different Docker flags** - Still hangs

## Workaround: Disable NVSS Seeding

**Use standard self-calibration without catalog-based MODEL_DATA seeding.**

### Working Configuration

```python
config = SelfCalConfig(
    use_nvss_seeding=False,  # DISABLE to avoid Docker hang
    calib_ra_deg=129.278,   # Use calibrator model instead
    calib_dec_deg=55.381,
    calib_flux_jy=0.050,
    # ... other parameters
)
```

### Impact

- ✅ Self-calibration completes successfully
- ✅ SNR improvement still achieved
- ❌ No multi-source sky model (only calibrator)
- ❌ Slower imaging (no mask-based optimization)

## Alternative Approaches (Future Work)

### 1. Native WSClean Instead of Docker

Check for native WSClean installation:

```bash
which wsclean
# If found, set: wsclean_path="/path/to/wsclean"
```

**Pros:** Avoids Docker entirely, faster execution  
**Cons:** Requires WSClean installed on host system

### 2. Pre-Seed MODEL_DATA Separately

Run NVSS prediction as a one-time preprocessing step:

```bash
# Outside the self-cal loop
wsclean -predict -name nvss_model ms_path.ms
```

Then run self-cal without `use_nvss_seeding`.

**Pros:** Decouples MODEL_DATA seeding from self-cal iteration  
**Cons:** Extra preprocessing step, manual workflow

### 3. Use FITS Masks Only (No MODEL_DATA Seeding)

Use NVSS catalog for cleaning masks but skip MODEL_DATA seeding:

```python
# Future enhancement needed in code
use_nvss_mask=True,     # For cleaning mask
seed_nvss_model=False,  # Skip MODEL_DATA seeding
```

**Pros:** Fast cleaning with masks, no Docker hang  
**Cons:** Requires code modifications to separate mask/seeding

### 4. Investigate Docker/Kernel Issue

- Check Docker logs: `docker logs <container_id>`
- Check kernel logs: `dmesg | tail -100`
- Test with different Docker storage drivers
- Test on different filesystem (not NFS)

## Impact Assessment

| Feature                 | Without NVSS Seeding | With NVSS Seeding (Broken) |
| ----------------------- | -------------------- | -------------------------- |
| Self-cal works          | ✅ Yes               | ❌ Hangs                   |
| SNR improvement         | ✅ Yes               | N/A                        |
| Multi-source sky model  | ❌ No                | ✅ Yes (if worked)         |
| Masked cleaning speedup | ❌ No                | ✅ Yes (if worked)         |
| Execution time          | ~10-15 min           | N/A (hangs)                |
| Production readiness    | ✅ Ready             | ❌ Not ready               |

## Recommendation

**For production use: Disable NVSS seeding until Docker hang is resolved.**

```python
# Production-safe configuration
config = SelfCalConfig(
    use_nvss_seeding=False,  # CRITICAL: Prevents hang
    calib_ra_deg=ra,
    calib_dec_deg=dec,
    calib_flux_jy=flux,
    # ... standard self-cal parameters
)
```

## Testing Status

| Test Configuration                    | Result      | Notes              |
| ------------------------------------- | ----------- | ------------------ |
| Self-cal without NVSS seeding         | ✅ Works    | Production-ready   |
| Self-cal with calibrator model only   | ✅ Works    | Production-ready   |
| NVSS catalog query (standalone)       | ✅ Works    | Not the issue      |
| NVSS mask creation (standalone)       | ✅ Works    | Not the issue      |
| NVSS MODEL_DATA seeding via Docker    | ❌ Hangs    | Known issue        |
| NVSS MODEL_DATA seeding via native WS | ⚠️ Untested | Potential solution |

## Related Documentation

- `docs/troubleshooting/selfcal_nvss_hang_fix.md` - MODEL_DATA conflict fix
- `docs/troubleshooting/wsclean_docker_hang_fix.md` - Timeout attempt (failed)
- `docs/how-to/self_calibration.md` - User guide (needs update)

## Files Affected

- `scripts/test_selfcal_masked.py` - Uses NVSS seeding (broken)
- `scripts/test_selfcal_simple.py` - Avoids NVSS seeding (working)
- `backend/src/dsa110_contimg/imaging/cli_imaging.py` - Docker WSClean calls
- `backend/src/dsa110_contimg/calibration/selfcal.py` - Self-cal orchestration

---

**Status:** 🔴 Unresolved - Use workaround (disable NVSS seeding) for production
until native WSClean solution is implemented or Docker issue is debugged at
kernel level.

**Priority:** Medium - Workaround is available and production-ready
