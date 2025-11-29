# Docker WSClean Container Hang

**Date:** November 2025  
**Severity:** HIGH  
**Status:** 🔴 Open (Workaround Available)  
**Affects:** NVSS seeding, Docker-based WSClean `-predict` operations

---

## Table of Contents

1. [Problem Description](#problem-description)
2. [Symptoms](#symptoms)
3. [Root Cause Analysis](#root-cause-analysis)
4. [Workaround](#workaround)
5. [Debugging Steps](#debugging-steps)
6. [Alternative Solutions](#alternative-solutions)
7. [Impact Assessment](#impact-assessment)

---

## Problem Description

Docker-based WSClean `-predict` operations consistently hang at "Cleaning up
temporary files..." and never complete. This affects:

- NVSS sky model prediction (`-predict` with Docker WSClean)
- Any Docker WSClean operation that writes to MS MODEL_DATA
- Self-calibration with `use_nvss_seeding=True`

Python subprocess timeouts don't trigger because the hang occurs at the
Docker/kernel level, not the Python layer.

---

## Symptoms

```
Writing changed model back to /data_ms/2025-10-19T14:31:45.ms:
 0%....10%....20%....30%....40%....50%....60%....70%....80%....90%....100%
Cleaning up temporary files...
[HANGS INDEFINITELY - timeouts don't trigger]
```

### What We Know

- Timeouts ARE implemented (30 min, 10 min, 5 min)
- Main imaging works with timeouts
- NVSS `-predict` hangs even with `timeout=600s`
- Process gets interrupted BEFORE timeout expires

### What We Don't Know

- What's killing the process before timeout
- Whether it's OOM killer, session timeout, or Docker daemon
- Whether it's a kernel-level deadlock on volume unmount

---

## Root Cause Analysis

**Suspected cause: Docker volume unmounting after container completion**

1. WSClean completes successfully and begins cleanup
2. Docker attempts to unmount volumes (`/data_ms`, `/data_txt`) with `--rm` flag
3. Volume unmounting hangs due to:
   - File locks on MS from CASA/WSClean
   - NFS latency on `/stage` mount
   - Kernel-level issues with bind mounts
4. Process hangs before subprocess timeout can trigger
5. External process interruption (session timeout, OOM, system limit)

### Why Timeouts Don't Help

```python
subprocess.run(cmd_predict, check=True, timeout=600)  # 10 min
```

The hang is at a lower level (kernel/Docker daemon) rather than the Python
subprocess level.

---

## Workaround

**Disable NVSS seeding for production use.**

### Working Configuration

```python
config = SelfCalConfig(
    use_nvss_seeding=False,  # DISABLE to avoid Docker hang
    calib_ra_deg=129.278,    # Use calibrator model instead
    calib_dec_deg=55.381,
    calib_flux_jy=0.050,
    # ... other parameters
)
```

### Impact of Workaround

| Feature                 | Without NVSS Seeding | With NVSS Seeding (Broken) |
| ----------------------- | -------------------- | -------------------------- |
| Self-cal works          | ✅ Yes               | ❌ Hangs                   |
| SNR improvement         | ✅ Yes               | N/A                        |
| Multi-source sky model  | ❌ No                | ✅ Yes (if worked)         |
| Masked cleaning speedup | ❌ No                | ✅ Yes (if worked)         |
| Execution time          | ~10-15 min           | N/A (hangs)                |
| Production readiness    | ✅ Ready             | ❌ Not ready               |

---

## Debugging Steps

### Step 1: Capture Exact Error

Add signal handler to determine what's killing the process:

```python
import signal

def timeout_handler(signum, frame):
    LOG.error("TIMEOUT HANDLER TRIGGERED - Python timeout expired")
    raise TimeoutError("Python subprocess timeout reached")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(600)

try:
    result = subprocess.run(cmd_predict, check=True, timeout=600)
    signal.alarm(0)
except subprocess.TimeoutExpired:
    LOG.error("subprocess.TimeoutExpired exception raised")
except TimeoutError:
    LOG.error("TimeoutError from signal handler")
except Exception as e:
    LOG.error(f"Other exception: {type(e).__name__}: {e}")
```

### Step 2: Monitor System During Hang

Run in separate terminals:

```bash
# Terminal 1: Monitor Docker containers
watch -n 1 'docker ps -a | head -20'

# Terminal 2: Monitor system logs for OOM
tail -f /var/log/syslog | grep -i "oom\|killed"

# Terminal 3: Monitor dmesg for kernel issues
dmesg -w | grep -i "docker\|killed\|timeout"

# Terminal 4: Monitor process tree
watch -n 2 'ps aux | grep wsclean'

# Terminal 5: Check file locks on MS
while true; do
    lsof /stage/dsa110-contimg/test_ms/*.ms 2>/dev/null | grep -v "^COMMAND"
    sleep 5
done
```

### Step 3: Check Docker Daemon Logs

```bash
journalctl -u docker.service -f --since "5 minutes ago"
```

### Step 4: Test Without --rm Flag

Modify Docker command to NOT auto-remove container:

```python
cmd = [
    "docker", "run",
    # "--rm",  # COMMENT OUT
    "-v", f"{ms_dir}:/data_ms",
    "-v", f"{txt_dir}:/data_txt",
    "dsa110/wsclean:latest",
    "wsclean", "-predict",
    # ...
]
```

Then manually clean up:

```bash
docker ps -a | grep wsclean | awk '{print $1}' | xargs docker rm
```

### Step 5: Strace the Docker Process

```bash
ps aux | grep "docker run.*wsclean"
strace -p <PID> -f -o /tmp/docker_wsclean_strace.txt
# When it hangs:
tail -100 /tmp/docker_wsclean_strace.txt
```

Look for:

- `umount()` - Volume unmount issues
- `flock()` / `fcntl()` - File locking issues
- `wait()` / `waitpid()` - Waiting for child process

---

## Alternative Solutions

### 1. Native WSClean Instead of Docker

```bash
which wsclean
# If found: wsclean_path="/path/to/wsclean"
```

**Pros:** Avoids Docker entirely, faster execution  
**Cons:** Requires WSClean installed on host system

### 2. Pre-Seed MODEL_DATA Separately

Run NVSS prediction as a one-time preprocessing step outside self-cal loop:

```bash
wsclean -predict -name nvss_model ms_path.ms
```

**Pros:** Decouples MODEL_DATA seeding from self-cal  
**Cons:** Extra preprocessing step, manual workflow

### 3. Use FITS Masks Only

Use unified catalog for cleaning masks but skip MODEL_DATA seeding:

```python
# Future enhancement
use_unicat_mask=True,     # For unified catalog cleaning mask
seed_nvss_model=False,    # Skip MODEL_DATA seeding
```

**Pros:** Fast cleaning with masks, no Docker hang  
**Cons:** Requires code modifications

### 4. Investigate Docker/Kernel Issue

- Check Docker logs: `docker logs <container_id>`
- Check kernel logs: `dmesg | tail -100`
- Test with different Docker storage drivers
- Test on different filesystem (not NFS)

---

## Impact Assessment

### Testing Status

| Test Configuration                    | Result      | Notes              |
| ------------------------------------- | ----------- | ------------------ |
| Self-cal without NVSS seeding         | ✅ Works    | Production-ready   |
| Self-cal with calibrator model only   | ✅ Works    | Production-ready   |
| NVSS catalog query (standalone)       | ✅ Works    | Not the issue      |
| NVSS mask creation (standalone)       | ✅ Works    | Not the issue      |
| NVSS MODEL_DATA seeding via Docker    | ❌ Hangs    | Known issue        |
| NVSS MODEL_DATA seeding via native WS | ⚠️ Untested | Potential solution |

### Attempted Fixes (All Failed)

1. ✅ Fixed MODEL_DATA conflict - Disabled dual seeding (calibrator + NVSS)
2. ✅ Disabled model export - Removed CASA incompatibility
3. ❌ Added subprocess timeouts - Process interrupted before timeout
4. ❌ Permission fixes - Already implemented, didn't help
5. ❌ Different Docker flags - Still hangs

---

## Files Affected

- `scripts/test_selfcal_masked.py` - Uses NVSS seeding (broken)
- `scripts/test_selfcal_simple.py` - Avoids NVSS seeding (working)
- `backend/src/dsa110_contimg/imaging/cli_imaging.py` - Docker WSClean calls
- `backend/src/dsa110_contimg/calibration/selfcal.py` - Self-cal orchestration

---

## Recommendation

**For production:** Disable NVSS seeding until Docker hang is resolved.

```python
config = SelfCalConfig(
    use_nvss_seeding=False,  # CRITICAL: Prevents hang
    # ... standard self-cal parameters
)
```

**Priority:** Medium - Workaround is available and production-ready

---

## Related Documentation

- [MS Permission Errors](resolved/ms-permission-errors.md) - Related permission
  fixes
- [Self-Calibration Guide](../how-to/self_calibration.md) - User guide
