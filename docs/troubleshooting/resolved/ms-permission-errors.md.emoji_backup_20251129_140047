# MS Permission Errors - Troubleshooting Guide

**Date:** 2025-11-19  
**Type:** Troubleshooting  
**Status:** ✅ Resolved

---

## Problem Description

When running CASA tasks (particularly `applycal`, `gaincal`, `tclean`) on
Measurement Set (MS) files, you may encounter permission errors like:

```
RuntimeError: RegularFileIO: error in open or create of file
/path/to/file.ms/table.dat: Permission denied
```

This occurs because:

1. CASA tasks may be run as `root` user
2. MS files and their contents are created with `root` ownership
3. Non-root users (like `ubuntu`) cannot modify these files
4. Each CASA task that modifies the MS may reset ownership

---

## Root Cause

Measurement Sets are **directories** containing multiple files and
subdirectories:

```
2025-10-19T14:31:45.ms/
├── table.dat           # Main data file
├── table.f0            # Data columns
├── ANTENNA/
├── DATA_DESCRIPTION/
├── FEED/
├── FIELD/
├── OBSERVATION/
├── SPECTRAL_WINDOW/
└── ... (other tables)
```

When CASA opens an MS for writing (e.g., to update `CORRECTED_DATA`), it:

- May create new files with `root` ownership
- May change permissions on existing files
- Requires write access to multiple subdirectories

---

## Solutions Implemented

### Solution 1: Automated Permission Fixing in Self-Calibration

The `selfcal.py` module now **automatically fixes MS permissions**:

1. **At initialization:** Fixes permissions when `SelfCalibrator` is created
2. **After each `applycal` call:** Re-fixes permissions in case CASA changed
   them

**Implementation:**

```python
def _fix_ms_permissions(ms_path: Path, user: str = None) -> bool:
    """Fix MS permissions to ensure current user can read/write."""
    if user is None:
        user = os.getenv("USER", "ubuntu")

    # Change ownership recursively
    subprocess.run(["sudo", "chown", "-R", f"{user}:{user}", str(ms_path)], ...)

    # Set permissions (u+rw, g+r, o+r)
    subprocess.run(["sudo", "chmod", "-R", "u+rw,g+r,o+r", str(ms_path)], ...)

    # Make directories executable
    subprocess.run(["sudo", "find", str(ms_path), "-type", "d", "-exec", "chmod", "u+x", "{}", "+"], ...)
```

**Integrated into workflow:**

```python
class SelfCalibrator:
    def __init__(self, ms_path, ...):
        self.ms_path = Path(ms_path)
        # Fix permissions at initialization
        _fix_ms_permissions(self.ms_path)

    def _run_initial_imaging(self):
        applycal(vis=self.ms_path, ...)
        # Fix permissions after applycal
        _fix_ms_permissions(self.ms_path)
```

This ensures permissions are correct **before and after** every operation that
might change them.

---

### Solution 2: Manual Permission Fixing Script

For manual/ad-hoc fixes, use the provided script:

```bash
/data/dsa110-contimg/scripts/fix_ms_permissions.sh <ms_path> [user]
```

**Example:**

```bash
# Fix permissions for specific MS
./scripts/fix_ms_permissions.sh /stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms ubuntu

# Output:
# Fixing permissions for: /stage/dsa110-contimg/test_data/2025-10-19T14:31:45.ms
# Target user: ubuntu
#   - Changing ownership to ubuntu...
#   - Setting permissions (u+rw,g+r,o+r)...
#   - Making directories executable...
# ✓ Permissions fixed successfully
```

---

### Solution 3: Run CASA Tasks as Non-Root User

**Preferred long-term solution:** Configure the system to run CASA tasks as the
correct user from the start.

**Environment setup:**

```bash
# In ~/.bashrc or script
export USER=ubuntu
export HOME=/home/ubuntu

# Activate casa6 environment
source /opt/miniforge/envs/casa6/bin/activate
```

**When launching Python scripts:**

```bash
# Run as ubuntu user, not root
python3 script.py
# NOT: sudo python3 script.py
```

---

## Verification

Check MS permissions:

```bash
# Check ownership
ls -la /path/to/file.ms/table.dat

# Should show:
# -rw-r--r-- 1 ubuntu ubuntu 13806 Nov 19 09:01 table.dat
#              ^^^^^^ ^^^^^^
#              user   group
```

Check if you can write:

```bash
# Test write access
touch /path/to/file.ms/test_write && rm /path/to/file.ms/test_write && echo "✓ Write access OK"
```

---

## Prevention

To prevent permission issues in the future:

### 1. **Always run as correct user**

```bash
# Good
python3 /data/dsa110-contimg/scripts/test_selfcal.py

# Bad
sudo python3 /data/dsa110-contimg/scripts/test_selfcal.py
```

### 2. **Use developer setup**

```bash
source /data/dsa110-contimg/scripts/dev/developer-setup.sh
```

This ensures:

- Correct Python environment (casa6)
- Correct user permissions
- Error detection enabled

### 3. **Check permissions before long-running operations**

```bash
# Before starting self-calibration
./scripts/fix_ms_permissions.sh /path/to/file.ms
python3 test_selfcal.py
```

---

## Related Issues

- **Issue:** `applycal` fails with "Permission denied"
  - **Solution:** Run `fix_ms_permissions.sh` or use `selfcal.py` (automatic)
- **Issue:** MS created as root, can't modify as ubuntu
  - **Solution:** Change ownership with `sudo chown -R ubuntu:ubuntu file.ms`
- **Issue:** Permission denied on subdirectories
  - **Solution:** Use recursive chmod/chown (included in
    `fix_ms_permissions.sh`)

---

## Technical Details

### Why CASA Creates Root-Owned Files

1. **CASA process inheritance:** If CASA is launched by a root process, child
   processes inherit root privileges
2. **System configuration:** Some systems run scientific software as root for
   hardware access
3. **File creation defaults:** New files inherit the creating process's UID/GID

### Permission Requirements

CASA tasks need:

- **Read access:** All MS subdirectories and files
- **Write access:** `table.dat`, column files (`table.f*`), lock files
- **Execute access:** All MS subdirectories (to traverse)

### Security Implications

Using `sudo` in production code is **NOT recommended** long-term. Better
solutions:

- Run entire pipeline as correct user
- Use setuid/setgid on directories
- Use filesystem ACLs
- Run in container with correct UID mapping

---

## Summary

**Problem:** MS permission errors block self-calibration and other CASA
operations

**Solutions:**

1. ✅ **Automatic:** `selfcal.py` fixes permissions automatically
2. ✅ **Manual:** Use `fix_ms_permissions.sh` script
3. ✅ **Prevention:** Run as correct user from the start

**Status:** Resolved - self-calibration now handles permissions automatically

---

**See Also:**

- `docs/how-to/self_calibration.md` - Self-calibration user guide
- `scripts/fix_ms_permissions.sh` - Permission fixing script
- `backend/src/dsa110_contimg/calibration/selfcal.py` - Implementation
