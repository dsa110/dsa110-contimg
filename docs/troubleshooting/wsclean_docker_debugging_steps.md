# Docker WSClean Hang - Debugging Steps

**Date:** 2025-11-20  
**Type:** Debugging Guide  
**Status:** 🔄 In Progress

---

## Problem Statement

Docker WSClean `-predict` operations hang at "Cleaning up temporary files..."
and get interrupted BEFORE Python's subprocess timeout expires. This suggests
the issue is below the Python layer.

## Current State

### ✅ What We Know

- Timeouts ARE implemented (30 min, 10 min, 5 min)
- Timeouts ARE in the code (verified at lines 318, 880, 912, 952, 973)
- Main imaging works with timeouts
- NVSS `-predict` hangs even with timeout=600s

### ❓ What We DON'T Know

- What's killing the process before timeout?
- Is it OOM killer, session timeout, or Docker daemon?
- Is it kernel-level deadlock on volume unmount?

---

## Diagnostic Steps

### Step 1: Capture Exact Error When Hang Occurs

Modify the code to capture exactly what happens:

```python
import signal
import time

def timeout_handler(signum, frame):
    LOG.error("TIMEOUT HANDLER TRIGGERED - Python timeout expired")
    raise TimeoutError("Python subprocess timeout reached")

# Before subprocess.run():
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(600)  # Set alarm for same duration as subprocess timeout

try:
    result = subprocess.run(cmd_predict, check=True, timeout=600)
    signal.alarm(0)  # Cancel alarm if successful
    LOG.info("subprocess.run() completed successfully")
except subprocess.TimeoutExpired:
    LOG.error("subprocess.TimeoutExpired exception raised")
    raise
except TimeoutError:
    LOG.error("TimeoutError from signal handler")
    raise
except Exception as e:
    LOG.error(f"Other exception: {type(e).__name__}: {e}")
    raise
```

**Expected outputs:**

- If Python timeout works: "subprocess.TimeoutExpired exception raised"
- If signal handler fires: "TimeoutError from signal handler"
- If external kill: "Other exception: ..." or no log at all

### Step 2: Monitor System While Hang Occurs

Run these in separate terminals while the hang is happening:

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
# Check Docker daemon logs for the exact time of hang
journalctl -u docker.service -f --since "5 minutes ago"

# Or if using Docker Desktop
docker logs $(docker ps -a | grep wsclean | head -1 | awk '{print $1}')
```

### Step 4: Test Without --rm Flag

Try running Docker WSClean WITHOUT auto-removal to see if that's the issue:

```python
# In cli_imaging.py, modify Docker command:
# REMOVE: "--rm",
cmd = [
    "docker",
    "run",
    # "--rm",  # <-- COMMENT OUT THIS LINE
    "-v", f"{ms_dir}:/data_ms",
    "-v", f"{txt_dir}:/data_txt",
    "dsa110/wsclean:latest",
    "wsclean",
    "-predict",
    # ... rest of command
]
```

Then manually clean up containers later:

```bash
docker ps -a | grep wsclean | awk '{print $1}' | xargs docker rm
```

### Step 5: Test With Detached Docker

Try running Docker in detached mode and waiting for it:

```python
import subprocess
import time

# Start Docker in detached mode
container_id = subprocess.check_output(
    ["docker", "run", "-d", "-v", f"{ms_dir}:/data_ms", ...],
    text=True
).strip()

LOG.info(f"Started container {container_id}")

# Poll for completion with timeout
start_time = time.time()
timeout = 600
while time.time() - start_time < timeout:
    result = subprocess.run(
        ["docker", "ps", "-q", "--filter", f"id={container_id}"],
        capture_output=True,
        text=True
    )
    if not result.stdout.strip():
        # Container finished
        break
    time.sleep(5)
else:
    LOG.error("Container still running after timeout")
    subprocess.run(["docker", "kill", container_id])

# Get exit code
exit_code = subprocess.check_output(
    ["docker", "inspect", container_id, "--format='{{.State.ExitCode}}'"],
    text=True
).strip()

LOG.info(f"Container exit code: {exit_code}")
```

### Step 6: Check NFS Performance

If MS is on NFS, test if that's the bottleneck:

```bash
# Check NFS mount options
mount | grep /stage

# Test NFS performance
dd if=/dev/zero of=/stage/test_nfs_write bs=1M count=1000
rm /stage/test_nfs_write

# Check NFS server logs (if accessible)
# This might show volume unmount timeouts
```

### Step 7: Strace the Docker Process

Capture system calls to see where it hangs:

```bash
# Find the Docker process PID
ps aux | grep "docker run.*wsclean"

# Strace it (run this BEFORE the hang occurs)
strace -p <PID> -f -o /tmp/docker_wsclean_strace.txt

# When it hangs, check what system call is blocking:
tail -100 /tmp/docker_wsclean_strace.txt
```

Look for:

- `umount()` calls - Volume unmount issues
- `flock()` or `fcntl()` - File locking issues
- `wait()` or `waitpid()` - Waiting for child process

---

## Expected Findings

### Scenario A: OOM Killer

```
dmesg:
[12345.678] Out of memory: Kill process 12345 (python) score 900 or sacrifice child
[12345.679] Killed process 12345 (python) total-vm:8GB
```

**Solution:** Increase memory limits, reduce concurrent operations

### Scenario B: Docker Daemon Timeout

```
journalctl -u docker:
timeout waiting for container to stop
failed to remove container: device or resource busy
```

**Solution:** Increase Docker daemon timeout, don't use `--rm` flag

### Scenario C: NFS Volume Unmount Hang

```
strace output:
umount2("/var/lib/docker/volumes/...", 0) = ? ERESTARTSYS (Interrupted by signal)
```

**Solution:** Copy MS to local disk, use native WSClean, or pre-seed MODEL_DATA

### Scenario D: Python Timeout Actually Works

```
subprocess.TimeoutExpired exception raised
```

**Solution:** Document 2 is outdated, timeouts DO work

---

## Next Actions Based on Findings

| Finding              | Recommendation                                                    |
| -------------------- | ----------------------------------------------------------------- |
| OOM Killer           | Add memory limits to config, reduce concurrent tasks              |
| Docker Timeout       | Remove `--rm` flag, manual cleanup, or increase daemon timeout    |
| NFS Unmount          | Use local temp directory, native WSClean, or rsync before imaging |
| File Locks           | Add explicit file handle cleanup before Docker call               |
| Python Timeout Works | Update documentation, issue is resolved                           |

---

## Proposed Code Enhancement

Add comprehensive error handling and diagnostics:

```python
import signal
import psutil
import time
from contextlib import contextmanager

@contextmanager
def monitor_subprocess(cmd, timeout, log_prefix="subprocess"):
    """Context manager for subprocess monitoring with detailed diagnostics."""
    start_time = time.time()
    proc = None

    try:
        LOG.info(f"{log_prefix}: Starting command: {' '.join(cmd)}")
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Monitor process
        while proc.poll() is None:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                LOG.error(f"{log_prefix}: Timeout after {elapsed:.1f}s")

                # Get process tree info before killing
                try:
                    parent = psutil.Process(proc.pid)
                    children = parent.children(recursive=True)
                    LOG.error(f"{log_prefix}: Parent PID {proc.pid}, {len(children)} children")
                    for child in children:
                        LOG.error(f"  Child: {child.pid} {child.name()} {child.status()}")
                except:
                    pass

                # Kill process tree
                proc.terminate()
                time.sleep(5)
                proc.kill()
                raise subprocess.TimeoutExpired(cmd, timeout)

            time.sleep(1)

        # Process finished
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            LOG.error(f"{log_prefix}: Failed with exit code {proc.returncode}")
            LOG.error(f"STDERR: {stderr}")
            raise subprocess.CalledProcessError(proc.returncode, cmd, stdout, stderr)

        LOG.info(f"{log_prefix}: Completed in {time.time() - start_time:.1f}s")
        yield proc

    except subprocess.TimeoutExpired:
        LOG.error(f"{log_prefix}: Python timeout mechanism triggered")
        raise
    except Exception as e:
        LOG.error(f"{log_prefix}: Exception {type(e).__name__}: {e}")
        raise
    finally:
        if proc and proc.poll() is None:
            proc.kill()

# Usage:
with monitor_subprocess(cmd_predict, timeout=600, log_prefix="wsclean-predict"):
    pass  # Process monitored in context manager
```

---

## Files to Update After Diagnosis

1. `docs/troubleshooting/docker_wsclean_known_issue.md` - Update with findings
2. `docs/troubleshooting/wsclean_docker_hang_fix.md` - Clarify what's fixed vs
   not
3. `src/dsa110_contimg/src/dsa110_contimg/imaging/cli_imaging.py` - Add enhanced
   error handling
4. `scripts/test_selfcal_masked.py` - Add diagnostic logging

---

**Status:** 🔄 Awaiting diagnostic results

**Priority:** High - Blocks NVSS seeding feature
